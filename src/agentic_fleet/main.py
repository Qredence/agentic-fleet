"""FastAPI entry point for the Agentic Fleet workflow."""

from __future__ import annotations

import json
import os
from typing import Any

import dspy
from asyncer import asyncify
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from agentic_fleet.gepa.optimizer import FleetOptimizer
from agentic_fleet.config import TEAM_REGISTRY
from agentic_fleet.dspy_modules.signatures import TaskContext
from agentic_fleet.db import create_db_and_tables, save_run
from agentic_fleet.llm import get_lm
from agentic_fleet.skills.manager import SkillManager
from agentic_fleet.skills.models import Skill, SkillContent, SkillMetadata
from agentic_fleet.workflows.modules import build_modules_workflow


class RunRequest(BaseModel):
    message: str = Field(..., description="User message to route through the workflow.")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata passed to all agents."
    )
    team_id: str | None = Field(default=None, description="Optional team identifier override.")


class RunResponse(BaseModel):
    outputs: list[Any] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)


class TrainExample(BaseModel):
    task: str
    plan: str
    result: str
    team_id: str | None = Field(default=None, description="Optional team id for context.")
    constraints: list[str] | None = Field(default=None, description="Optional constraints list.")
    tools: list[str] | None = Field(default=None, description="Optional tools override.")


class TrainRequest(BaseModel):
    examples: list[TrainExample] = Field(default_factory=list)


class TrainResponse(BaseModel):
    output_path: str
    examples_used: int


class CreateSkillRequest(BaseModel):
    skill_id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Human-readable skill name")
    version: str = Field(default="1.0.0", description="Semantic version")
    description: str = Field(..., description="Brief skill description")
    team_id: str = Field(..., description="Team that owns this skill")
    tags: list[str] = Field(default_factory=list, description="Skill tags")
    purpose: str = Field(..., description="When and why to use this skill")
    when_to_use: str = Field(..., description="Conditions for skill selection")
    how_to_apply: str = Field(..., description="Implementation guidance")
    example: str = Field(default="", description="Usage example")
    constraints: list[str] = Field(default_factory=list, description="Skill constraints")
    prerequisites: list[str] = Field(default_factory=list, description="Required context/tools")


class UpdateSkillRequest(BaseModel):
    metadata: dict[str, Any] | None = None
    content: dict[str, Any] | None = None


