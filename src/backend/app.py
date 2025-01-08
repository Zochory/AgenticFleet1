from fastapi import FastAPI, BackgroundTasks, HTTPException
from typing import Dict, Any, Optional, AsyncIterator, Sequence
from fastapi.responses import StreamingResponse
from autogen_agentchat.ui import Console
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_agentchat.messages import ChatMessage
import json
import asyncio

from models import (
    create_azure_client,
    GPT4_CONFIG,
    AZURE_GPT4_CONFIG,
    PlanMessage,
    ErrorMessage,
    DialogMessage,
    ThoughtMessage,
    create_message
)
from models.logging import team_logger, system_logger

app = FastAPI(
    title="AutoGen API",
    description="API for running AutoGen agent teams",
    version="0.1.0"
)

team: Optional[MagenticOneGroupChat] = None
team_agents = []  # Store agent list for health checks

@app.on_event("startup")
async def startup_event():
    try:
        system_logger.info("startup", "Initializing AutoGen API")
        
        # Create model client using our configuration
        model_client = create_azure_client(
            model_config=GPT4_CONFIG,
            azure_config=AZURE_GPT4_CONFIG
        )
        
        # Initialize agents
        fs = FileSurfer(
            "FileSurfer",
            model_client=model_client
        )

        # WebSurfer is optional as it requires additional system dependencies
        try:
            ws = MultimodalWebSurfer(
                "WebSurfer",
                model_client=model_client
            )
            team_agents.append(ws)
        except Exception as e:
            system_logger.warning(
                "agent_init",
                "WebSurfer agent not available",
                {"error": str(e)}
            )

        coder = MagenticOneCoderAgent(
            "Coder",
            model_client=model_client
        )
        
        # Add base agents
        team_agents.extend([fs, coder])
        
        # Create global team instance
        global team
        team = MagenticOneGroupChat(team_agents, model_client=model_client)
        
        system_logger.info(
            "startup_complete",
            "Application initialized successfully",
            {"agents": [agent.name for agent in team_agents]}
        )
        
    except Exception as e:
        error_msg = create_message(
            "error",
            content="Failed to initialize application",
            error_type="StartupError",
            message="Failed to initialize application",
            details={"error": str(e)}
        )
        system_logger.error(
            "startup_error",
            "Failed to initialize application",
            {"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=error_msg.content)

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check if the service is healthy and team is initialized."""
    if team is None:
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

@app.post("/run_task")
async def run_task(task: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Run a task using the agent team."""
    if not task:
        system_logger.warning("task_validation", "Empty task received")
        raise HTTPException(status_code=400, detail="Task cannot be empty")
    
    if team is None:
        system_logger.error("task_execution", "Team not initialized")
        raise HTTPException(status_code=503, detail="Team not initialized")
    
    try:
        team_logger.log_task_start(task, [agent.name for agent in team_agents])
        
        # Create initial thought about the task
        thought = create_message(
            "thought",
            content="Analyzing task requirements",
            reasoning="Preparing to execute task",
            observations=[f"Received task: {task}"],
            next_steps=["Create execution plan", "Delegate to agents", "Monitor execution"]
        )
        
        # Create a plan message for the task
        plan = create_message(
            "plan",
            content=f"Plan to execute task: {task}",
            title="Task Execution Plan",
            description=f"Plan to execute task: {task}",
            steps=[
                "Parse and understand the task requirements",
                "Execute task using appropriate agents",
                "Return results and any generated artifacts"
            ]
        )
        
        # Run the task in background
        background_tasks.add_task(
            Console, team.run_stream(task=task)
        )
        
        # Create response message
        response = create_message(
            "dialog",
            content="Task accepted and being processed",
            speaker="System",
            utterance="Task accepted and being processed",
            context=task
        )
        
        team_logger.info(
            "task_accepted",
            "Task accepted for processing",
            {
                "task": task,
                "thought": thought.model_dump(),
                "plan": plan.model_dump()
            }
        )
        
        # Return immediate response
        return {
            "status": "accepted",
            "message": response.content,
            "thought": thought.content,
            "plan": plan.content
        }
        
    except Exception as e:
        error_msg = create_message(
            "error",
            content=f"Failed to execute task: {task}",
            error_type="TaskExecutionError",
            message="Failed to execute task",
            details={
                "task": task,
                "error": str(e)
            }
        )
        team_logger.error(
            "task_error",
            "Failed to execute task",
            {"task": task, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=error_msg.content)

async def stream_output(task: str) -> AsyncIterator[str]:
    """Stream the task execution output in real-time."""
    try:
        team_logger.log_task_start(task, [agent.name for agent in team_agents])
        
        # Create initial plan
        plan = create_message(
            "plan",
            content=f"Plan to execute task: {task}",
            title="Task Execution Plan",
            description=f"Plan to execute task: {task}",
            steps=[
                "Parse and understand the task requirements",
                "Execute task using appropriate agents",
                "Return results and any generated artifacts"
            ]
        )
        yield f"data: {json.dumps({'type': 'plan', 'content': plan.content})}\n\n"
        
        if team is None:
            raise ValueError("Team not initialized")
            
        # Stream task execution
        async for event in team.run_stream(task=task):
            try:
                source = getattr(event, 'source', 'system')
                content = getattr(event, 'content', str(event))
                
                # Log the event
                team_logger.log_agent_message(source, "stream", content)
                
                # Send event to client
                yield f"data: {json.dumps({
                    'type': 'event',
                    'source': source,
                    'content': content
                })}\n\n"
                
            except Exception as e:
                system_logger.error(
                    "stream_error",
                    "Error processing event",
                    {"error": str(e)}
                )
                continue
        
        team_logger.log_task_complete(task, True)
                
    except Exception as e:
        error = create_message(
            "error",
            content="Error during streaming",
            error_type="StreamError",
            message="Error during streaming",
            details={"error": str(e)}
        )
        team_logger.error(
            "stream_error",
            "Error during streaming",
            {"task": task, "error": str(e)}
        )
        yield f"data: {json.dumps({'type': 'error', 'content': error.content})}\n\n"
        team_logger.log_task_complete(task, False, {"error": str(e)})

@app.get("/stream_task")
async def stream_task(task: str) -> StreamingResponse:
    """Stream task execution in real-time using Server-Sent Events."""
    if not task:
        system_logger.warning("task_validation", "Empty task received")
        raise HTTPException(status_code=400, detail="Task cannot be empty")
    
    if team is None:
        system_logger.error("stream_task", "Team not initialized")
        raise HTTPException(status_code=503, detail="Team not initialized")
    
    return StreamingResponse(
        stream_output(task),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)