"""Fleet-native workflow entrypoints.

This module exposes the public ``SupervisorWorkflow`` class used by the CLI and
tests, while delegating the main implementation to the fleet adapter.  It also
re-exports a ``compile_supervisor`` symbol for backward-compatibility with
legacy lazy-compilation tests.
"""

from __future__ import annotations

from ..utils.compiler import compile_supervisor as _compile_supervisor
from .config import WorkflowConfig
from .fleet.adapter import SupervisorWorkflow as _FleetSupervisorWorkflow
from .fleet.adapter import create_fleet_workflow
from .initialization import initialize_workflow_context

# Public entrypoint used throughout the codebase/tests
SupervisorWorkflow = _FleetSupervisorWorkflow


# Legacy tests patch ``agentic_fleet.workflows.supervisor_workflow.compile_supervisor``
# directly.  Re-export the real implementation here so patches continue to
# work as expected while newer code relies on the utilities in
# ``utils.compiler`` and ``workflows.compilation``.
def compile_supervisor(*args, **kwargs):  # type: ignore[override]
    """Compatibility shim delegating to :func:`utils.compiler.compile_supervisor`.

    Tests patch this symbol in this module; production code simply forwards to
    the real compiler implementation.
    """

    return _compile_supervisor(*args, **kwargs)


async def create_supervisor_workflow(
    *,
    compile_dspy: bool = True,
    config: WorkflowConfig | None = None,
) -> _FleetSupervisorWorkflow:
    """Create and initialize the fleet workflow.

    This is the preferred entrypoint for the application.  It wires the
    ``SupervisorContext`` via :func:`initialize_workflow_context` and then
    delegates to :func:`create_fleet_workflow` to build the
    agent-framework-based workflow.
    """

    context = await initialize_workflow_context(config=config, compile_dspy=compile_dspy)
    return await create_fleet_workflow(context=context, compile_dspy=compile_dspy)
