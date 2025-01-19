"""Message models and types for agent communication.

This module defines strongly-typed message models for agent communication,
including structured responses, plans, thoughts, and errors.

Example:
    ```python
    from messages import create_message
    
    # Create an agent message
    msg = create_message(
        message_type="agent",
        content="Task completed successfully",
        source="WebSurfer",
        target="Coder"
    )
    ```
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, validator

MessageType = Literal["agent", "plan", "thought", "dialog", "code", "error"]

class BaseMessage(BaseModel):
    """Base class for all message types with common fields."""
    content: str = Field(..., description="The main content of the message")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    message_type: MessageType = Field(..., description="Type of message")

    @validator("timestamp")
    def validate_timestamp(cls, v: str) -> str:
        """Ensure timestamp is in ISO format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Timestamp must be in ISO format")

class AgentMessage(BaseMessage):
    """Message from an agent with source and target information."""
    source: str = Field(..., description="The agent that created this message")
    target: Optional[str] = Field(default=None, description="The intended recipient agent")
    priority: Optional[int] = Field(default=0, ge=0, le=10, description="Message priority (0-10)")

class PlanMessage(BaseMessage):
    """Structured plan for task execution with steps and timing."""
    title: str = Field(..., min_length=1, description="Title of the plan")
    description: str = Field(..., min_length=10, description="Detailed description of what will be done")
    steps: List[str] = Field(..., min_items=1, description="Ordered list of steps to execute")
    estimated_time: Optional[str] = Field(default=None, description="Estimated time to complete")
    dependencies: Optional[List[str]] = Field(default_factory=list, description="Required dependencies")
    status: str = Field(default="pending", description="Current status of the plan")

    @validator("steps")
    def validate_steps(cls, v: List[str]) -> List[str]:
        """Ensure steps are not empty strings."""
        if any(not step.strip() for step in v):
            raise ValueError("Steps cannot be empty strings")
        return v

class ThoughtMessage(BaseMessage):
    """Internal reasoning and thought process with confidence metrics."""
    reasoning: str = Field(..., min_length=10, description="The reasoning or thought process")
    observations: List[str] = Field(..., description="List of relevant observations")
    next_steps: List[str] = Field(..., description="Planned next steps")
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Confidence level in the reasoning (0.0-1.0)"
    )

    @validator("confidence")
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        """Validate confidence is between 0 and 1."""
        if v is not None and not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v

class DialogMessage(BaseMessage):
    """Conversational message with context and emotion tracking."""
    speaker: str = Field(..., min_length=1, description="The speaker/source of the dialog")
    utterance: str = Field(..., min_length=1, description="The actual spoken/written content")
    context: Optional[str] = Field(default=None, description="Context of the conversation")
    emotion: Optional[str] = Field(
        default=None,
        description="Emotional tone of the message",
        regex="^(neutral|happy|sad|angry|confused|surprised)$"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the dialog occurred"
    )

class CodeMessage(BaseMessage):
    """Code-related message with language and execution context."""
    language: str = Field(..., regex="^[a-zA-Z0-9+#]+$", description="Programming language")
    code: str = Field(..., min_length=1, description="The actual code content")
    explanation: Optional[str] = Field(default=None, description="Explanation of the code")
    file_path: Optional[str] = Field(default=None, description="Related file path")
    version: Optional[str] = Field(default=None, description="Version or commit reference")
    requires_execution: bool = Field(default=False, description="Whether code needs to be run")

class ErrorMessage(BaseMessage):
    """Detailed error message with severity and resolution hints."""
    error_type: str = Field(..., description="Type or category of error")
    message: str = Field(..., min_length=1, description="Error message or description")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Error details")
    traceback: Optional[str] = Field(default=None, description="Error traceback if available")
    severity: str = Field(
        default="error",
        regex="^(debug|info|warning|error|critical)$",
        description="Error severity level"
    )
    resolution_hints: Optional[List[str]] = Field(
        default_factory=list,
        description="Suggested steps to resolve the error"
    )

# Message type definitions
AnyMessage = Union[AgentMessage, PlanMessage, ThoughtMessage, DialogMessage, CodeMessage, ErrorMessage]
MESSAGE_CLASSES: Dict[str, type] = {
    "agent": AgentMessage,
    "plan": PlanMessage,
    "thought": ThoughtMessage,
    "dialog": DialogMessage,
    "code": CodeMessage,
    "error": ErrorMessage
}

def create_message(message_type: MessageType, content: str, **kwargs: Any) -> AnyMessage:
    """Create a strongly-typed message instance.

    Args:
        message_type: Type of message to create
        content: Main message content
        **kwargs: Additional arguments for the specific message type

    Returns:
        An instance of the appropriate message class

    Raises:
        ValueError: If message_type is not recognized or validation fails

    Example:
        ```python
        error_msg = create_message(
            message_type="error",
            content="Failed to process request",
            error_type="ValidationError",
            severity="critical"
        )
        ```
    """
    if message_type not in MESSAGE_CLASSES:
        raise ValueError(f"Unknown message type: {message_type}")

    # Ensure message_type is included in kwargs
    kwargs['message_type'] = message_type

    try:
        return MESSAGE_CLASSES[message_type](content=content, **kwargs)
    except Exception as err:
        raise ValueError(f"Failed to create {message_type} message: {str(err)}") from err
