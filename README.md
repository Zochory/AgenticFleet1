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



https://github.com/user-attachments/assets/e36b215a-4fac-4b2a-95e2-90ce7701f277





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


## Installation

### From PyPI

Recommanded : create a virtual environment using uv:

```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
``` 



The simplest way to install AgenticFleet is via pip:

```bash
pip install agentic-fleet
```
Copy the example environment file and update it with your settings:

```bash
cp .env.example .env
```

Then, you can run the application using the `chainlit` command:

```bash
chainlit run src/app/app.py
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

Additional dependencies may be required for certain features. For example, to install Playwright dependencies:

```bash
sudo playwright install-deps
sudo apt install -y nodejs npm
npx playwright install-deps
```

## Roadmap (short-term)

Current Progress:
- [x] Implement core multi-agent architecture
- [x] Add Multi-modal Surfer agent
- [x] Add FileSurfer agent
- [x] Integrate Chainlit 2.0 frontend
- [x] Add OAuth authentication support
- [x] Implement real-time streaming responses
- [x] Add CogCache integration

Short-term Goals:
- [ ] Add Composio Agent
- [ ] Implement LLM model auto-selection
- [ ] Enhance agent coordination
- [ ] Add message persistence
- [ ] Improve file handling capabilities
- [ ] Release AgenticFabric
- [ ] Implement GraphFleet integration
- [ ] Develop AI training tools

Mid-term Goals:
- [ ] Launch cloud service with OAuth + Freetier
- [ ] Create comprehensive prompt engineering suite
- [ ] Build enterprise deployment options
- [ ] Establish agent marketplace
- [ ] Enable cross-platform interoperability
- [ ] Enhance UI/UX features
- [ ] Implement advanced monitoring
- [ ] Add automated error recovery

## Prerequisites

- Python 3.10 or later
- uv package manager




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

To start the application in development mode:

```bash
# Ensure you're in the virtual environment
. .venv/bin/activate

# Start the Chainlit application
chainlit run src/app/app.py
```

This will:
- Launch the Chainlit interface at http://localhost:8001
- Enable real-time agent communication
- Provide colored logging output
- Handle graceful shutdown





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

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Qredence/AgenticFleet&type=Date)](https://star-history.com/#Qredence/AgenticFleet&Date) 
