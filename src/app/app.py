import os
import asyncio
import aiohttp
import json
import pandas as pd
import re
import logging
from dotenv import load_dotenv
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

load_dotenv()

# Constants
STREAM_DELAY = 0.01
DEFAULT_MAX_ROUNDS = 50
DEFAULT_MAX_TIME = 10
DEFAULT_MAX_STALLS = 5
DEFAULT_START_PAGE = "https://bing.com"

# Create the Azure OpenAI client from environment variables
az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    model=os.getenv("AZURE_OPENAI_MODEL"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)


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
async def on_chat_start():
    """
    Initializes user parameters and displays them to the user.
    """
    # Initialize user parameters
    cl.user_session.set("max_rounds", DEFAULT_MAX_ROUNDS)
    cl.user_session.set("max_time", DEFAULT_MAX_TIME)
    cl.user_session.set("max_stalls", DEFAULT_MAX_STALLS)
    cl.user_session.set("start_page", DEFAULT_START_PAGE)

    # Display them to the user
    welcome_text = (
        f"Max Rounds: {DEFAULT_MAX_ROUNDS}\n"
        f"Max Time (Minutes): {DEFAULT_MAX_TIME}\n"
        f"Max Stalls Before Replan: {DEFAULT_MAX_STALLS}\n"
        f"Start Page URL: {DEFAULT_START_PAGE}"
    )
    await cl.Message(content=f"Welcome! Current settings:\n{welcome_text}").send()

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
    """
    Format messages from different agents with their own styling.
    """
    agent_prefixes = {
        "WebSurfer": "🌐 Web Search",
        "FileSurfer": "📁 File Analysis",
        "Coder": "💻 Code Assistant",
        "MagenticOneOrchestrator": "🎭 Orchestrator",
        "system": "🤖 System"
    }
    prefix = agent_prefixes.get(agent_name, "🔄 Agent")

    # Ensure code blocks are properly formatted with language
    if "```" in content:
        content = re.sub(
            r'```(\w*)\n(.*?)```',
            lambda m: f'```{m.group(1) or "python"}\n{
                m.group(2).strip()}\n```',
            content,
            flags=re.DOTALL
        )

    return f"### {prefix}\n{content}"


@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handle incoming messages and process them using the multi-agent team.
    """
    team = cl.user_session.get("team")
    if not team:
        await cl.Message(content="⚠️ Error: Agent team not initialized").send()
        return

    thinking_msg = cl.Message(content="🤔 Thinking...", author="System")
    await thinking_msg.send()

    try:
        async for response in team.run_stream(task=message.content):
            await process_response(response)
    except Exception as e:
        logging.exception("Error processing response")
        error_msg = format_agent_message('system', f"Error: {str(e)}")
        await cl.Message(content=error_msg, author="System").send()
    finally:
        await thinking_msg.remove()

    completion_msg = format_agent_message('system', "✅ Task completed.")
    await cl.Message(content=completion_msg, author="System").send()


async def process_response(response: Any):
    """
    Stream each piece of content as a separate message in Chainlit.
    """
    if hasattr(response, 'content'):
        contents = response.content if isinstance(
            response.content, list) else [response.content]
        agent_name = getattr(response, 'source', 'system')
        for item in contents:
            if isinstance(item, str):
                if re.search(r'http[s]?://\S+\.(?:png|jpg|jpeg|gif)', item):
                    # Render image
                    await cl.Message(content=item, author=agent_name, elements=[cl.Image(src=item)]).send()
                else:
                    formatted = format_agent_message(agent_name, item)
                    await cl.Message(content=formatted, author=agent_name).send()
                await asyncio.sleep(STREAM_DELAY)
    else:
        # Handle system or unknown content
        formatted = format_agent_message('system', str(response))
        await cl.Message(content=formatted, author="System").send()
