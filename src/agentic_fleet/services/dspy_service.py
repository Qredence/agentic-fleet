"""DSPy operations service for AgenticFleet API.

Provides business logic for DSPy module operations including compilation,
caching, and introspection.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any

import dspy

from agentic_fleet.utils.compiler import clear_cache, get_cache_info
from agentic_fleet.workflows.supervisor import SupervisorWorkflow

logger = logging.getLogger(__name__)


class DSPyService:
    """Service for DSPy operations.

    Encapsulates business logic for DSPy-related operations,
    separated from HTTP handling concerns.
    """

    def __init__(self, workflow: SupervisorWorkflow) -> None:
        self.workflow = workflow

    def get_predictor_prompts(self) -> dict[str, Any]:
        """Extract prompts from all DSPy predictors."""
        if not self.workflow.dspy_reasoner:
            raise ValueError("DSPy reasoner not available")

        prompts: dict[str, Any] = {}

        # Check if named_predictors is available
        if not hasattr(self.workflow.dspy_reasoner, "named_predictors"):
            return {"error": "DSPy reasoner does not support introspection"}

        for name, predictor in self.workflow.dspy_reasoner.named_predictors():
            signature = getattr(predictor, "signature", None)
            if not signature:
                continue

            instructions = getattr(signature, "instructions", "")

            inputs: list[dict[str, str]] = []
            outputs: list[dict[str, str]] = []

            # Handle fields (DSPy 2.5+ uses model_fields or fields)
            fields = getattr(signature, "fields", {})
            if not fields and hasattr(signature, "__annotations__"):
                fields = signature.__annotations__

            for field_name, field in fields.items():
                desc = ""
                prefix = ""

                # Try json_schema_extra (Pydantic v2)
                if hasattr(field, "json_schema_extra"):
                    extra = field.json_schema_extra or {}
                    if isinstance(extra, dict):
                        desc = extra.get("desc", "") or extra.get("description", "")
                        prefix = extra.get("prefix", "")

                # Try metadata (Pydantic v1/Field)
                if not desc and hasattr(field, "description"):
                    desc = field.description

                # Try dspy.InputField/OutputField attributes
                if not prefix and hasattr(field, "prefix"):
                    prefix = field.prefix

                field_info = {"name": field_name, "desc": str(desc), "prefix": str(prefix)}

                if hasattr(signature, "input_fields") and field_name in signature.input_fields:
                    inputs.append(field_info)
                elif hasattr(signature, "output_fields") and field_name in signature.output_fields:
                    outputs.append(field_info)
                else:
                    inputs.append(field_info)

            demos: list[dict[str, str]] = []
            if hasattr(predictor, "demos"):
                demos_list = getattr(predictor, "demos", None) or []
                for demo in demos_list:
                    demo_dict: dict[str, str] = {}
                    try:
                        for k, v in demo.items():
                            demo_dict[str(k)] = str(v)
                    except Exception as exc:
                        logger.warning("Malformed demo skipped: %s", exc)
                    demos.append(demo_dict)

            prompts[name] = {
                "instructions": instructions,
                "inputs": inputs,
                "outputs": outputs,
                "demos_count": len(demos),
                "demos": demos,
            }

        return prompts

    def get_config(self) -> dict[str, Any]:
        """Get current DSPy configuration."""
        lm_info = "unknown"
        if hasattr(dspy.settings, "lm") and dspy.settings.lm:
            lm_info = str(dspy.settings.lm)
            if hasattr(dspy.settings.lm, "model"):
                lm_info = f"{dspy.settings.lm.__class__.__name__}(model={dspy.settings.lm.model})"

        return {
            "lm_provider": lm_info,
            "adapter": str(dspy.settings.adapter)
            if hasattr(dspy.settings, "adapter") and dspy.settings.adapter
            else "default",
        }

    def get_stats(self) -> dict[str, Any]:
        """Get DSPy usage statistics."""
        lm = getattr(dspy.settings, "lm", None)
        history_count = 0
        if lm and hasattr(lm, "history"):
            history_count = len(lm.history)
        return {"history_count": history_count}

    def get_cache_info(self) -> dict[str, Any] | None:
        """Get compilation cache information."""
        return get_cache_info()

    def clear_cache(self) -> None:
        """Clear compilation cache artifacts."""
        clear_cache()

    def get_reasoner_summary(self) -> dict[str, Any]:
        """Get reasoner execution summary."""
        if not self.workflow.dspy_reasoner:
            return {
                "history_count": 0,
                "routing_cache_size": 0,
                "use_typed_signatures": False,
                "modules_initialized": False,
            }

        summary = self.workflow.dspy_reasoner.get_execution_summary()
        return {
            "history_count": summary.get("history_count", 0),
            "routing_cache_size": summary.get("routing_cache_size", 0),
            "use_typed_signatures": summary.get("use_typed_signatures", False),
            "modules_initialized": True,
        }

    def clear_routing_cache(self) -> None:
        """Clear reasoner routing cache."""
        if not self.workflow.dspy_reasoner:
            raise ValueError("DSPy reasoner not available")
        self.workflow.dspy_reasoner.clear_routing_cache()

    def list_signatures(self) -> dict[str, Any]:
        """List all available DSPy signatures."""
        signatures_info: dict[str, Any] = {}

        try:
            from agentic_fleet.dspy_modules import (
                answer_quality,
                handoff_signatures,
                nlu_signatures,
                signatures,
            )

            modules = [signatures, handoff_signatures, nlu_signatures, answer_quality]
            for module in modules:
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, dspy.Signature)
                        and obj != dspy.Signature
                    ):
                        instructions = getattr(obj, "instructions", "") or getattr(
                            obj, "__doc__", ""
                        )
                        input_fields: list[str] = []
                        output_fields: list[str] = []

                        if hasattr(obj, "input_fields"):
                            input_fields = list(obj.input_fields.keys())
                        if hasattr(obj, "output_fields"):
                            output_fields = list(obj.output_fields.keys())

                        signatures_info[name] = {
                            "name": name,
                            "type": "dspy.Signature",
                            "instructions": instructions.strip() if instructions else None,
                            "input_fields": input_fields,
                            "output_fields": output_fields,
                        }
        except Exception as exc:
            logger.error("Failed to list signatures: %s", exc)

        return signatures_info

    async def compile_module_async(
        self,
        module_name: str,
        use_cache: bool = True,
        optimizer: str = "bootstrap",
    ) -> dict[str, Any]:
        """Compile a single DSPy module asynchronously.

        Phase 4: Individual module compilation API for parallel execution.

        Args:
            module_name: Name of module to compile ('reasoner', 'quality', 'nlu')
            use_cache: Whether to use cached compilation if available
            optimizer: Optimizer to use ('bootstrap', 'gepa')

        Returns:
            Compilation result with cache path and status

        Raises:
            ValueError: If module_name is invalid
        """
        from agentic_fleet.utils.compiler import (
            compile_answer_quality,
            compile_nlu,
            compile_reasoner,
        )
        from agentic_fleet.utils.progress import NullProgressCallback

        valid_modules = {"reasoner", "quality", "nlu"}
        if module_name not in valid_modules:
            raise ValueError(
                f"Invalid module_name '{module_name}'. Must be one of: {', '.join(valid_modules)}"
            )

        logger.info("Starting async compilation for module: %s", module_name)

        def _compile_sync() -> dict[str, Any]:
            """Synchronous compilation wrapper for executor."""
            callback = NullProgressCallback()

            if module_name == "reasoner":
                if not self.workflow.dspy_reasoner:
                    raise ValueError("DSPy reasoner not available")

                result = compile_reasoner(
                    self.workflow.dspy_reasoner,
                    use_cache=use_cache,
                    optimizer=optimizer,
                    progress_callback=callback,
                )
                return {
                    "module": module_name,
                    "cache_path": ".var/cache/dspy/compiled_reasoner.json",
                    "status": "completed",
                    "compiled": result is not None,
                }

            elif module_name == "quality":
                result = compile_answer_quality(
                    use_cache=use_cache,
                    progress_callback=callback,
                )
                return {
                    "module": module_name,
                    "cache_path": ".var/logs/compiled_answer_quality.pkl",
                    "status": "completed",
                    "compiled": result is not None,
                }

            elif module_name == "nlu":
                result = compile_nlu(
                    use_cache=use_cache,
                    progress_callback=callback,
                )
                return {
                    "module": module_name,
                    "cache_path": ".var/logs/compiled_nlu.pkl",
                    "status": "completed",
                    "compiled": result is not None,
                }

            raise ValueError(f"Unexpected module name: {module_name}")

        # Run compilation in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _compile_sync)
        logger.info("Completed async compilation for module: %s", module_name)
        return result

    async def compile_modules_parallel(
        self,
        modules: list[str],
        use_cache: bool = True,
        optimizer: str = "bootstrap",
    ) -> list[dict[str, Any]]:
        """Compile multiple DSPy modules in parallel.

        Phase 4: Parallel module compilation for faster optimization.

        Args:
            modules: List of module names to compile
            use_cache: Whether to use cached compilation if available
            optimizer: Optimizer to use

        Returns:
            List of compilation results, one per module
        """
        logger.info("Starting parallel compilation for modules: %s", modules)

        # Create compilation tasks
        tasks = [self.compile_module_async(module, use_cache, optimizer) for module in modules]

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    {
                        "module": modules[i],
                        "status": "failed",
                        "error": str(result),
                    }
                )
            else:
                final_results.append(result)

        logger.info("Completed parallel compilation for %d modules", len(modules))
        return final_results


__all__ = ["DSPyService"]
