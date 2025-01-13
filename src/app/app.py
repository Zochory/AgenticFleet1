import os
import asyncio
import aiohttp
import json
import pandas as pd
from typing import AsyncGenerator, List, Optional, Any, Dict 
import chainlit as cl
from autogen_ext.models.openai import OpenAIChatCompletionClient, AzureOpenAIChatCompletionClient
from autogen_agentchat.teams import MagenticOneGroupChat 
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_core.models import ChatCompletionClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai._openai_client import BaseOpenAIChatCompletionClient 
from magentic_one_helper import MagenticOneHelper

import re
from dotenv import load_dotenv

load_dotenv()

# Create the Azure OpenAI client from environment variables
az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    model=os.getenv("AZURE_OPENAI_MODEL"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

STREAM_DELAY = 0.01

@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> Optional[cl.User]:
    """
    Example OAuth callback that authenticates a user and returns a Chainlit User object.
    Adjust the logic here based on your actual OAuth provider or authentication flow.
    """
    # Always returning default_user for this example
    return default_user

@cl.on_chat_start
async def start_chat():
    """
    Initializes a multi-agent team and saves it to the user's session.
    """
    # Create agents
    surfer = MultimodalWebSurfer(
        "WebSurfer",
        model_client=az_model_client
    )

    file_surfer = FileSurfer(
        "FileSurfer",
        model_client=az_model_client
    )

    coder = MagenticOneCoderAgent(
        "Coder",
        model_client=az_model_client
    )

    # Group them into a team
    team = MagenticOneGroupChat(
        participants=[surfer, file_surfer, coder],
        model_client=az_model_client
    )

    # Store in user session
    cl.user_session.set("team", team)

    # Send a welcome message to the user
    await cl.Message(content="Hello! Your multi-agent team is ready.").send()

def format_agent_message(agent_name: str, content: str) -> str:
    """Format messages from different agents with their own styling."""
    agent_prefixes = {
        "WebSurfer": "🌐 Web Search",
        "FileSurfer": "📁 File Analysis",
        "Coder": "💻 Code Assistant",
        "MagenticOneOrchestrator": "🎭 Orchestrator",
        "system": "🤖 System"
    }
    
    prefix = agent_prefixes.get(agent_name, "🔄 Agent")
    
    # Check if content contains code blocks
    if "```" in content:
        # Ensure code blocks are properly formatted with language
        content = re.sub(
            r'```(\w*)\n(.*?)```',
            lambda m: f'```{m.group(1) or "python"}\n{m.group(2).strip()}\n```',
            content,
            flags=re.DOTALL
        )
    
    return f"### {prefix}\n{content}"

@cl.on_message
async def handle_message(message: cl.Message):
    """Handle messages with clear agent identification and structured responses."""
    team = cl.user_session.get("team")
    if not team:
        await cl.Message(content="⚠️ Error: Agent team not initialized").send()
        return

    # Create a message element to show thinking status
    msg = cl.Message(content="🤔 Thinking...", author="System")
    await msg.send()

    # Stream responses from the team
    async for response in team.run_stream(task=message.content):
        try:
            if hasattr(response, 'content'):
                # Handle list-type content
                if isinstance(response.content, list):
                    for content_item in response.content:
                        if isinstance(content_item, str):
                            # Get the agent name from the response if available
                            agent_name = getattr(response, 'source', 'system')
                            formatted_content = format_agent_message(agent_name, content_item)
                            
                            # Send message with proper markdown formatting
                            await cl.Message(
                                content=formatted_content,
                                author=agent_name,
                                language="markdown"  # Ensure markdown is rendered
                            ).send()
                            
                            await asyncio.sleep(STREAM_DELAY)
                else:
                    # Handle single content
                    agent_name = getattr(response, 'source', 'system')
                    formatted_content = format_agent_message(
                        agent_name, 
                        str(response.content)
                    )
                    await cl.Message(
                        content=formatted_content,
                        author=agent_name,
                        language="markdown"
                    ).send()
            else:
                # Handle system messages or other types
                formatted_content = format_agent_message('system', str(response))
                await cl.Message(
                    content=formatted_content,
                    author="System",
                    language="markdown"
                ).send()

        except Exception as e:
            error_msg = format_agent_message('system', f"Error processing response: {str(e)}")
            await cl.Message(
                content=error_msg,
                author="System"
            ).send()

    # Remove the thinking message
    await msg.remove()

    # Send a completion message
    completion_msg = format_agent_message(
        'system',
        "✅ Task completed. All agents have finished their analysis."
    )
    await cl.Message(
        content=completion_msg,
        author="System"
    ).send()