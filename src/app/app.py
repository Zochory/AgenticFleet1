"""Chainlit-based web interface for AutoGen agent interactions."""

import os
import asyncio
import re
import json
import string
import logging
from typing import List, Optional, Any, Dict, Union

import chainlit as cl
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_agentchat.messages import MultiModalMessage, TextMessage, Image, FunctionCall
from autogen_agentchat.base import TaskResult
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Constants
STREAM_DELAY = 0.01
DEFAULT_MAX_ROUNDS = 50
DEFAULT_MAX_TIME = 10
DEFAULT_MAX_STALLS = 5
DEFAULT_START_PAGE = "https://bing.com"

# Initialize Azure OpenAI client
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    model=os.getenv("AZURE_OPENAI_MODEL"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_ad_token_provider=token_provider,
    model_info={
        "vision": True,
        "function_calling": True,
        "json_output": True,
    }
)


@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User
) -> Optional[cl.User]:
    """Handle OAuth authentication."""
    try:
        # Check if OAuth is disabled via environment variable
        if os.getenv("DISABLE_OAUTH") == "1":
            logger.info("OAuth is disabled, using default user")
            return default_user

        # Handle GitHub OAuth
        if provider_id == "github":
            if not (os.getenv("OAUTH_GITHUB_CLIENT_ID") and os.getenv("OAUTH_GITHUB_CLIENT_SECRET")):
                logger.warning("GitHub OAuth credentials not found")
                return default_user
                
            # You can customize the user based on GitHub data
            username = raw_user_data.get("login", "")
            name = raw_user_data.get("name", "")
            email = raw_user_data.get("email", "")
            
            logger.info(f"Authenticated GitHub user: {username}")
            return cl.User(
                identifier=username,
                metadata={
                    "name": name,
                    "email": email,
                    "provider": "github"
                }
            )
            
        # Default fallback
        logger.warning(f"Unsupported OAuth provider: {provider_id}")
        return default_user
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return default_user

@cl.on_chat_start
async def initialize_session() -> None:
    """Initialize user session and set up agent team."""
    try:
        # Handle user authentication
        app_user = cl.user_session.get("user")
        greeting = f"Hello {app_user.identifier}!" if app_user else "Welcome, guest!"
        await cl.Message(greeting).send()

        # Initialize session parameters
        cl.user_session.set("max_rounds", DEFAULT_MAX_ROUNDS)
        cl.user_session.set("max_time", DEFAULT_MAX_TIME)
        cl.user_session.set("max_stalls", DEFAULT_MAX_STALLS)
        cl.user_session.set("start_page", DEFAULT_START_PAGE)

        # Display settings
        welcome_text = (
            f"Max Rounds: {DEFAULT_MAX_ROUNDS}\n"
            f"Max Time (Minutes): {DEFAULT_MAX_TIME}\n"
            f"Max Stalls Before Replan: {DEFAULT_MAX_STALLS}\n"
            f"Start Page URL: {DEFAULT_START_PAGE}"
        )
        await cl.Message(content=f"Welcome! Current settings:\n{welcome_text}").send()

        # Initialize agent team
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
        # Create code executor
        code_executor = LocalCommandLineCodeExecutor(
            work_dir=os.path.join(os.getcwd(), "workspace")
        )

        # Create executor agent with code executor
        executor = CodeExecutorAgent(
            code_executor=code_executor,
            name="Executor"
        )

        # Create team
        team = MagenticOneGroupChat(
            participants=[surfer, file_surfer, coder, executor],
            model_client=az_model_client
        )
        cl.user_session.set("team", team)
        
        # Initialize task list
        task_list = cl.TaskList()
        cl.user_session.set("task_list", task_list)
        await task_list.send()
        
        await cl.Message(content="Your multi-agent team is ready.").send()
        
    except Exception as e:
        logger.exception("Failed to initialize session")
        await cl.Message(content=f"⚠️ Initialization failed: {str(e)}").send()


