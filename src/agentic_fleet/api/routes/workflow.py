import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from agentic_fleet.agents import get_default_agent_metadata
from agentic_fleet.api.models import (
    AgentInfo,
    AgentListResponse,
    HistoryEntry,
    HistoryResponse,
    OptimizationRequest,
    OptimizationResult,
    SelfImprovementRequest,
    SelfImprovementResponse,
    WorkflowRequest,
    WorkflowResponse,
)
from agentic_fleet.cli.runner import WorkflowRunner
from agentic_fleet.utils.history_manager import HistoryManager
from agentic_fleet.utils.self_improvement import SelfImprovementEngine
from agentic_fleet.workflows.config import WorkflowConfig
from agentic_fleet.workflows.supervisor_workflow import create_supervisor_workflow

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory store for job status (replace with DB in production)
jobs: dict[str, Any] = {}


@router.post("/run", response_model=WorkflowResponse, status_code=status.HTTP_200_OK)
async def run_workflow(request: WorkflowRequest):
    """
    Execute a workflow for a given task.
    """
    start_time = time.time()
    workflow_id = str(uuid.uuid4())

    try:
        # Create configuration
        config_dict = request.config or {}
        workflow_config = WorkflowConfig(**config_dict)

        # Create and run workflow
        workflow = await create_supervisor_workflow(config=workflow_config)
        result = await workflow.run(request.task)

        execution_time = time.time() - start_time

        # Extract quality score safely
        quality_data = result.get("quality", {})
        score = 0.0
        if hasattr(quality_data, "score"):
            score = float(quality_data.score)
        elif isinstance(quality_data, dict):
            score = float(quality_data.get("score", 0.0))

        response = WorkflowResponse(
            workflow_id=workflow_id,
            status="completed",
            result=str(result.get("result", "")),
            quality_score=score,
            execution_time_seconds=execution_time,
            metadata=result.get("metadata", {}),
        )
        return response

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {e!s}",
        ) from e


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = Query(20, description="Number of entries to return"),
    min_quality: float = Query(0.0, description="Minimum quality score filter"),
):
    """
    Retrieve execution history.
    """
    try:
        history_manager = HistoryManager()
        history = history_manager.load_history(limit=limit)

        entries = []
        for item in history:
            quality = item.get("quality", {})
            score = 0.0
            if isinstance(quality, dict):
                score = float(quality.get("score", 0.0))
            elif hasattr(quality, "score"):
                score = float(quality.score)

            if score < min_quality:
                continue

            entries.append(
                HistoryEntry(
                    workflow_id=item.get("workflowId", "unknown"),
                    task=item.get("task", ""),
                    result=str(item.get("result", "")),
                    quality_score=score,
                    total_time_seconds=float(item.get("total_time_seconds", 0.0)),
                    timestamp=item.get("timestamp", item.get("start_time", "")),
                )
            )

        return HistoryResponse(history=entries, total=len(entries))
    except Exception as e:
        logger.error(f"Failed to retrieve history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {e!s}",
        ) from e


@router.post("/self-improve", response_model=SelfImprovementResponse)
async def trigger_self_improvement(request: SelfImprovementRequest):
    """
    Trigger self-improvement process to learn from history.
    """
    try:
        engine = SelfImprovementEngine(
            min_quality_score=request.min_quality, max_examples_to_add=request.max_examples
        )

        # Run improvement logic (synchronously for now, could be async/background)
        # Note: auto_improve might take time, ideally should be background task if large history
        added, status_msg = engine.auto_improve()

        return SelfImprovementResponse(
            added_count=added,
            status="success" if added > 0 else "no_change",
            details={"message": status_msg},
        )
    except Exception as e:
        logger.error(f"Self-improvement failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Self-improvement failed: {e!s}",
        ) from e


@router.post("/optimize", response_model=OptimizationResult, status_code=status.HTTP_202_ACCEPTED)
async def start_optimization(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """
    Trigger a self-improvement/optimization run (GEPA/DSPy compilation).
    Runs in background.
    """
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending", "request": request.model_dump()}

    background_tasks.add_task(run_optimization_task, job_id, request)

    return OptimizationResult(
        optimization_id=job_id,
        status="pending",
        compiled_avg_time=None,
        uncompiled_avg_time=None,
        improvement_percentage=None,
        details={"message": "Optimization started in background"},
    )


@router.get("/optimize/{job_id}", response_model=OptimizationResult)
async def get_optimization_status(job_id: str):
    """
    Check status of an optimization run.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return OptimizationResult(
        optimization_id=job_id,
        status=job["status"],
        compiled_avg_time=job.get("compiled_avg_time"),
        uncompiled_avg_time=job.get("uncompiled_avg_time"),
        improvement_percentage=job.get("improvement_percentage"),
        details=job.get("details", {}),
    )


async def run_optimization_task(job_id: str, request: OptimizationRequest):
    """
    Background task logic for optimization (simulating cli benchmark).
    """
    try:
        jobs[job_id]["status"] = "running"

        # Reuse WorkflowRunner logic but adapted for non-CLI
        results: dict[str, list[float]] = {"compiled": [], "uncompiled": []}

        # 1. Compiled Run
        if request.compile_dspy:
            runner_compiled = WorkflowRunner()
            await runner_compiled.initialize_workflow(compile_dspy=True)
            for _ in range(request.iterations):
                start = time.time()
                await runner_compiled.run_without_streaming(request.task)
                results["compiled"].append(time.time() - start)

        # 2. Uncompiled Run
        runner_uncompiled = WorkflowRunner()
        await runner_uncompiled.initialize_workflow(compile_dspy=False)
        for _ in range(request.iterations):
            start = time.time()
            await runner_uncompiled.run_without_streaming(request.task)
            results["uncompiled"].append(time.time() - start)

        # Calculate metrics
        avg_compiled = (
            sum(results["compiled"]) / len(results["compiled"]) if results["compiled"] else None
        )
        avg_uncompiled = (
            sum(results["uncompiled"]) / len(results["uncompiled"])
            if results["uncompiled"]
            else None
        )

        improvement = 0.0
        if avg_compiled and avg_uncompiled:
            improvement = ((avg_uncompiled - avg_compiled) / avg_uncompiled) * 100

        jobs[job_id].update(
            {
                "status": "completed",
                "compiled_avg_time": avg_compiled,
                "uncompiled_avg_time": avg_uncompiled,
                "improvement_percentage": improvement,
                "details": {"results": results},
            }
        )

    except Exception as e:
        logger.error(f"Optimization task failed: {e}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["details"] = {"error": str(e)}


@router.get("/agents", response_model=AgentListResponse)
async def list_agents():
    """

    List available agents and their capabilities.

    """

    agent_metadata = get_default_agent_metadata()

    agent_list = [AgentInfo(**agent) for agent in agent_metadata]

    return AgentListResponse(agents=agent_list)
