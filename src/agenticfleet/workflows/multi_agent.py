"""
Custom multi-agent workflow implementation for coordinating specialized agents.

This module defines a custom workflow class to orchestrate multiple agents
(Orchestrator, Researcher, Coder, Analyst) for complex tasks. The workflow
logic is implemented independently and does not use the official Microsoft Agent
Framework's built-in workflow orchestration patterns.
Agents may be based on the Microsoft Agent Framework, but the orchestration is custom.
"""

from typing import Any

from agenticfleet.agents import (
    create_analyst_agent,
    create_coder_agent,
    create_orchestrator_agent,
    create_researcher_agent,
)
from agenticfleet.config import settings
from agenticfleet.core.exceptions import WorkflowError


class MultiAgentWorkflow:
    """
    Sequential multi-agent workflow orchestrator.

    Uses the orchestrator agent to coordinate task delegation to specialized
    agents (researcher, coder, analyst) based on the official Python Agent
    Framework pattern.
    """

    def __init__(self) -> None:
        """Initialize workflow with all agent participants."""
        self.orchestrator = create_orchestrator_agent()
        self.researcher = create_researcher_agent()
        self.coder = create_coder_agent()
        self.analyst = create_analyst_agent()

        # Execution limits from config
        workflow_config = settings.workflow_config.get("workflow", {})
        self.max_rounds = workflow_config.get("max_rounds", 10)
        self.max_stalls = workflow_config.get("max_stalls", 3)
        self.current_round = 0
        self.stall_count = 0
        self.last_response: str | None = None

    async def run(self, user_input: str) -> str:
        """
        Execute workflow by routing user input through orchestrator.

        The orchestrator analyzes the request and delegates to appropriate
        specialized agents as needed. Uses sequential execution pattern
        from official Agent Framework.

        Args:
            user_input: User's request or query

        Returns:
            str: Final response from the orchestrator

        Raises:
            WorkflowError: If max rounds or stalls exceeded
        """
        self.current_round = 0
        self.stall_count = 0
        self.last_response = None

        # Create context with available agents
        context = {
            "available_agents": {
                "researcher": "Performs web searches and data gathering",
                "coder": "Writes, executes, and debugs code",
                "analyst": "Analyzes data and generates insights",
            },
            "user_query": user_input,
        }

        while self.current_round < self.max_rounds:
            self.current_round += 1

            try:
                # Orchestrator decides next action
                result = await self.orchestrator.run(
                    f"Round {self.current_round}/{self.max_rounds}\n"
                    f"User Query: {user_input}\n"
                    f"Context: {context}\n"
                    f"Previous Response: {self.last_response or 'None'}\n\n"
                    "Analyze the request and either:\n"
                    "1. Provide a final answer if no delegation needed\n"
                    "2. Delegate to researcher/coder/analyst if more work needed\n"
                    "3. Synthesize results if subtasks complete"
                )

                response_text = result.content if hasattr(result, "content") else str(result)

                # Check for stalling (identical responses)
                if response_text == self.last_response:
                    self.stall_count += 1
                    if self.stall_count >= self.max_stalls:
                        return (
                            f"Workflow stalled after {self.stall_count} identical responses. "
                            f"Last response:\n{response_text}"
                        )
                else:
                    self.stall_count = 0

                self.last_response = response_text

                # Check if orchestrator delegated to another agent
                if "DELEGATE:" in response_text:
                    # Parse delegation instruction
                    agent_response = await self._handle_delegation(response_text, context)
                    context["last_delegation_result"] = agent_response
                    continue

                # Check if orchestrator provided final answer
                if "FINAL_ANSWER:" in response_text or self.current_round == self.max_rounds:
                    return response_text

            except Exception as e:
                raise WorkflowError(f"Error in workflow round {self.current_round}: {str(e)}")

        return f"Max rounds ({self.max_rounds}) reached. Last response:\n{self.last_response}"

    async def _handle_delegation(self, orchestrator_response: str, context: dict[str, Any]) -> str:
        """
        Handle delegation from orchestrator to specialized agent.

        Args:
            orchestrator_response: Response containing delegation instruction
            context: Current workflow context

        Returns:
            str: Response from delegated agent
        """
        # Parse delegation (format: "DELEGATE: <agent_name> - <task>")
        delegation_lines = [
            line for line in orchestrator_response.split("\n") if line.startswith("DELEGATE:")
        ]
        if not delegation_lines:
            return "Error: Could not parse delegation instruction"

        delegation_line = delegation_lines[0]
        parts = delegation_line.replace("DELEGATE:", "").strip().split(" - ", 1)
        agent_name = parts[0].strip().lower() if parts else ""
        task = parts[1].strip() if len(parts) > 1 else context.get("user_query", "")

        # Route to appropriate agent
        agent_map = {"researcher": self.researcher, "coder": self.coder, "analyst": self.analyst}

        if agent_name not in agent_map:
            return f"Error: Unknown agent '{agent_name}'"

        agent = agent_map[agent_name]
        try:
            result = await agent.run(task)
            return getattr(result, "content", str(result))
        except Exception as e:
            return f"Error: Agent '{agent_name}' failed to execute task: {str(e)}"


# Create default workflow instance
workflow = MultiAgentWorkflow()
