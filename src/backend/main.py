# Standard library imports
import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List, AsyncGenerator
import logging
import os
from pydantic import BaseSettings, ValidationError, SecretStr, BaseModel, constr

# FastAPI imports
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

# AutoGen core imports
from autogen_core import AgentId, AgentProxy, DefaultTopicId, Image
from autogen_core import SingleThreadedAgentRuntime
from autogen_core.models import RequestUsage

# AutoGen agent chat imports
from autogen_agentchat.agents import CodeExecutorAgent, AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    MultiModalMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent
)
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console

# AutoGen extension imports
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.azure import ACADynamicSessionsCodeExecutor
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Local imports
from models.logging import SystemLogger, TeamLogger
from magentic_one_helper import MagenticOneHelper

# Initialize loggers
system_logger = SystemLogger(name="system")
team_logger = TeamLogger(name="team")

helper: Optional[MagenticOneHelper] = None
team_agents: List[Any] = []  # Store agent list for health checks

# Add structured logging with sensitive data redaction
class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = record.msg.replace(
                os.getenv("AZURE_OPENAI_API_KEY", ""),
                "[REDACTED]"
            )
        return True

logger = logging.getLogger(__name__)
logger.addFilter(SensitiveDataFilter())

# Add validation for required environment variables
from pydantic import BaseSettings, ValidationError

class Settings(BaseSettings):
    AZURE_OPENAI_API_KEY: SecretStr
    BING_API_KEY: SecretStr
    APP_PORT: int = 8000
    DEBUG: bool = False

    class Config:
        env_file = ".env"

try:
    settings = Settings()
except ValidationError as e:
    logger.error(f"Invalid environment variables: {e}")
    raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize the application on startup.
    Sets up a MagenticOneHelper instance and configures default agents.
    """
    try:
        system_logger.info("startup", "Initializing AutoGen API")

        global helper
        helper = MagenticOneHelper()

        # Configure default agents
        default_agents = [
            {
                "type": "MagenticOne", 
                "name": "Coder"
            },
            {
                "type": "MagenticOne",
                "name": "WebSurfer",
                "capabilities": {
                    "vision": True,
                    "function_calling": True,
                    "json_output": True
                }
            },
            {
                "type": "MagenticOne",
                "name": "FileSurfer"
            }
        ]

        await helper.initialize(default_agents)
        team_agents.extend(helper.agents)

        system_logger.info(
            "startup_complete",
            "Application initialized successfully",
            {"agents": [agent.name for agent in team_agents]}
        )
    except Exception as e:
        system_logger.error(
            "startup_error",
            "Failed to initialize application",
            {"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))
    
    yield
    
    # Cleanup code (if any) would go here

app = FastAPI(
    title="AutoGen API",
    description="API for running AutoGen agent teams",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Check if the service is healthy and the agent team is initialized.
    Returns a JSON object with the status, initialization state, and agent names.
    """
    if helper is None:
        system_logger.warning("health_check", "Service not ready")
        raise HTTPException(status_code=503, detail="Service not ready")

    system_logger.info(
        "health_check",
        "Health check successful",
        {"agents": [agent.name for agent in team_agents]}
    )
    return {
        "status": "healthy",
        "team_initialized": True,
        "agents": [agent.name for agent in team_agents]
    }


def _message_to_str(message: Any) -> str:
    """
    Convert a message object into a string representation.

    Supports ChatMessage, AgentEvent, MultiModalMessage, and generic objects.
    """
    if isinstance(message, (ChatMessage, AgentEvent)):
        return str(message.content)
    elif isinstance(message, MultiModalMessage):
        result: List[str] = []
        for c in message.content:
            if isinstance(c, str):
                result.append(c)
            else:
                result.append("<image>")
        return "\n".join(result)
    else:
        return str(message)


