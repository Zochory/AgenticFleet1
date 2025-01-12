# AgenticFleet Documentation

## Overview

AgenticFleet is a next-generation AI assistant platform that combines Chainlit for the frontend interface with a multi-agent architecture powered by AutoGen and Magentic-One. It features a flexible agent system, real-time communication, and comprehensive error handling.

## Architecture

### Implementation Approaches

The system offers two implementation approaches in the `src/app` directory:

#### 1. Direct Agent Integration (app.py)
The primary implementation that directly integrates with the agent system:
- Direct communication with Azure OpenAI
- Real-time agent team coordination
- Efficient message streaming
- Built-in code block formatting
- Markdown rendering support

#### 2. Backend Communication (_app.py)
An alternative implementation that uses a backend server:
- Server-Sent Events (SSE) for real-time updates
- Detailed token usage tracking
- Character-by-character streaming
- Color-coded agent messages
- Thought process visualization

### Core Components

#### 1. Agent System
The platform includes specialized agents:

- **MagenticOneCoderAgent**: 
  - Handles code-related tasks
  - Provides code analysis and generation
  - Supports multiple programming languages

- **MultimodalWebSurfer**: 
  - Web content analysis
  - URL processing
  - Data extraction

- **FileSurfer**: 
  - File system navigation
  - Content analysis
  - File operations

#### 2. Team Orchestration
The MagenticOneGroupChat manages agent coordination:
- Dynamic task distribution
- Real-time communication
- Response streaming
- Error handling

#### 3. Message Handling
Comprehensive message processing:
- Agent-specific formatting
- Code block syntax highlighting
- Markdown rendering
- Token usage tracking
- Progress indicators

## Implementation Details

### 1. Agent Configuration

Agents are initialized with Azure OpenAI integration:

```python
az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    model=os.getenv("AZURE_OPENAI_MODEL"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)
```

### 2. Message Handling

Messages are formatted with agent-specific styling:

```python
def format_agent_message(agent_name: str, content: str) -> str:
    agent_prefixes = {
        "WebSurfer": "🌐 Web Search",
        "FileSurfer": "📁 File Analysis",
        "Coder": "💻 Code Assistant",
        "MagenticOneOrchestrator": "🎭 Orchestrator",
        "system": "🤖 System"
    }
```

### 3. Real-time Communication

The system uses Chainlit's streaming capabilities for real-time responses:

```python
async for response in team.run_stream(task=message.content):
    if hasattr(response, 'content'):
        # Handle streaming response
        await cl.Message(
            content=formatted_content,
            author=agent_name,
            language="markdown"
        ).send()
```

## Alternative Implementations

### CogCache Integration

For alternative LLM providers, CogCache integration is available:

```python
cogcache_client = OpenAIChatCompletionClient(
    base_url = "https://proxy-api.cogcache.com/v1/",
    api_key = os.getenv('COGCACHE_API_KEY'),
    model = "gpt-4o-mini-2024-07-18",
    default_headers = { 
        "Authorization": f"Bearer {os.getenv('COGCACHE_API_KEY')}",
    },
)
```

## Configuration

### Environment Variables

Required environment variables:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT=deployment_name
AZURE_OPENAI_MODEL=model_name
AZURE_OPENAI_API_VERSION=api_version

# Chainlit Configuration
CHAINLIT_AUTH_SECRET=your_secret
CHAINLIT_URL=http://localhost:8001

# OAuth Configuration (Optional)
OAUTH_GITHUB_CLIENT_ID=your_client_id
OAUTH_GITHUB_CLIENT_SECRET=your_client_secret
```

## Features

### Current Features

1. **Multi-Agent System**
   - Specialized agents for different tasks
   - Real-time agent coordination
   - Streaming responses
   - Agent-specific message formatting

2. **Authentication**
   - OAuth support
   - GitHub integration
   - Custom authentication callbacks

3. **User Interface**
   - Markdown support
   - Code syntax highlighting
   - Agent-specific styling
   - Real-time updates
   - Progress indicators

### Planned Features

1. **Enhanced Agent Capabilities**
   - Composio Agent integration
   - Advanced task planning
   - Improved coordination

2. **Infrastructure**
   - Cloud integration
   - Message persistence
   - Enhanced file handling

## Technical Requirements

- Python 3.10 or later
- uv package manager
- Node.js and npm (for development)
- Playwright dependencies

## Getting Started

1. Install dependencies:
```bash
uv venv
. .venv/bin/activate
uv pip install -e .
```

2. Configure environment variables:
```bash
cp .env.example .env
```

3. Start the application:
```bash
chainlit run src/app/app.py
```

## Error Handling

The system implements comprehensive error handling:
- Agent-specific error handling
- User-friendly error messages
- Proper error formatting and display
- Async operation error management

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details on:
- Code style guidelines
- Testing requirements
- Pull request process
- Development setup

## License

Licensed under the [Apache 2.0 License](../LICENSE).
