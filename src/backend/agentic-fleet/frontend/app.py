"""
Chainlit frontend for the Magentic team.
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, Any, AsyncGenerator, List
import chainlit as cl
from chainlit.types import AskFileResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

async def process_sse_stream(response: aiohttp.ClientResponse) -> AsyncGenerator[str, None]:
    """Process Server-Sent Events stream."""
    buffer = ""
    try:
        async for chunk in response.content:
            if not chunk:
                continue
            try:
                buffer += chunk.decode('utf-8')
                while '\n\n' in buffer:
                    line, buffer = buffer.split('\n\n', 1)
                    if line.startswith('data: '):
                        yield line[6:]  # Remove "data: " prefix
            except UnicodeDecodeError as e:
                print(f"Error decoding chunk: {e}")
                continue
    except Exception as e:
        print(f"Error in SSE stream: {e}")
        raise

@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    # Send welcome message
    msg = cl.Message(
        content="👋 Welcome! I'm your AI assistant powered by the MagenticTeam. How can I help you today?",
        author="System"
    )
    await msg.send()

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    try:
        # Stream response from backend
        async with cl.Step("Processing Task") as step:
            try:
                async with aiohttp.ClientSession() as session:
                    try:
                        print(f"Connecting to backend at {BACKEND_URL}")
                        async with session.get(
                            f"{BACKEND_URL}/stream_task",
                            params={"task": message.content},
                            headers={"Accept": "text/event-stream"}
                        ) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                print(f"Backend returned status {response.status}: {error_text}")
                                raise Exception(f"Backend error (status {response.status}): {error_text}")
                            
                            print("Connected to backend stream")
                            current_plan_tasks = []
                            task_list = None
                            
                            async for data in process_sse_stream(response):
                                if not data:
                                    continue
                                    
                                try:
                                    event = json.loads(data)
                                    event_type = event.get("type", "")
                                    content = event.get("content", "")
                                    
                                    print(f"Received event: {event_type}")
                                    
                                    if event_type == "plan":
                                        # Create a new task list for the MagenticTeam's plan
                                        task_list = cl.TaskList()
                                        task_list.status = "Executing Plan"
                                        
                                        # Parse plan steps from the content
                                        if isinstance(content, str):
                                            # Extract steps after the plan marker
                                            plan_marker = "Here is the plan to follow as best as possible:"
                                            if plan_marker in content:
                                                plan_text = content.split(plan_marker)[1].strip()
                                                # Split into steps, handling both numbered and bullet points
                                                steps = [step.strip().lstrip('1234567890.-) ') 
                                                        for step in plan_text.split('\n') 
                                                        if step.strip() and not step.strip().startswith(plan_marker)]
                                                print(f"Extracted {len(steps)} steps from plan")
                                            else:
                                                print("Plan marker not found in content")
                                                steps = [content]
                                        elif isinstance(content, list):
                                            steps = content
                                        else:
                                            steps = [str(content)]
                                        
                                        # Filter out empty steps and create tasks
                                        for step in [s for s in steps if s]:
                                            task = cl.Task(
                                                title=step,
                                                status=cl.TaskStatus.READY
                                            )
                                            await task_list.add_task(task)
                                            current_plan_tasks.append(task)
                                        
                                        if current_plan_tasks:
                                            current_plan_tasks[0].status = cl.TaskStatus.RUNNING
                                        await task_list.send()
                                    
                                    elif event_type == "thought":
                                        msg = cl.Message(
                                            content=f"💭 {content}",
                                            author="MagenticTeam"
                                        )
                                        await msg.send()
                                    
                                    elif event_type == "error":
                                        msg = cl.Message(
                                            content=f"❌ Error: {content}",
                                            author="System"
                                        )
                                        await msg.send()
                                        raise Exception(content)
                                    
                                    elif event_type == "event":
                                        source = event.get("source", "MagenticTeam")
                                        msg = cl.Message(
                                            content=content,
                                            author=source
                                        )
                                        await msg.send()
                                        
                                        # Update task progress if we have a task list
                                        if task_list and current_plan_tasks:
                                            current_plan_tasks[0].status = cl.TaskStatus.DONE
                                            if len(current_plan_tasks) > 1:
                                                current_plan_tasks[1].status = cl.TaskStatus.RUNNING
                                            current_plan_tasks = current_plan_tasks[1:]
                                            await task_list.send()
                                    
                                    else:
                                        msg = cl.Message(
                                            content=content,
                                            author="MagenticTeam"
                                        )
                                        await msg.send()
                                
                                except json.JSONDecodeError as e:
                                    print(f"JSON decode error: {e}")
                                    print(f"Raw data: {data}")
                                    msg = cl.Message(
                                        content=data,
                                        author="MagenticTeam"
                                    )
                                    await msg.send()
                                except Exception as e:
                                    print(f"Error processing event: {e}")
                                    raise
                                    
                    except aiohttp.ClientError as e:
                        print(f"Connection error: {e}")
                        raise Exception(f"Failed to connect to backend: {e}")
                        
            except asyncio.TimeoutError:
                print("Connection timed out")
                raise Exception("Connection to backend timed out")
                
        # Update final task statuses
        if task_list and current_plan_tasks:
            for task in current_plan_tasks:
                task.status = cl.TaskStatus.DONE
            task_list.status = "Completed"
            await task_list.send()
        
    except Exception as e:
        print(f"Error in main handler: {e}")
        if task_list:
            task_list.status = "Failed"
            if current_plan_tasks:
                current_plan_tasks[0].status = cl.TaskStatus.FAILED
            await task_list.send()
        
        msg = cl.Message(
            content=f"❌ An error occurred: {str(e)}\n\nPlease make sure the backend server is running at {BACKEND_URL}",
            author="System"
        )
        await msg.send()

if __name__ == "__main__":
    cl.run()