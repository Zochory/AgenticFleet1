"""
Message models and types for agent communication.

This module defines the message types used for communication between agents,
including structured responses, plans, thoughts, and errors.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class BaseMessage(BaseModel):
    """Base class for all message types."""
    content: str = Field(..., description="The main content of the message")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class AgentMessage(BaseMessage):
    """Message from an agent."""
    source: str = Field(..., description="The agent that created this message")
    target: Optional[str] = Field(default=None, description="The intended recipient agent")
    message_type: str = Field(default="text", description="Type of message (text, code, error, etc)")

class PlanMessage(BaseMessage):
    """Structured plan for task execution."""
    title: str = Field(..., description="Title of the plan")
    description: str = Field(..., description="Detailed description of what will be done")
    steps: List[str] = Field(..., description="Ordered list of steps to execute")
    estimated_time: Optional[str] = Field(default=None, description="Estimated time to complete")
    dependencies: Optional[List[str]] = Field(default=None, description="Required dependencies or prerequisites")

class ThoughtMessage(BaseMessage):
    """Internal reasoning and thought process."""
    reasoning: str = Field(..., description="The reasoning or thought process")
    observations: List[str] = Field(..., description="List of relevant observations")
    next_steps: List[str] = Field(..., description="Planned next steps")
    confidence: Optional[float] = Field(default=None, description="Confidence level in the reasoning")

class DialogMessage(BaseMessage):
    """Conversational message or dialog."""
    speaker: str = Field(..., description="The speaker/source of the dialog")
    utterance: str = Field(..., description="The actual spoken/written content")
    context: Optional[str] = Field(default=None, description="Context of the conversation")
    emotion: Optional[str] = Field(default=None, description="Emotional tone of the message")

class CodeMessage(BaseMessage):
    """Code-related message."""
    language: str = Field(..., description="Programming language of the code")
    code: str = Field(..., description="The actual code content")
    explanation: Optional[str] = Field(default=None, description="Explanation of the code")
    file_path: Optional[str] = Field(default=None, description="Related file path")

class ErrorMessage(BaseMessage):
    """Error or exception message."""
    error_type: str = Field(..., description="Type or category of error")
    message: str = Field(..., description="Error message or description")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    traceback: Optional[str] = Field(default=None, description="Error traceback if available")

# Type alias for any message type
AnyMessage = Union[
    AgentMessage,
    PlanMessage,
    ThoughtMessage,
    DialogMessage,
    CodeMessage,
    ErrorMessage
]

def create_message(
    message_type: str,
    content: str,
    **kwargs: Any
) -> AnyMessage:
    """
    Factory function to create a message of the specified type.
    
    Args:
        message_type: Type of message to create
        content: Main message content
        **kwargs: Additional arguments for the specific message type
    
    Returns:
        An instance of the appropriate message class
    
    Raises:
        ValueError: If message_type is not recognized
    """
    message_classes = {
        "agent": AgentMessage,
        "plan": PlanMessage,
        "thought": ThoughtMessage,
        "dialog": DialogMessage,
        "code": CodeMessage,
        "error": ErrorMessage
    }
    
    if message_type not in message_classes:
        raise ValueError(f"Unknown message type: {message_type}")
    
    return message_classes[message_type](content=content, **kwargs) 