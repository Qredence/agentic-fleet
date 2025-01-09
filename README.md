# AgenticFleet

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/127fb3f8aa894b1ba6694bd03594a26f)](https://app.codacy.com/gh/Qredence/AgenticFleet?utm_source=github.com&utm_medium=referral&utm_content=Qredence/AgenticFleet&utm_campaign=Badge_Grade)

<div align="left">
<a href="https://pypi.org/project/agentic-fleet/">
   <img alt="Pepy Total Downlods" src="https://img.shields.io/pepy/dt/agentic-fleet">
   </a>
   <img alt="GitHub License" src="https://img.shields.io/github/license/qredence/agenticfleet">
   <img alt="GitHub forks" src="https://img.shields.io/github/forks/qredence/agenticfleet">
   <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/qredence/agenticfleet">

</div>

[Join the discord
](https://discord.gg/ebgy7gtZHK)

[Follow AgenticFleet on Twitter](https://x.com/agenticfleet) to stay updated and announcement, coming heavily just a matter of polish for the set of underlying solutions coming !

[Join the Early Access Waitlist](https://www.qredence.ai/)

> [!CAUTION]
> In early beta, expect changes, more detail soon, expect for AgenticFleet approximatly  3-4 git push/week minimum.




AgenticFleet is an Adaptative Agentic System in beta that currently  uses Chainlit for the frontend interface and FastAPI for the backend, based on the ground work of Autogen & Magentic-One

## Features

- Interactive Chainlit 2.0 chat interface 
- FastAPI backend with structured logging and WebSocket support
- General Multi-tasking Agentic System based on Magentic-One
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
git clone https://github.com/qredence/agenticfleet.git
cd agenticfleet
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
chainlit run agentic-fleet/frontend/app.py
```

This will:
- Start the backend server at http://localhost:8000
- Launch the Chainlit frontend interface http://localhost:8001
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


## Roadmap

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

@misc{fourney2024magenticonegeneralistmultiagentsolving,
      title={Magentic-One: A Generalist Multi-Agent System for Solving Complex Tasks},
      author={Adam Fourney and Gagan Bansal and Hussein Mozannar and Cheng Tan and Eduardo Salinas and Erkang and Zhu and Friederike Niedtner and Grace Proebsting and Griffin Bassman and Jack Gerrits and Jacob Alber and Peter Chang and Ricky Loynd and Robert West and Victor Dibia and Ahmed Awadallah and Ece Kamar and Rafah Hosn and Saleema Amershi},
      year={2024},
      eprint={2411.04468},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2411.04468},
}

[Autogen](https://microsoft.github.io/autogen/0.4.0.dev13/index.html) 

## License

This project is licensed under the Apache 2.0 License.