async def stream_output(task: str) -> AsyncGenerator[str, None]:
    """
    Stream the task execution output in real-time using an async generator.
    Yields SSE (Server-Sent Events) data chunks as JSON.
    """
    start_time = time.time()
    try:
        if not task or len(task) > 1000:
            raise ValueError("Invalid task length")
            
        team_logger.log_task_start(task, [agent.name for agent in team_agents])
        total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

        # Provide an initial "plan" message
        plan_content = {
            "type": "plan",
            "title": "Task Execution Plan",
            "description": f"Plan to execute task: {task}",
            "steps": [
                "Parse and understand the task requirements",
                "Execute task using appropriate agents",
                "Return results and any generated artifacts"
            ]
        }
        yield f"data: {json.dumps(plan_content)}\n\n"

        if helper is None:
            raise ValueError("Team not initialized")

        # Stream events from the helper
        async for event in helper.main(task):
            try:
                if isinstance(event, (ChatMessage, MultiModalMessage, AgentEvent)):
                    source = getattr(event, 'source', 'system')
                    content = _message_to_str(event)

                    # Extract token usage if available
                    if hasattr(event, 'models_usage') and event.models_usage:
                        total_usage.prompt_tokens += event.models_usage.prompt_tokens
                        total_usage.completion_tokens += event.models_usage.completion_tokens
                        usage_info = {
                            "prompt_tokens": event.models_usage.prompt_tokens,
                            "completion_tokens": event.models_usage.completion_tokens
                        }
                    else:
                        usage_info = None
                else:
                    source = 'system'
                    content = str(event)
                    usage_info = None

                # Log the event
                team_logger.log_agent_message(source, "stream", content)

                # Create the SSE message payload
                message_output = {
                    "type": "message",
                    "source": source,
                    "content": content,
                    "timestamp": time.time() - start_time
                }

                if usage_info:
                    message_output["usage"] = usage_info

                yield f"data: {json.dumps(message_output)}\n\n"

            except Exception as e:
                system_logger.error(
                    "stream_error",
                    "Error processing event",
                    {"error": str(e)}
                )
                continue

        # Summarize usage at the end
        summary = {
            "type": "summary",
            "duration": time.time() - start_time,
            "total_prompt_tokens": total_usage.prompt_tokens,
            "total_completion_tokens": total_usage.completion_tokens
        }
        yield f"data: {json.dumps(summary)}\n\n"

        team_logger.log_task_complete(task, True, summary)

    except ValueError as e:
        error_content = {
            "type": "error",
            "source": "system",
            "content": f"Validation error: {str(e)}",
            "timestamp": time.time() - start_time
        }
        yield f"data: {json.dumps(error_content)}\n\n"
    except Exception as e:
        error_content = {
            "type": "error",
            "source": "system",
            "content": f"Unexpected error: {str(e)}",
            "timestamp": time.time() - start_time
        }
        yield f"data: {json.dumps(error_content)}\n\n"


from pydantic import BaseModel, constr

class TaskRequest(BaseModel):
    task: constr(min_length=1, max_length=1000)

@app.get("/stream_task")
async def stream_task(task: TaskRequest) -> StreamingResponse:
    """
    Endpoint to stream task execution in real-time using Server-Sent Events.

    Args:
        task: Description of the task to be performed.

    Returns:
        A StreamingResponse object that streams the execution output.
    """
    if not task:
        system_logger.warning("task_validation", "Empty task received")
        raise HTTPException(status_code=400, detail="Task cannot be empty")

    if helper is None:
        system_logger.error("stream_task", "Team not initialized")
        raise HTTPException(status_code=503, detail="Team not initialized")

    return StreamingResponse(
        stream_output(task.task),
        media_type="text/event-stream"
    )


@app.post("/run_task")
async def run_task(task: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Endpoint to run a given task asynchronously using the agent team.

    Args:
        task: A string describing the task to run.
        background_tasks: A FastAPI BackgroundTasks instance to schedule asynchronous jobs.

    Returns:
        A dictionary with status and confirmation message if the task is started.
    """
    if not task:
        system_logger.warning("task_validation", "Empty task received")
        raise HTTPException(status_code=400, detail="Task cannot be empty")

    if helper is None:
        system_logger.error("task_execution", "Team not initialized")
        raise HTTPException(status_code=503, detail="Team not initialized")

    try:
        async def process_task() -> None:
            async for _ in helper.main(task):
                pass

        background_tasks.add_task(process_task)

        return {
            "status": "accepted",
            "message": "Task started in background"
        }
    except Exception as e:
        system_logger.error(
            "task_error",
            "Error starting task",
            {"error": str(e)}
        )
        raise HTTPException(status_code=500, detail="An internal error has occurred.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)