def _jsonify(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {key: _jsonify(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonify(item) for item in value]
    if hasattr(value, "to_dict"):
        try:
            return _jsonify(value.to_dict())
        except Exception:
            pass
    if hasattr(value, "model_dump"):
        try:
            return _jsonify(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return _jsonify(value.dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            data = {key: val for key, val in value.__dict__.items() if not key.startswith("_")}
            return _jsonify(data)
        except Exception:
            pass
    return str(value)


def _configure_dspy() -> None:
    model = os.getenv("DSPY_MODEL", "deepseek-v3.2")
    lm = get_lm(model=model)
    dspy.settings.configure(lm=lm)


def create_app() -> FastAPI:
    app = FastAPI()
    workflow = build_modules_workflow()
    app.state.workflow = workflow
    app.state.planner_state_path = None

    @app.on_event("startup")
    async def _startup() -> None:
        load_dotenv(dotenv_path=".env", override=False)
        _configure_dspy()
        await asyncify(create_db_and_tables)()

    @app.post("/run", response_model=RunResponse)
    async def run_workflow(payload: RunRequest) -> RunResponse:
        result = await app.state.workflow.run(
            payload.message,
            metadata=payload.metadata,
            team_id=payload.team_id,
        )
        outputs = _jsonify(result.get_outputs())
        trace = [event.executor_id for event in result if hasattr(event, "executor_id")]
        await asyncify(save_run)(
            message=payload.message,
            outputs=outputs,
            trace=trace,
            team_id=payload.team_id,
            metadata=payload.metadata,
        )
        return RunResponse(outputs=outputs, trace=trace)

    @app.websocket("/ws")
    async def websocket_run(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                try:
                    payload = await websocket.receive_json()
                except (ValueError, json.JSONDecodeError):
                    await websocket.send_json({"error": "invalid_json"})
                    continue

                message = payload.get("message") if isinstance(payload, dict) else None
                if not message:
                    await websocket.send_json({"error": "missing_message"})
                    continue

                metadata = payload.get("metadata") if isinstance(payload, dict) else None
                team_id = payload.get("team_id") if isinstance(payload, dict) else None

                result = await app.state.workflow.run(
                    message,
                    metadata=metadata,
                    team_id=team_id,
                )
                outputs = _jsonify(result.get_outputs())
                trace = [event.executor_id for event in result if hasattr(event, "executor_id")]
                await asyncify(save_run)(
                    message=message,
                    outputs=outputs,
                    trace=trace,
                    team_id=team_id,
                    metadata=metadata,
                )
                await websocket.send_json({"outputs": outputs, "trace": trace})
        except WebSocketDisconnect:
            return

    @app.post("/train", response_model=TrainResponse)
    async def train_fleet(payload: TrainRequest) -> TrainResponse:
        if not payload.examples:
            raise HTTPException(status_code=400, detail="No training examples provided.")

        state_dir = os.getenv("FLEET_STATE_DIR", ".context/state")
        training_data = []
        for ex in payload.examples:
            team_id = ex.team_id or "default"
            team_cfg = TEAM_REGISTRY.get(team_id, TEAM_REGISTRY["default"])
            tools = ex.tools if ex.tools is not None else list(team_cfg.get("tools", []))
            constraints = ex.constraints or []
            context = TaskContext(team_id=team_id, constraints=constraints, tools=tools)
            training_data.append(
                dspy.Example(
                    task=ex.task,
                    context=context,
                    plan=ex.plan,
                    result=ex.result,
                ).with_inputs("task", "context")
            )

        optimizer = FleetOptimizer()
        output_path = optimizer.compile(
            training_data,
            output_path=state_dir,
        )

        app.state.planner_state_path = str(output_path)
        app.state.workflow = build_modules_workflow(planner_state_path=str(output_path))

        return TrainResponse(output_path=str(output_path), examples_used=len(training_data))

    # Skill management endpoints
    skill_manager = SkillManager()

    @app.get("/skills")
    async def list_skills(team_id: str | None = None) -> dict:
        """List all available skills, optionally filtered by team."""
        skills = skill_manager.list_skills(team_id)
        return {"skills": [s.model_dump() for s in skills]}

    @app.get("/skills/{skill_id}")
    async def get_skill(skill_id: str, team_id: str | None = None) -> dict:
        """Get details of a specific skill."""
        skill = skill_manager.get_skill(skill_id, team_id)
        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
        return skill.model_dump()

    @app.post("/skills")
    async def create_skill(request: CreateSkillRequest) -> dict:
        """Create a new skill."""
        metadata = SkillMetadata(
            skill_id=request.skill_id,
            name=request.name,
            version=request.version,
            description=request.description,
            team_id=request.team_id,
            tags=request.tags,
        )
        content = SkillContent(
            purpose=request.purpose,
            when_to_use=request.when_to_use,
            how_to_apply=request.how_to_apply,
            example=request.example,
            constraints=request.constraints,
            prerequisites=request.prerequisites,
        )
        skill = Skill(metadata=metadata, content=content)
        path = skill_manager.create_skill(skill)
        return {"message": "Skill created", "path": str(path)}

    @app.put("/skills/{skill_id}")
    async def update_skill(
        skill_id: str,
        request: UpdateSkillRequest,
        team_id: str | None = None,
    ) -> dict:
        """Update an existing skill."""
        success = skill_manager.update_skill(skill_id, request.model_dump(exclude_none=True), team_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
        return {"message": "Skill updated"}

    @app.delete("/skills/{skill_id}")
    async def delete_skill(skill_id: str, team_id: str | None = None) -> dict:
        """Delete a skill."""
        success = skill_manager.delete_skill(skill_id, team_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
        return {"message": "Skill deleted"}

    @app.get("/skills/{skill_id}/usage")
    async def get_skill_usage(skill_id: str) -> dict:
        """Get usage statistics for a skill."""
        patterns = skill_manager.get_successful_patterns(skill_id)
        return {"skill_id": skill_id, "patterns": patterns}

    # =============================================================================
    # Skill Creation API (6-step workflow)
    # =============================================================================

    @app.post("/skills/create/understand")
    async def understand_skill_request(
        request: dict,
    ) -> dict:
        """Step 1: Understand - Analyze task requirements and usage patterns."""
        from agentic_fleet.skills.creator import SkillUnderstandSignature
        import dspy

        raw_request = request.get("raw_request", "")
        context_history = request.get("context_history", "")

        result = dspy.Predict(SkillUnderstandSignature)(
            raw_request=raw_request,
            context_history=context_history,
        )

        return {
            "step": "understand",
            "task_summary": result.task_summary,
            "trigger_patterns": result.trigger_patterns.split(",") if result.trigger_patterns else [],
            "example_patterns": result.example_patterns,
            "required_capabilities": result.required_capabilities.split(",") if result.required_capabilities else [],
        }

    @app.post("/skills/create/plan")
    async def plan_skill_structure(request: dict) -> dict:
        """Step 2: Plan - Identify resources and skill structure."""
        from agentic_fleet.skills.creator import SkillPlanSignature
        import dspy

        task_summary = request.get("task_summary", "")
        required_capabilities = request.get("required_capabilities", "")
        existing_skills = request.get("existing_skills", "")

        result = dspy.Predict(SkillPlanSignature)(
            task_summary=task_summary,
            required_capabilities=required_capabilities,
            existing_skills=existing_skills,
        )

        return {
            "step": "plan",
            "skill_taxonomy": result.skill_taxonomy,
            "scripts_needed": result.scripts_needed.split(",") if result.scripts_needed else [],
            "references_needed": result.references_needed.split(",") if result.references_needed else [],
            "assets_needed": result.assets_needed.split(",") if result.assets_needed else [],
            "avoid_duplication": result.avoid_duplication.split(",") if result.avoid_duplication else [],
        }

    @app.post("/skills/create/initialize")
    async def initialize_skill(request: dict) -> dict:
        """Step 3: Initialize - Create skill skeleton."""
        from agentic_fleet.skills.creator import SkillInitializeSignature
        import dspy

        skill_name = request.get("skill_name", "")
        skill_taxonomy = request.get("skill_taxonomy", "")
        task_summary = request.get("task_summary", "")

        result = dspy.Predict(SkillInitializeSignature)(
            skill_name=skill_name,
            skill_taxonomy=skill_taxonomy,
            task_summary=task_summary,
        )

        return {
            "step": "initialize",
            "skill_directory": result.skill_directory,
            "skill_yaml": result.skill_yaml,
            "script_templates": result.script_templates,
            "reference_templates": result.reference_templates,
        }

    @app.post("/skills/create/edit")
    async def generate_skill_content(request: dict) -> dict:
        """Step 4: Edit - Generate full skill content."""
        from agentic_fleet.skills.creator import SkillEditSignature
        import dspy

        skill_name = request.get("skill_name", "")
        task_summary = request.get("task_summary", "")
        example_patterns = request.get("example_patterns", "")
        required_capabilities = request.get("required_capabilities", "")
        compatibility_notes = request.get("compatibility_notes", "")

        result = dspy.Predict(SkillEditSignature)(
            skill_name=skill_name,
            task_summary=task_summary,
            example_patterns=example_patterns,
            required_capabilities=required_capabilities,
            compatibility_notes=compatibility_notes,
        )

        return {
            "step": "edit",
            "skill_purpose": result.skill_purpose,
            "when_to_use": result.when_to_use,
            "how_to_apply": result.how_to_apply,
            "example": result.example,
            "constraints": result.constraints.split(",") if result.constraints else [],
            "prerequisites": result.prerequisites.split(",") if result.prerequisites else [],
        }

    @app.post("/skills/create/package")
    async def package_skill(request: dict) -> dict:
        """Step 5: Package - Validate and prepare for approval."""
        from agentic_fleet.skills.creator import SkillPackageSignature
        import dspy

        skill_path = request.get("skill_path", "")
        skill_content = request.get("skill_content", "")
        skill_yaml = request.get("skill_yaml", "")

        result = dspy.Predict(SkillPackageSignature)(
            skill_path=skill_path,
            skill_content=skill_content,
            skill_yaml=skill_yaml,
        )

        validation_results = (
            result.validation_results.split(",") if result.validation_results else []
        )
        improvement_suggestions = (
            result.improvement_suggestions.split(",")
            if result.improvement_suggestions
            else []
        )

        return {
            "step": "package",
            "validation_results": validation_results,
            "quality_score": result.quality_score,
            "improvement_suggestions": improvement_suggestions,
            "package_status": result.package_status,
        }

    # Skill Approval Workflow
    from agentic_fleet.skills.approval import ApprovalStatus, approval_store

    @app.get("/skills/approvals")
    async def list_approvals(status: str | None = None) -> dict:
        """List skill approval requests."""
        workflows = approval_store.list_all()
        if status:
            workflows = [w for w in workflows if w.decision and w.decision.status.value == status]

        return {
            "approvals": [
                {
                    "workflow_id": w.workflow_id,
                    "skill_name": w.request.skill_name,
                    "status": w.decision.status.value if w.decision else "pending",
                    "created_at": w.created_at.isoformat(),
                    "quality_score": w.request.quality_score,
                }
                for w in workflows
            ]
        }

    @app.post("/skills/create/approve/{workflow_id}")
    async def approve_skill(
        workflow_id: str,
        decision: dict,
    ) -> dict:
        """Step 6: Approve - HITL approval workflow."""
        from agentic_fleet.skills.approval import ApprovalStatus

        status = ApprovalStatus(decision.get("status", "pending"))
        feedback = decision.get("feedback", "")
        reviewed_by = decision.get("reviewed_by", "human")

        success = approval_store.record_decision(
            workflow_id=workflow_id,
            status=status,
            feedback=feedback,
            reviewed_by=reviewed_by,
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

        return {
            "workflow_id": workflow_id,
            "status": status.value,
            "message": f"Skill {status.value}",
        }

    # Hierarchical Taxonomy Endpoints

    @app.get("/skills/taxonomy")
    async def get_taxonomy() -> dict:
        """Get the skill taxonomy hierarchy."""
        from agentic_fleet.skills.models import SkillType

        taxonomy = {
            "types": [
                {
                    "type": SkillType.OPERATIONAL.value,
                    "description": "Skills that perform actions (data, tools, automation)",
                    "categories": [
                        {"name": "data_processing", "description": "Extract, transform, load data"},
                        {"name": "research", "description": "Search and discover information"},
                        {"name": "software_development", "description": "Code and development tasks"},
                    ],
                },
                {
                    "type": SkillType.COGNITIVE.value,
                    "description": "Skills that plan and reason",
                    "categories": [
                        {"name": "planning", "description": "Task decomposition and scheduling"},
                        {"name": "reasoning", "description": "Analysis and inference"},
                    ],
                },
                {
                    "type": SkillType.COMMUNICATION.value,
                    "description": "Skills that generate and synthesize",
                    "categories": [
                        {"name": "generation", "description": "Text and content creation"},
                        {"name": "synthesis", "description": "Summarization and translation"},
                    ],
                },
                {
                    "type": SkillType.DOMAIN.value,
                    "description": "Domain-specific expertise",
                    "categories": [
                        {"name": "technology", "description": "Tech stack expertise"},
                        {"name": "business", "description": "Business domain expertise"},
                        {"name": "science", "description": "Scientific domain expertise"},
                    ],
                },
            ]
        }
        return taxonomy

    @app.get("/skills/taxonomy/{skill_type}")
    async def get_taxonomy_by_type(skill_type: str) -> dict:
        """Get taxonomy for a specific skill type."""
        from agentic_fleet.skills.models import SkillType

        try:
            st = SkillType(skill_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid skill type: {skill_type}")

        # Return filtered taxonomy
        all_taxonomy = {
            SkillType.OPERATIONAL.value: {
                "type": SkillType.OPERATIONAL.value,
                "categories": ["data_processing", "research", "software_development"],
            },
            SkillType.COGNITIVE.value: {
                "type": SkillType.COGNITIVE.value,
                "categories": ["planning", "reasoning"],
            },
            SkillType.COMMUNICATION.value: {
                "type": SkillType.COMMUNICATION.value,
                "categories": ["generation", "synthesis"],
            },
            SkillType.DOMAIN.value: {
                "type": SkillType.DOMAIN.value,
                "categories": ["technology", "business", "science"],
            },
        }

        return all_taxonomy.get(skill_type, {})

    # Memory Search Endpoints

    @app.post("/skills/memory/search")
    async def search_skills(request: dict) -> dict:
        """Search skills in memory based on task description."""
        from agentic_fleet.skills.memory import skill_retrieval_service

        task_description = request.get("task_description", "")
        task_type = request.get("task_type")
        available_skills = request.get("available_skills")
        top_k = request.get("top_k", 5)

        results = skill_retrieval_service.retrieve_for_task(
            task_description=task_description,
            task_type=task_type,
            available_skills=available_skills,
            top_k=top_k,
        )

        return {"results": results}

    @app.get("/skills/memory/index")
    async def get_memory_index() -> dict:
        """Get the current skill memory index."""
        from agentic_fleet.skills.memory import skill_memory_store

        indexes = skill_memory_store.list_all()
        return {
            "indexes": [
                {
                    "skill_id": idx.skill_id,
                    "hierarchical_path": idx.hierarchical_path,
                    "keywords": idx.keywords,
                    "capability_tags": idx.capability_tags,
                    "usage_count": idx.usage_count,
                    "success_rate": idx.success_rate,
                }
                for idx in indexes
            ]
        }

    @app.post("/skills/memory/index")
    async def index_skill(request: dict) -> dict:
        """Index a skill in memory."""
        from agentic_fleet.skills.memory import skill_memory_store
        from agentic_fleet.skills.manager import SkillManager

        skill_id = request.get("skill_id")
        team_id = request.get("team_id")

        manager = SkillManager()
        skill = manager.get_skill(skill_id, team_id)

        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

        index = skill_memory_store.index_skill(skill)
        return {
            "skill_id": skill_id,
            "hierarchical_path": index.hierarchical_path,
            "keywords": index.keywords,
        }

    # Skill Retrieval by Hierarchy

    @app.get("/skills/hierarchy/{skill_type}/{category}")
    async def get_skills_by_hierarchy(
        skill_type: str,
        category: str,
    ) -> dict:
        """Get skills by hierarchy path."""
        from agentic_fleet.skills.memory import skill_memory_store
        from agentic_fleet.skills.models import SkillType

        try:
            st = SkillType(skill_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid skill type: {skill_type}")

        indexes = skill_memory_store.search_by_hierarchy(
            skill_type=st,
            category=category,
        )

        return {
            "skill_type": skill_type,
            "category": category,
            "skills": [idx.skill_id for idx in indexes],
        }

    return app


app = create_app()
