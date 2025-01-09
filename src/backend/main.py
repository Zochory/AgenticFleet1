from typing import Dict, Any, Optional, AsyncIterator, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    MultiModalMessage
)
from autogen_core import Image
from autogen_core.models import RequestUsage
import json
import asyncio
import time

from magentic_one_helper import MagenticOneHelper
from models.logging import team_logger, system_logger

app = FastAPI(
    title="AutoGen API",
    description="API for running AutoGen agent teams",
    version="0.1.0"
)

helper: Optional[MagenticOneHelper] = None
team_agents: List[Any] = []  # Store agent list for health checks


@app.on_event("startup")
async def startup_event() -> None:
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
            {"type": "MagenticOne", "name": "FileSurfer"},
            {"type": "MagenticOne", "name": "WebSurfer"},
            {"type": "MagenticOne", "name": "Coder"}
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


async def stream_output(task: str) -> AsyncIterator[str]:
    """
    Stream the task execution output in real-time using an async generator.
    Yields SSE (Server-Sent Events) data chunks as JSON.
    """
    start_time = time.time()
    try:
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

    except Exception as e:
        error_content = {
            "type": "error",
            "source": "system",
            "content": f"Error during streaming: {str(e)}",
            "timestamp": time.time() - start_time
        }
        team_logger.error(
            "stream_error",
            "Error during streaming",
            {"task": task, "error": str(e)}
        )
        yield f"data: {json.dumps(error_content)}\n\n"
        team_logger.log_task_complete(task, False, {"error": str(e)})


@app.get("/stream_task")
async def stream_task(task: str) -> StreamingResponse:
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
        stream_output(task),
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
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)