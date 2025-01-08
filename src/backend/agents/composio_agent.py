# filename: composio_agent.py

"""
Composio Agent Implementation for AutoGen AgentChat (dev13)

This script defines a "Composio Agent" that is compatible with the
autogen_agentchat==0.4.0.dev13 framework. The Composio Agent utilizes the modular
architecture enabled by AgentChat, interacting through standardized attributes 
and methods such as `name`, `description`, `on_messages()`, `on_messages_stream()` 
and `on_reset()`.

Features:
- The agent supports stateful conversations.
- Processes input via a conversation backbone using `ChatMessage` instances.
- Resets its behavior/session via the `on_reset()` method.
- Provides both synchronous and streaming interfaces for responses.
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from typing import Iterator, Sequence, Optional

class ComposioAgent(AssistantAgent):
    """
    The ComposioAgent is a custom implementation of an AssistantAgent within the AgentChat framework.
    """
    def __init__(
        self,
        name: str,
        model_client,
        description: Optional[str] = None,
    ):
        """
        Initialize the ComposioAgent.

        Args:
            name (str): Unique name for the agent.
            model_client: The model client to use for generating responses.
            description (str, optional): Description of what the agent does.
        """
        super().__init__(
            name=name,
            system_message=description or "I am a helpful assistant that processes messages and maintains state.",
            model_client=model_client,
        )
        self.state = {}  # Stores stateful information between conversations.

    async def on_message(self, message: ChatMessage, cancellation_token: Optional[CancellationToken] = None) -> ChatMessage:
        """Process a single incoming message."""
        response_content = f"Composio Agent received your message: {message.content}"
        self.state["last_message"] = message.content
        return TextMessage(source=self.name, content=response_content)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: Optional[CancellationToken] = None) -> ChatMessage:
        """Process a sequence of messages."""
        if not messages:
            return TextMessage(source=self.name, content="No messages received.")
        return await self.on_message(messages[-1], cancellation_token)

    def on_reset(self):
        """Reset the agent's state."""
        self.state.clear()
        print(f"ComposioAgent '{self.name}' has been reset.")