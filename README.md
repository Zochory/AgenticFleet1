# AgenticFleet

AgenticFleet is a powerful AI assistant application that uses Chainlit for the frontend interface and FastAPI for the backend, featuring real-time communication and advanced AI capabilities.

## Features

- Interactive Chainlit-based chat interface with real-time updates
- FastAPI backend with structured logging and WebSocket support
- Multi-agent system with specialized agents (Composio, Multi-modal Surfer)
- Advanced prompt engineering with PromptFleet templates
- Dataset and prompt fabric tools for AI training
- Comprehensive error handling and connection management
- Environment-based configuration
- Extensible architecture for future enhancements

## Prerequisites

- Python 3.10 or later
- uv package manager

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fleet.git
cd fleet
```

2. Create and activate a virtual environment using uv:
```bash
cd src/backend
uv venv
. .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
uv pip install -e .
```

4. Configure environment variables:

Backend (.env):
```env
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

Frontend (.env):
```env
BACKEND_URL=http://localhost:8000
```

## Development

To start the application in development mode:

```bash
cd src/backend
. .venv/bin/activate  # Ensure you're in the virtual environment
chainlit run agentic-fleet.frontend.app
```

This will:
- Start the backend server at http://localhost:8000
- Launch the Chainlit frontend interface
- Enable real-time communication
- Provide colored logging output
- Handle graceful shutdown

## Project Structure

```
fleet/
├── src/
│   └── backend/
│       ├── agentic-fleet/
│       │   ├── frontend/
│       │   │   ├── __init__.py
│       │   │   └── app.py       # Chainlit frontend application
│       │   └── models/
│       │       └── __init__.py  # Models initialization
│       ├── agents/
│       │   ├── composio_agent.py    # Composio agent implementation
│       │   └── multi-modal-surfer.py # Multi-modal surfing agent
│       ├── models/
│       │   ├── config.py        # Configuration management
│       │   ├── logging.py       # Structured logging
│       │   ├── messages.py      # Message type definitions
│       │   └── azure_client.py  # Azure services integration
│       ├── labs/
│       │   ├── dataset_fabric/  # Dataset generation tools
│       │   ├── prompt_fabric/   # Prompt engineering tools
│       │   └── promptfleet/     # Prompt templates
│       ├── app.py              # FastAPI application
│       └── pyproject.toml      # Python project configuration
├── docs/                       # Documentation
│   └── agentic-fleet.mdx      # Detailed technical documentation
└── README.md
```

## Error Handling

The application implements comprehensive error handling:
- Connection errors with automatic retry
- Input validation errors
- Server-side errors with proper status codes
- User-friendly error messages in the UI
- Agent-specific error handling and recovery

## Logging

Structured logging is implemented with:
- Different log levels (DEBUG, INFO, WARNING, ERROR)
- JSON-formatted log output
- Timestamp and context information
- Error tracking with stack traces
- Agent activity monitoring
- Performance metrics

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your PR:
- Includes appropriate tests
- Updates documentation as needed
- Follows the existing code style
- Includes proper error handling
- Has meaningful commit messages

## Roadmap

- [x] Add Composio Agent
- [x] Add Multi-modal Surfer agent
- [ ] Improve backend main Agentic AI (based on Autogen and Magentic-One)
- [ ] Add a pool of LLM model auto-select for each agent
- [ ] Improve the generalist multi-tasking agentic fleet
- [ ] Add a Cloud service with OAuth + Freetier
- [ ] Add pre-release of AgenticFabric
- [ ] Release of the GraphFleet refactor
- [ ] Fix interoperability between AgenticFleet and GraphFleet
- [ ] Add message persistence
- [ ] Implement user authentication
- [ ] Add file sharing capabilities
- [ ] Enhance UI/UX with more interactive features

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
