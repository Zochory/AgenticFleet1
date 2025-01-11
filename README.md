# AgenticFleet

<div align="left">
<a href="https://pypi.org/project/agentic-fleet/">
   <img alt="Pepy Total Downlods" src="https://img.shields.io/pepy/dt/agentic-fleet">
</a>
<img alt="GitHub License" src="https://img.shields.io/github/license/qredence/agenticfleet">
<img alt="GitHub forks" src="https://img.shields.io/github/forks/qredence/agenticfleet">
<img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/qredence/agenticfleet">
</div>

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/cf5bcfbdbf50493b9b5de381c24dc147)](https://app.codacy.com/gh/Qredence/AgenticFleet/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

AgenticFleet is an Adaptative Agentic System that leverages Chainlit for the frontend interface and FastAPI for the backend, built on the foundation of Autogen & Magentic-One.

![image](https://github.com/user-attachments/assets/2de0ec9d-d9f5-4003-9cdc-45128f0fb909)


## Quick Links
- [Join our Discord Community](https://discord.gg/ebgy7gtZHK)
- [Follow us on Twitter](https://x.com/agenticfleet)
- [Join Early Access Waitlist](https://www.qredence.ai/)

## Features

- Interactive Chainlit 2.0 chat interface 
- FastAPI backend with structured logging and WebSocket support
- General Multi-tasking Agentic System based on Magentic-One
- Advanced prompt engineering with PromptFleet templates
- Dataset and prompt fabric tools for AI training
- Comprehensive error handling and connection management
- Environment-based configuration
- Extensible architecture for future enhancements

## Roadmap (short-term)

- [ ] Add Composio Agent
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

## Prerequisites

- Python 3.10 or later
- uv package manager

## Installation

### From PyPI

The simplest way to install AgenticFleet is via pip:

```bash
pip install agentic-fleet
```

Or with optional dependencies:
```bash
# For development tools
pip install "agentic-fleet[dev,test]"

# For documentation tools
pip install "agentic-fleet[docs]"
```

### From Source

1. Clone the repository:
```bash
git clone https://github.com/qredence/agenticfleet.git
cd agenticfleet
```

2. Create and activate a virtual environment using uv:
```bash
uv venv
. .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

3. Install dependencies:

For basic installation:
```bash
uv pip install -e .
sudo playwright install-deps
sudo apt install -y nodejs npm
npx playwright install-deps
```

For development (includes testing, linting, and formatting tools):
```bash
uv pip install -e ".[dev,test]"
```

For documentation:
```bash
uv pip install -e ".[docs]"
```

4. Configure environment variables:

Copy the example environment file and update it with your settings:
```bash
cp .env.example .env
```

The `.env` file contains all necessary configuration for both backend and frontend:
- Azure Services configuration (OpenAI, Key Vault, etc.)
- External AI Services API keys
- Backend server settings
- Frontend (Chainlit) configuration

## Development

To start the application in development mode, you'll need to run both the backend and frontend servers:

1. Start the backend server:
```bash
cd src/backend
. .venv/bin/activate  # Ensure you're in the virtual environment
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

2. In a new terminal, start the frontend:
```bash
cd src/frontend
. .venv/bin/activate  # Ensure you're in the virtual environment
chainlit run app.py
```

This will:
- Start the backend server at http://localhost:8000
- Launch the Chainlit frontend interface at http://localhost:8001
- Enable real-time communication between frontend and backend
- Provide colored logging output
- Handle graceful shutdown

You can access:
- Backend API documentation at http://localhost:8000/docs
- Frontend Chainlit interface at http://localhost:8001

## Project Structure

```
fleet/
├── src/
│   ├── frontend/              # Chainlit Frontend
│   │   ├── .chainlit/        # Chainlit configuration
│   │   ├── __init__.py
│   │   ├── app.py            # Frontend application
│   │   └── chainlit.md       # Chainlit documentation
│   └── backend/              # FastAPI Backend
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
│       └── app.py              # FastAPI application
├── docs/                      # Documentation
│   └── agentic-fleet.mdx     # Detailed technical documentation
└── README.md
```

## Development

### Code Style and Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
  ```bash
  black src/
  ```

- **isort**: Import sorting
  ```bash
  isort src/
  ```

- **flake8**: Code linting
  ```bash
  flake8 src/
  ```

- **mypy**: Static type checking
  ```bash
  mypy src/
  ```

### Testing

Run tests with pytest:
```bash
pytest
```

Run tests with coverage report:
```bash
pytest --cov
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

## Citation

```bibtex
@misc{fourney2024magenticonegeneralistmultiagentsolving,
    title={Magentic-One: A Generalist Multi-Agent System for Solving Complex Tasks},
    author={Adam Fourney and Gagan Bansal and Hussein Mozannar and Cheng Tan and Eduardo Salinas 
            and Erkang and Zhu and Friederike Niedtner and Grace Proebsting and Griffin Bassman 
            and Jack Gerrits and Jacob Alber and Peter Chang and Ricky Loynd and Robert West 
            and Victor Dibia and Ahmed Awadallah and Ece Kamar and Rafah Hosn and Saleema Amershi},
    year={2024},
    eprint={2411.04468},
    archivePrefix={arXiv},
    primaryClass={cs.AI},
    url={https://arxiv.org/abs/2411.04468}
}
```

For more information about Autogen, visit their [documentation](https://microsoft.github.io/autogen/0.4.0.dev13/index.html).

## License

This project is licensed under the [Apache 2.0 License](LICENSE).
