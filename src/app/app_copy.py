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
from magentic_one_helper import MagenticOneHelper

load_dotenv()

# Constants
STREAM_DELAY = 0.01
DEFAULT_MAX_ROUNDS = 50
DEFAULT_MAX_TIME = 10
DEFAULT_MAX_STALLS = 5
DEFAULT_START_PAGE = "https://bing.com"

# Agent Names and Authors
AGENT_NAMES = {
    "WebSurfer": "🌐 Web Search",
    "FileSurfer": "📁 File Analysis",
    "Coder": "💻 Code Assistant",
    "MagenticOneOrchestrator": "🎭 Orchestrator",
    "system": "🤖 System"
}

AGENT_AUTHORS = {
    "WebSurfer": "WebSurferAgent",
    "FileSurfer": "FileSurferAgent",
    "Coder": "CoderAgent",
    "MagenticOneOrchestrator": "MagenticOneOrchestratorAgent",
    "system": "System"
}

# Create the Azure OpenAI client from environment variables
az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    model=os.getenv("AZURE_OPENAI_MODEL"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@cl.oauth_callback
def oauth_callback(provider_id: str, token: str, raw_user_data: Dict[str, str], default_user: cl.User) -> Optional[cl.User]:
    """Authenticate the user based on the provided OAuth token."""
    return default_user

@cl.on_chat_start
async def on_chat_start():
    """Initialize user parameters and display welcome message."""
    cl.user_session.set("max_rounds", DEFAULT_MAX_ROUNDS)
    cl.user_session.set("max_time", DEFAULT_MAX_TIME)
    cl.user_session.set("max_stalls", DEFAULT_MAX_STALLS)
    cl.user_session.set("start_page", DEFAULT_START_PAGE)

    welcome_text = f"Max Rounds: {DEFAULT_MAX_ROUNDS}\nMax Time (Minutes): {DEFAULT_MAX_TIME}\nMax Stalls Before Replan: {DEFAULT_MAX_STALLS}\nStart Page URL: {DEFAULT_START_PAGE}"
    await cl.Message(content=f"Welcome! Current settings:\n{welcome_text}").send()

    surfer = MultimodalWebSurfer("WebSurfer", model_client=az_model_client)
    file_surfer = FileSurfer("FileSurfer", model_client=az_model_client)
    coder = MagenticOneCoderAgent("Coder", model_client=az_model_client)
    team = MagenticOneGroupChat(participants=[surfer, file_surfer, coder], model_client=az_model_client)
    cl.user_session.set("team", team)

    await cl.Message(content="Hello! Your multi-agent team is ready.").send()

    # Add TaskList element
    task_list = cl.TaskList()
    await task_list.send()

def format_agent_message(agent_name: str, content: str) -> str:
    """Format messages from different agents."""
    prefix = AGENT_NAMES.get(agent_name, "🔄 Agent")
    if "```" in content:
        content = re.sub(r'```(\w*)\n(.*?)```',
                         lambda m: f'```{m.group(1) or "python"}\n{m.group(2).strip()}\n```',
                         content,
                         flags=re.DOTALL)
    return f"### {prefix}\n{content}"

@cl.on_message
async def handle_message(message: cl.Message):
    """Handle incoming messages and process them using the multi-agent team."""
    team = cl.user_session.get("team")
    if not team:
        await cl.Message(content="⚠️ Error: Agent team not initialized").send()
        return

    thinking_msg = await cl.Message(content="🤔 Thinking...", author="System").send()
    max_rounds = cl.user_session.get("max_rounds", DEFAULT_MAX_ROUNDS)
    current_round = 0
    collected_responses = []
    initial_plan = None

    try:
        while current_round < max_rounds:
            async for response in team.run_stream(task=message.content):
                if initial_plan is None and "Here is the plan to follow as best as possible:" in response.content:
                    initial_plan = response.content
                    task_list = cl.TaskList()
                    task_list.add_task(initial_plan)
                    await task_list.send()
                await process_response(response, collected_responses)
                current_round += 1
                if current_round >= max_rounds:
                    break
    except Exception as e:
        logger.exception("Error processing response")
        error_msg = format_agent_message('system', f"Error: {str(e)}")
        await cl.Message(content=error_msg, author="System").send()
    finally:
        await thinking_msg.remove()
        final_answer = generate_final_answer(collected_responses)
        await cl.Message(content=final_answer, author="System").send()

        # Update TaskList with final answer
        task_list = cl.TaskList()
        task_list.add_task(final_answer)
        await task_list.send()

def generate_final_answer(collected_responses: List[str]) -> str:
    """Generate a final detailed and formatted answer based on collected responses."""
    final_answer = "### Final Answer\n\n"
    for response in collected_responses:
        final_answer += response + "\n\n"
    return final_answer

async def process_response(response: Any, collected_responses: List[str]):
    """Stream each piece of content as a separate message in Chainlit and collect responses."""
    if hasattr(response, 'content'):
        contents = response.content if isinstance(response.content, list) else [response.content]
        agent_name = getattr(response, 'source', 'system')
        for item in contents:
            await send_response_item(item, agent_name, collected_responses)
    else:
        formatted = format_agent_message('system', str(response))
        await cl.Message(content=formatted, author="System").send()
        collected_responses.append(formatted)

async def send_response_item(item: str, agent_name: str, collected_responses: List[str]):
    """Send an individual response item to the Chainlit interface and collect responses."""
    author = AGENT_AUTHORS.get(agent_name, "Unknown Agent")
    if isinstance(item, str):
        if re.search(r'http[s]?://\S+\.(?:png|jpg|jpeg|gif)', item):
            try:
                await cl.Message(content=item, author=author, elements=[cl.Image(src=item)]).send()
            except Exception as e:
                logger.exception("Error sending image")
                error_msg = format_agent_message('system', f"Error: {str(e)}")
                await cl.Message(content=error_msg, author="System").send()
        else:
            formatted = format_agent_message(agent_name, item)
            await cl.Message(content=formatted, author=author).send()
            collected_responses.append(formatted)
    await asyncio.sleep(STREAM_DELAY)

# Add TaskList element to the interface
@cl.on_chat_start
async def on_chat_start():
    """Initialize user parameters and display welcome message."""
    cl.user_session.set("max_rounds", DEFAULT_MAX_ROUNDS)
    cl.user_session.set("max_time", DEFAULT_MAX_TIME)
    cl.user_session.set("max_stalls", DEFAULT_MAX_STALLS)
    cl.user_session.set("start_page", DEFAULT_START_PAGE)

    welcome_text = f"Max Rounds: {DEFAULT_MAX_ROUNDS}\nMax Time (Minutes): {DEFAULT_MAX_TIME}\nMax Stalls Before Replan: {DEFAULT_MAX_STALLS}\nStart Page URL: {DEFAULT_START_PAGE}"
    await cl.Message(content=f"Welcome! Current settings:\n{welcome_text}").send()

    surfer = MultimodalWebSurfer("WebSurfer", model_client=az_model_client)
    file_surfer = FileSurfer("FileSurfer", model_client=az_model_client)
    coder = MagenticOneCoderAgent("Coder", model_client=az_model_client)
    team = MagenticOneGroupChat(participants=[surfer, file_surfer, coder], model_client=az_model_client)
    cl.user_session.set("team", team)

    await cl.Message(content="Hello! Your multi-agent team is ready.").send()

    # Add TaskList element
    task_list = cl.TaskList()
    await task_list.send()

@cl.on_message
async def handle_message(message: cl.Message):
    """Handle incoming messages and process them using the multi-agent team."""
    team = cl.user_session.get("team")
    if not team:
        await cl.Message(content="⚠️ Error: Agent team not initialized").send()
        return

    thinking_msg = await cl.Message(content="🤔 Thinking...", author="System").send()
    max_rounds = cl.user_session.get("max_rounds", DEFAULT_MAX_ROUNDS)
    current_round = 0
    collected_responses = []
    initial_plan = None

    try:
        while current_round < max_rounds:
            async for response in team.run_stream(task=message.content):
                if initial_plan is None and "Here is the plan to follow as best as possible:" in response.content:
                    initial_plan = response.content
                    task_list = cl.TaskList()
                    task_list.add_task(initial_plan)
                    await task_list.send()
                await process_response(response, collected_responses)
                current_round += 1
                if current_round >= max_rounds:
                    break
    except Exception as e:
        logger.exception("Error processing response")
        error_msg = format_agent_message('system', f"Error: {str(e)}")
        await cl.Message(content=error_msg, author="System").send()
    finally:
        await thinking_msg.remove()
        final_answer = generate_final_answer(collected_responses)
        await cl.Message(content=final_answer, author="System").send()

        # Update TaskList with final answer
        task_list = cl.TaskList()
        task_list.add_task(final_answer)
        await task_list.send()