def format_agent_message(agent_name: str, content: str) -> str:
    """Format messages with agent-specific styling while preserving agent names."""
    if "```" in content:
        content = re.sub(
            r'```(\w*)\n(.*?)```',
            lambda m: f'```{m.group(1) or "python"}\n{m.group(2).strip()}\n```',
            content,
            flags=re.DOTALL
        )

    return content


def extract_steps_from_content(content: str) -> List[str]:
    """Extract steps from the content."""
    steps = []
    # Look for steps in different formats
    patterns = [
        r'(?:Step|STEP)\s*\d+:?\s*([^\n]+)',  # Step 1: Do something
        r'(?:^|\n)\s*\d+\.\s*([^\n]+)',        # 1. Do something
        r'(?:^|\n)\s*-\s*([^\n]+)',            # - Do something
        r'(?:^|\n)\s*\*\s*([^\n]+)'            # * Do something
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        steps.extend(match.group(1).strip() for match in matches)
    
    return steps


async def process_response(
    response: Any,
    collected_responses: List[str]
) -> None:
    """Process agent responses while preserving agent attribution and showing inner messages."""
    try:
        # Handle non-content responses (like LLM calls)
        if not hasattr(response, 'content'):
            # Check if it's an LLM call
            if hasattr(response, 'type') and response.type == "LLMCall":
                # Show LLM call details
                llm_details = (
                    f"LLM Call Details:\n"
                    f"Prompt Tokens: {response.prompt_tokens}\n"
                    f"Completion Tokens: {response.completion_tokens}\n"
                    f"Messages: {json.dumps(response.messages, indent=2)}"
                )
                await cl.Message(content=llm_details, author="System").send()
            else:
                # Handle other non-content responses
                formatted = format_agent_message('system', str(response))
                await cl.Message(content=formatted, author="System").send()
            collected_responses.append(str(response))
            return

        contents = response.content if isinstance(response.content, list) else [response.content]
        agent_name = getattr(response, 'source', 'system')
        
        # Show all messages, including planning ones
        for item in contents:
            if not isinstance(item, (str, dict)):
                continue
                
            # Handle MultiModalMessage with images
            if isinstance(item, list) and len(item) > 1:
                try:
                    # Extract text content and image object
                    text_content = item[0]
                    image_obj = item[-1]
                    
                    # Log the image object details
                    logger.info(f"Image object type: {type(image_obj)}")
                    logger.info(f"Image object attributes: {dir(image_obj)}")
                    
                    # Send text content
                    await cl.Message(
                        content=text_content,
                        author=agent_name
                    ).send()
                    
                    # Try to get image data
                    try:
                        if hasattr(image_obj, '_image_data'):
                            # Convert base64 to bytes if needed
                            import base64
                            try:
                                image_bytes = base64.b64decode(image_obj._image_data)
                            except:
                                image_bytes = image_obj._image_data
                            
                            # Create temporary file
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                                tmp.write(image_bytes)
                                tmp.flush()
                                
                                # Send image using file path
                                await cl.Message(
                                    content="Screenshot:",
                                    author=agent_name,
                                    elements=[cl.Image(path=tmp.name)]
                                ).send()
                                
                                # Clean up
                                import os
                                os.unlink(tmp.name)
                                
                        elif hasattr(image_obj, 'data'):
                            # Handle raw bytes data
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                                tmp.write(image_obj.data)
                                tmp.flush()
                                
                                await cl.Message(
                                    content="Screenshot:",
                                    author=agent_name,
                                    elements=[cl.Image(path=tmp.name)]
                                ).send()
                                
                                # Clean up
                                import os
                                os.unlink(tmp.name)
                        else:
                            # Log what we found
                            logger.info(f"Image object content: {str(image_obj)}")
                            await cl.Message(
                                content="Unable to display image - data not found",
                                author="System"
                            ).send()
                    except Exception as img_e:
                        logger.error(f"Failed to process image data: {str(img_e)}")
                        await cl.Message(
                            content=f"Error processing image data: {str(img_e)}",
                            author="System"
                        ).send()
                    
                except Exception as e:
                    logger.error(f"Failed to process image: {str(e)}")
                    await cl.Message(
                        content=f"Error processing image: {str(e)}",
                        author="System"
                    ).send()
                    
            # Handle URL-based images
            elif isinstance(item, str) and re.search(r'http[s]?://\S+\.(?:png|jpg|jpeg|gif)', item):
                try:
                    # Try to display the image URL
                    await cl.Message(
                        content="Screenshot:",
                        author=agent_name,
                        elements=[cl.Image(url=item)]
                    ).send()
                except Exception as e:
                    logger.error(f"Failed to send image URL: {str(e)}")
                    # Fall back to showing the URL
                    await cl.Message(
                        content=f"Image URL: {item}",
                        author=agent_name
                    ).send()
            else:
                content = item if isinstance(item, str) else item.get('content', str(item))
                formatted = format_agent_message(agent_name, content)
                
                # Show all messages with their original authors
                await cl.Message(content=formatted, author=agent_name).send()
                collected_responses.append(formatted)
                
                # Check for steps in the content and update TaskList
                if "plan" in content.lower() or "step" in content.lower():
                    steps = extract_steps_from_content(content)
                    if steps:
                        task_list = cl.user_session.get("task_list")
                        if task_list:
                            # Clear existing tasks
                            task_list.tasks.clear()
                            # Add new tasks
                            for step in steps:
                                task_list.add_task(step)
                            await task_list.send()
                
            await asyncio.sleep(STREAM_DELAY)

        # Handle models_usage more carefully
        if hasattr(response, 'models_usage'):
            try:
                if hasattr(response.models_usage, '_asdict'):
                    usage_dict = response.models_usage._asdict()
                elif isinstance(response.models_usage, dict):
                    usage_dict = response.models_usage
                else:
                    usage_dict = {
                        "prompt_tokens": getattr(response.models_usage, "prompt_tokens", "unknown"),
                        "completion_tokens": getattr(response.models_usage, "completion_tokens", "unknown")
                    }
                
                usage_details = (
                    f"Model Usage:\n"
                    f"Prompt Tokens: {usage_dict.get('prompt_tokens', 'unknown')}\n"
                    f"Completion Tokens: {usage_dict.get('completion_tokens', 'unknown')}"
                )
                await cl.Message(content=usage_details, author="System").send()
            except Exception as e:
                logger.error(f"Failed to process model usage: {str(e)}")
                
    except Exception as e:
        logger.exception("Error processing response")
        await cl.Message(
            content=f"Error: {str(e)}",
            author="System"
        ).send()

@cl.on_message
async def handle_message(message: cl.Message) -> None:
    """Handle incoming user messages while preserving agent attribution."""
    team = cl.user_session.get("team")
    if not team:
        await cl.Message(content="⚠️ Error: Agent team not initialized", author="System").send()
        return

    thinking_msg = await cl.Message(content="🤔 Thinking...", author="System").send()
    collected_responses: List[str] = []
    
    try:
        max_time = cl.user_session.get("max_time", DEFAULT_MAX_TIME)
        async with asyncio.timeout(max_time * 60):  # Convert minutes to seconds
            async for response in team.run_stream(task=message.content):
                await process_response(response, collected_responses)
                
    except asyncio.TimeoutError:
        logger.warning("Message processing timed out")
        await cl.Message(
            content="⚠️ Processing timed out",
            author="System"
        ).send()
        
    except Exception as e:
        logger.exception("Error processing message")
        await cl.Message(
            content=f"Error: {str(e)}",
            author="System"
        ).send()
        
    finally:
        await thinking_msg.remove()
        
        if collected_responses:
            summary = "\n".join(collected_responses[-3:])  # Last 3 responses
            await cl.Message(content=summary, author="System").send()
        
        await cl.Message(content="✅ Task completed", author="System").send()


@cl.on_stop
async def cleanup() -> None:
    """Clean up resources when the application stops."""
    try:
        team = cl.user_session.get("team")
        if team:
            await team.aclose()
            logger.info("Successfully cleaned up agent team")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
