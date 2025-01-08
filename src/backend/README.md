# Backend

This directory contains the backend API for the Agentic Fleet Management System. It is built using FastAPI and provides a multi-agent system with specialized agents for different tasks.

## Functionality

The backend API provides:

-   Real-time communication via WebSocket
-   Multi-agent system architecture
-   Prompt engineering tools
-   Dataset generation capabilities
-   Comprehensive logging and monitoring

### API Endpoints

-   `/health`: Checks the health status of the service and whether the agent team is initialized.
-   `/run_task`: Accepts a task description and runs it using the agent team.
-   `/stream_task`: Streams the task execution output in real-time using Server-Sent Events (SSE).
-   `/ws`: WebSocket endpoint for real-time communication.

## Dependencies

The backend has the following core dependencies:

-   `fastapi`: Modern web framework for building APIs
-   `uvicorn`: ASGI server implementation
-   `chainlit`: Interactive chat interface
-   `magentic`: Core AI functionality
-   `autogen`: Agent system framework
-   `azure-*`: Azure service integrations
-   `websockets`: WebSocket support
-   Additional dependencies are listed in `pyproject.toml`

## Setup

1. Navigate to the backend directory:
    ```bash
    cd src/backend
    ```

2. Create a virtual environment using uv:
    ```bash
    uv venv
    ```

3. Activate the virtual environment:
    ```bash
    . .venv/bin/activate  # On Unix/macOS
    # or
    .venv\Scripts\activate  # On Windows
    ```

4. Install dependencies:
    ```bash
    uv pip install -e .
    ```

5. Create a `.env` file with required environment variables:
    ```env
    APP_HOST=0.0.0.0
    APP_PORT=8000
    DEBUG=false
    LOG_LEVEL=INFO
    ```

## Running the Backend

Start the backend server:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

For the Chainlit frontend:

```bash
chainlit run agentic-fleet.frontend.app
```

## API Documentation

### Health Check

```http
GET /health
```

Returns:
```json
{
  "status": "healthy",
  "team_initialized": true,
  "agents": ["Composio", "MultiModalSurfer"]
}
```

### Run Task

```http
POST /run_task
{
  "task": "Analyze this dataset and generate a report"
}
```

Returns:
```json
{
  "status": "accepted",
  "message": "Task accepted and being processed",
  "thought": "Planning task execution strategy",
  "plan": "1. Analyze dataset\n2. Generate insights\n3. Create report"
}
```

### Stream Task

```http
GET /stream_task?task=analyze_data
```

Returns SSE stream:
```
event: plan
data: {"type": "plan", "content": "Task execution plan..."}

event: progress
data: {"type": "progress", "agent": "Composio", "status": "Processing..."}

event: result
data: {"type": "result", "content": "Analysis complete..."}
```

## Logging

The backend uses structured logging with two main loggers:

-   `system_logger`: System-level events and errors
-   `team_logger`: Agent team activities and task execution

Log format:
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "event": "task_started",
  "agent": "Composio",
  "details": {
    "task_id": "123",
    "task_type": "analysis"
  }
}
```

## Error Handling

Errors are handled at multiple levels:

1. API Level
   - Input validation
   - Authentication/Authorization
   - Rate limiting

2. Agent Level
   - Task execution errors
   - Resource allocation
   - Communication failures

3. System Level
   - Connection handling
   - Resource management
   - Graceful degradation

## Development Guidelines

1. Code Style
   - Follow PEP 8
   - Use type hints
   - Document functions and classes

2. Testing
   - Write unit tests
   - Include integration tests
   - Test error scenarios

3. Logging
   - Use appropriate log levels
   - Include context in log messages
   - Monitor performance metrics

4. Error Handling
   - Use custom exceptions
   - Provide clear error messages
   - Implement proper fallbacks
