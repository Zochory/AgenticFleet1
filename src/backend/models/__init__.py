"""
Models package initialization.
"""

from .azure_client import create_azure_client
from .config import GPT4_CONFIG, AZURE_GPT4_CONFIG
from .messages import (
    BaseMessage,
    AgentMessage,
    PlanMessage,
    ThoughtMessage,
    DialogMessage,
    CodeMessage,
    ErrorMessage,
    create_message,
    AnyMessage
)
from .logging import team_logger, system_logger

__all__ = [
    'create_azure_client',
    'GPT4_CONFIG',
    'AZURE_GPT4_CONFIG',
    'BaseMessage',
    'AgentMessage',
    'PlanMessage',
    'ThoughtMessage',
    'DialogMessage',
    'CodeMessage',
    'ErrorMessage',
    'create_message',
    'AnyMessage',
    'team_logger',
    'system_logger'
] 