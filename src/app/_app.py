"""
Chainlit frontend for the Magentic team.
"""

import os
import json
import asyncio
import aiohttp
from typing import AsyncGenerator, List, Optional, Any, Dict
from chainlit.utils import mount_chainlit
from chainlit.context import init_http_context
import chainlit as cl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Streaming configuration
STREAM_DELAY = 0.01  # Delay between characters in seconds

# Agent colors for visual distinction
AGENT_COLORS = {
    "System": "gray",
    "MagenticTeam": "blue",
    "Coder": "green",
    "WebSurfer": "purple",
    "FileSurfer": "orange",
    "Executor": "red"
}

async def stream_message(
    msg: cl.Message,
    content: str,
    delay: float = STREAM_DELAY
) -> None:
    """
    Stream content character by character into the provided Chainlit message.

    Args:
        msg: A Chainlit message instance with already initialized content/author.
        content: The text to stream in segments.
        delay: Delay between characters, in seconds.
    """
    # Stream content one character at a time
    for char in content:
        await msg.stream_token(char)
        await asyncio.sleep(delay)

    # Finally, send the updated content without extra kwargs
    await msg.send()

async def create_agent_message(
    content: str,
    author: str,
    is_thought: bool = False,
    elements: Optional[List[Any]] = None
) -> cl.Message:
    """
    Create a Chainlit message with agent-specific styling.

    Args:
        content: The main text content for this message.
        author: A string to identify the message author.
        is_thought: Whether this should be considered an agent's internal thought.
        elements: An optional list of Chainlit UI elements.
    """
    # Determine font color based on agent name
    color = AGENT_COLORS.get(author, "blue")

    # Prepend the "thought" indicator if necessary
    if is_thought:
        prefix = "💭 " if not content.startswith("💭") else ""
        content = f"{prefix}{content}"

    # Create an initially empty message for streaming
    msg = cl.Message(
        content="",
        author=f"<span style='color: {color}'>{author}</span>",
        elements=elements or []
    )

    # Set the content directly here if you prefer:
    msg.content = content

    return msg

async def format_code_blocks(content: str) -> str:
    """
    Wrap lines between triple backticks for syntax highlighting.

    Args:
        content: The raw message string containing code sections.

    Returns:
        A new string with properly enclosed code blocks.
    """
    lines = content.split("\n")
    formatted_lines = []
    in_code_block = False
    code_block_lines: List[str] = []

    for line in lines:
        if line.strip().startswith("```"):
            # Toggle code block mode
            if in_code_block:
                # Close current code block
                code = "\n".join(code_block_lines)
                formatted_lines.append(f"```{code}```")
                code_block_lines.clear()
                in_code_block = False
            else:
                # Start a new code block
                in_code_block = True
        elif in_code_block:
            code_block_lines.append(line)
        else:
            formatted_lines.append(line)

    # Close any unclosed code block
    if code_block_lines:
        code = "\n".join(code_block_lines)
        formatted_lines.append(f"```{code}```")

    return "\n".join(formatted_lines)

async def process_sse_stream(response: aiohttp.ClientResponse) -> AsyncGenerator[str, None]:
    """
    Process a Server-Sent Events (SSE) response into a stream of raw data messages.

    Args:
        response: An aiohttp response object for an SSE endpoint.

    Yields:
        The text following "data: " blocks.
    """
    buffer = ""
    try:
        async for chunk in response.content:
            if not chunk:
                continue

            try:
                buffer += chunk.decode("utf-8")
                while "\n\n" in buffer:
                    line, buffer = buffer.split("\n\n", 1)
                    if line.startswith("data: "):
                        yield line[6:]  # Remove "data: " prefix
            except UnicodeDecodeError as e:
                print(f"Error decoding chunk: {e}")
                continue
    except Exception as e:
        print(f"Error in SSE stream: {e}")
        raise

@cl.on_chat_start
async def start() -> None:
    """
    Send an initial system message at the start of the chat.
    """
    msg = await create_agent_message(
        content="👋 Welcome! I'm your AI assistant powered by the MagenticTeam. How can I help you today?",
        author="System"
    )
    # Stream the welcome content
    await stream_message(msg, msg.content)

@cl.on_message
async def main(message: cl.Message) -> None:
    """
    Handle incoming messages by forwarding them to the backend's SSE endpoint
    and streaming the responses back to the user.
    """
    try:
        task_content = message.content.strip()
        if not task_content:
            # No content means we won't call the backend
            system_msg = await create_agent_message(
                content="Please enter a valid query or command.",
                author="System"
            )
            await stream_message(system_msg, system_msg.content)
            return

        async with cl.Step("Processing Task"):
            async with aiohttp.ClientSession() as session:
                # Connect to backend SSE stream
                async with session.get(
                    f"{BACKEND_URL}/stream_task",
                    params={"task": task_content},
                    headers={"Accept": "text/event-stream"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Backend returned status {response.status}: {error_text}")
                        raise Exception(f"Backend error (status {response.status}): {error_text}")

                    async for data in process_sse_stream(response):
                        if not data:
                            continue

                        # Attempt to parse each SSE data chunk as JSON
                        try:
                            event = json.loads(data)
                            event_type = event.get("type", "message")
                            source = event.get("source", "System")
                            content = event.get("content", "")
                            usage_info = event.get("usage", None)

                            # Create a Chainlit message
                            msg_event = await create_agent_message("", source)

                            if event_type == "plan":
                                plan_title = event.get("title", "Execution Plan")
                                plan_description = event.get("description", "")
                                plan_content = f"📝 {plan_title}\n\n{plan_description}"
                                await stream_message(msg_event, plan_content)

                            elif event_type == "summary":
                                duration = event.get("duration", 0)
                                prompt_tokens = event.get("total_prompt_tokens", 0)
                                completion_tokens = event.get("total_completion_tokens", 0)
                                summary_text = (
                                    f"Task completed in {duration:.2f}s.\n"
                                    f"Prompt tokens: {prompt_tokens}\n"
                                    f"Completion tokens: {completion_tokens}"
                                )
                                await stream_message(msg_event, summary_text)

                            elif event_type == "error":
                                error_label = "Error"
                                error_content = f"{error_label}: {content}"
                                await stream_message(msg_event, error_content)

                            else:
                                # Regular message content
                                await stream_message(msg_event, str(content))

                            # Optionally display usage info if present
                            if usage_info:
                                usage_msg = await create_agent_message("", "System")
                                usage_string = (
                                    f"Tokens used:\n"
                                    f"- Prompt: {usage_info.get('prompt_tokens', 0)}\n"
                                    f"- Completion: {usage_info.get('completion_tokens', 0)}"
                                )
                                await stream_message(usage_msg, usage_string)

                        except json.JSONDecodeError as e:
                            # Data wasn't valid JSON
                            print(f"JSON decode error: {e}\nRaw data: {data}")
                            raw_msg = await create_agent_message("", "System")
                            await stream_message(raw_msg, data)

    except Exception as e:
        print(f"Error in on_message: {e}")
        error_msg = await create_agent_message("", "System")
        await stream_message(
            error_msg,
            f"An error occurred: {str(e)}\nPlease ensure the backend server is reachable at {BACKEND_URL}."
        )

if __name__ == "__main__":
    cl.run()