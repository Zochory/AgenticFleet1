import asyncio
from dataclasses import dataclass
import os
from typing import Dict, Optional
from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage
from dotenv import load_dotenv

import chainlit as cl
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

load_dotenv()

# 
@cl.oauth_callback
def oauth_callback(
  provider_id: str,
  token: str,
  raw_user_data: Dict[str, str],
  default_user: cl.User,
) -> Optional[cl.User]:
  return default_user


#Create CogCache client
cogcache_client = OpenAIChatCompletionClient(
    base_url = "https://proxy-api.cogcache.com/v1/",
    api_key = os.getenv('COGCACHE_API_KEY'),
    model = "gpt-4o-mini-2024-07-18",
    # this is not needed here, if it's already set via environment variables
    default_headers = { 
        "Authorization": f"Bearer {os.getenv('COGCACHE_API_KEY')}",
    },
)

async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."

@cl.on_chat_start  # type: ignore
async def start_chat():
    cl.user_session.set("prompt_history", "")  # type: ignore


async def run_team(query: str):
    assistant_agent = AssistantAgent(
        name="assistant_agent", tools=[get_weather], model_client=cogcache_client
    )

    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)
    team = RoundRobinGroupChat(participants=[assistant_agent], termination_condition=termination)

    response_stream = team.run_stream(task=query)
    async for msg in response_stream:
        if hasattr(msg, "content"):
            cl_msg = cl.Message(content=msg.content, author="Agent Team")  # type: ignore
            await cl_msg.send()
        if isinstance(msg, TaskResult):
            cl_msg = cl.Message(content="Termination condition met. Team and Agents are reset.", author="Agent Team")
            await cl_msg.send()


@cl.on_message  # type: ignore
async def chat(message: cl.Message):
    await run_team(message.content)  # type: ignore



