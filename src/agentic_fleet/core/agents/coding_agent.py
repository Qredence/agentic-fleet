"""
Coding Agent Module.

This module implements an agent that generates, executes, and optimizes
code based on given tasks and requirements.
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Union

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage
from autogen_core import CancellationToken
from autogen_core.models import (
    CreateResult,
    RequestUsage,
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
)
from pydantic import BaseModel

from agentic_fleet.core.agents.base import BaseAgent
from agentic_fleet.core.tools.code_execution.code_execution_tool import (
    CodeBlock,
    ExecutionResult,
    CodeExecutionTool,
)

logger = logging.getLogger(__name__)


class CodingConfig(BaseModel):
    """Configuration for the Coding Agent."""

    max_iterations: int = 3
    max_execution_time: int = 30  # seconds
    generation_temperature: float = 0.7
    optimization_temperature: float = 0.8
    review_temperature: float = 0.6


class CodingAgent(BaseAgent):
    """
    An agent that generates, executes, and optimizes code based on tasks and requirements.
    """

    def __init__(
        self,
        name: str = "coding_agent",
        config: Optional[CodingConfig] = None,
        model_client: Optional[ChatCompletionClient] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the coding agent.

        Args:
            name: Name of the agent
            config: Configuration for the agent
            model_client: Model client for chat completion
            **kwargs: Additional arguments passed to BaseAgent
        """
        self._name = name
        super().__init__(
            name=name,
            model_client=model_client,
            **kwargs,
        )
        self.config = config or CodingConfig()
        self.code_execution_tool = CodeExecutionTool()

    async def process_message(self, message: str, token: CancellationToken = None) -> Response:
        """
        Process incoming messages and manage code operations.

        Args:
            message: Incoming chat message
            token: Cancellation token for the operation

        Returns:
            Response containing the operation result
        """
        try:
            # Parse the command and parameters from the message
            command, params = self._parse_message(message)

            if command == "generate":
                code = await self._generate_code(
                    params.get("task", ""),
                    params.get("requirements", {}),
                    params.get("context", {}),
                )
                return Response(content=str(code))

            elif command == "execute":
                result = await self._execute_code(params.get("code", ""), params.get("context", {}))
                return Response(content=str(result))

            elif command == "optimize":
                optimized = await self._optimize_code(
                    params.get("code", ""), params.get("metrics", []), params.get("context", {})
                )
                return Response(content=str(optimized))

            elif command == "review":
                review = await self._review_code(params.get("code", ""), params.get("context", {}))
                return Response(content=review)

            else:
                return Response(
                    content=f"Unknown command: {command}. Available commands: generate, execute, optimize, review",
                    error=True
                )

        except Exception as e:
            logger.error("Error processing code operation", exc_info=True)
            return Response(
                content=f"Error processing code operation: {str(e)}",
                error=True
            )

    async def generate_response(
        self,
        messages: Sequence[ChatMessage],
        token: CancellationToken = None,
        temperature: Optional[float] = None
    ) -> CreateResult:
        """
        Generate a response based on the message history.

        Args:
            messages: Sequence of messages in the conversation
            token: Cancellation token for the operation
            temperature: Optional temperature parameter for response generation

        Returns:
            CreateResult containing the generated response
        """
        # Pass temperature to model client if provided
        if temperature is not None and self._model_client:
            original_temp = getattr(self._model_client, 'temperature', None)
            self._model_client.temperature = temperature
            try:
                response = await super().on_messages(messages, token)
                return CreateResult(message=response.chat_message)
            finally:
                # Restore original temperature
                if original_temp is not None:
                    self._model_client.temperature = original_temp
        else:
            response = await super().on_messages(messages, token)
            return CreateResult(message=response.chat_message)

    async def _generate_code(
        self, task: str, requirements: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> CodeBlock:
        """
        Generate code based on task description and requirements.

        Args:
            task: Description of the coding task
            requirements: Specific requirements for the code
            context: Optional context information

        Returns:
            Generated code block
        """
        try:
            messages = [
                SystemMessage(content="Generate code based on the task and requirements."),
                UserMessage(content=f"Task: {task}\nRequirements: {requirements}\nContext: {context}", source="user"),
            ]

            result = await self.generate_response(
                messages, temperature=self.config.generation_temperature
            )

            return CodeBlock(
                code=result.message.content, language=self._detect_language(task, requirements)
            )

        except Exception as e:
            logger.error("Error generating code", exc_info=True)
            raise RuntimeError(f"Error generating code: {str(e)}") from e

    async def _execute_code(
        self, code: str, context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute a code block with safety checks.

        Args:
            code: Code to execute
            context: Optional execution context

        Returns:
            Result of code execution
        """
        try:
            code_block = CodeBlock(code=code, language=self._detect_language_from_code(code))

            result = await self.code_execution_tool.execute_code(code_block, context)

            return result

        except Exception as e:
            logger.error("Error executing code", exc_info=True)
            raise RuntimeError(f"Error executing code: {str(e)}") from e

    async def _optimize_code(
        self, code: str, metrics: List[str], context: Optional[Dict[str, Any]] = None
    ) -> CodeBlock:
        """
        Optimize code based on specified metrics.

        Args:
            code: Code to optimize
            metrics: List of metrics to optimize for
            context: Optional context information

        Returns:
            Optimized code block
        """
        try:
            messages = [
                SystemMessage(content="Optimize the code based on specified metrics."),
                UserMessage(content=f"Code: {code}\nMetrics: {metrics}\nContext: {context}", source="user"),
            ]

            result = await self.generate_response(
                messages, temperature=self.config.optimization_temperature
            )

            return CodeBlock(
                code=result.message.content, language=self._detect_language_from_code(code)
            )

        except Exception as e:
            logger.error("Error optimizing code", exc_info=True)
            raise RuntimeError(f"Error optimizing code: {str(e)}") from e

    async def _review_code(self, code: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Review code for quality, security, and best practices.

        Args:
            code: Code to review
            context: Optional context information

        Returns:
            Review comments and suggestions
        """
        try:
            messages = [
                SystemMessage(content="Review the code for quality, security, and best practices."),
                UserMessage(content=f"Code: {code}\nContext: {context}", source="user"),
            ]

            result = await self.generate_response(
                messages, temperature=self.config.review_temperature
            )

            return result.message.content

        except Exception as e:
            logger.error("Error reviewing code", exc_info=True)
            raise RuntimeError(f"Error reviewing code: {str(e)}") from e

    def _parse_message(self, content: str) -> tuple[str, Dict[str, Any]]:
        """
        Parse the command and parameters from a message.

        Args:
            content: Message content to parse

        Returns:
            Tuple of (command, parameters)
        """
        parts = content.split(maxsplit=1)
        command = parts[0].lower()
        params = {}

        if len(parts) > 1:
            param_text = parts[1]
            try:
                import json

                params = json.loads(param_text)
            except json.JSONDecodeError as ex:
                logger.debug(f"JSON decode failed: {ex}")
                params = {"content": param_text}
        return command, params

    def _improved_detect_language(self, text: str) -> str:
        """
        Improved language detection using langdetect.

        Args:
            text: Text to analyze

        Returns:
            Detected language as string (default is 'python')
        """
        try:
            from langdetect import detect_langs

            langs = detect_langs(text)
            if langs:
                return langs[0].lang
        except Exception:
            logger.error("Error in improved language detection", exc_info=True)
        return "python"

    def _detect_language(self, task: str, requirements: Dict[str, Any]) -> str:
        """
        Detect the programming language from task and requirements using keyword matching and improved detection as fallback.

        Args:
            task: Task description
            requirements: Task requirements

        Returns:
            Detected programming language
        """
        language_hints = {
            "python": ["python", "pip", "numpy", "pandas"],
            "javascript": ["javascript", "node", "npm", "react"],
            "typescript": ["typescript", "angular", "vue"],
            "java": ["java", "spring", "maven"],
            "go": ["golang", "go"],
        }
        combined_text = f"{task} {str(requirements)}".lower()
        for lang, hints in language_hints.items():
            if any(hint in combined_text for hint in hints):
                return lang
        # Fallback to improved detection
        return self._improved_detect_language(combined_text)

    def _detect_language_from_code(self, code: str) -> str:
        """
        Detect the programming language from code content using pattern matching.

        Args:
            code: Code content

        Returns:
            Detected programming language
        """
        language_patterns = {
            "python": ["def ", "import ", "class ", "print("],
            "javascript": ["function ", "const ", "let ", "var "],
            "typescript": ["interface ", "type ", "enum "],
            "java": ["public class ", "private ", "protected "],
            "go": ["func ", "package ", "import ("],
        }
        for lang, patterns in language_patterns.items():
            if any(pattern in code for pattern in patterns):
                return lang
        return "python"

    async def on_messages(self, messages: Sequence[ChatMessage]) -> Response:
        """
        Handle incoming messages and generate responses.

        Args:
            messages: Sequence of messages to process

        Returns:
            Response: The agent's response to the messages
        """
        if not messages:
            return Response(content="No messages to process")

        # For now, just process the last message
        last_message = messages[-1]
        response = await self.process_message(last_message.content)
        return Response(content=response if response else "Failed to process message")

    async def on_reset(self) -> None:
        """Reset the agent's state."""
        # No state to reset for now
        pass

    def produced_message_types(self) -> List[str]:
        """
        Get the types of messages this agent can produce.

        Returns:
            List[str]: List of supported message types
        """
        return ["text", "code"]
