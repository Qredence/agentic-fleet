# Installation Guide

## Prerequisites

Before installing AgenticFleet, ensure you have:

- Python 3.10-3.12 (Python 3.13 is not yet supported)
- uv package manager (recommended) or pip
- An Azure OpenAI account with API access (for production use)

## Installation Methods

### Using uv (Recommended)

```bash
uv pip install agentic-fleet
```

### Using pip (Alternative)

```bash
pip install agentic-fleet
```

### Development Installation

1. Clone the repository:
```bash
git clone https://github.com/qredence/agenticfleet.git
cd agenticfleet
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install uv (if not already installed):
```bash
pip install uv
```

4. Install in development mode:
```bash
uv pip install -e ".[dev]"
```

## Environment Configuration

We provide an `.env.example` file with all the necessary configuration settings. Follow these steps:

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Open the `.env` file in your editor and update these settings:

**Required Settings:**
```env
# Azure OpenAI - Required for the AI functionality
AZURE_OPENAI_API_KEY=your_api_key          # Your Azure OpenAI API key
AZURE_OPENAI_ENDPOINT=your_endpoint        # Azure OpenAI service endpoint
AZURE_OPENAI_DEPLOYMENT=your_deployment    # Model deployment name
AZURE_OPENAI_MODEL=your_model             # Model name (e.g., gpt-4)
```

**Recommended Settings:**
```env
# OAuth - Recommended for secure access
OAUTH_CLIENT_ID=your_client_id            # OAuth app client ID
OAUTH_CLIENT_SECRET=your_client_secret    # OAuth app client secret
OAUTH_REDIRECT_URI=http://localhost:8001/oauth/callback
```

The `.env.example` file includes comments explaining each setting. Simply replace the placeholder values with your actual credentials.

## Verifying Installation

1. Start the server:
```bash
agenticfleet start
```

2. Visit `http://localhost:8001` in your browser

3. You should see the AgenticFleet interface and be able to interact with the system.

## Using Docker Image

The Docker image for AgenticFleet is available on Docker Hub. You can pull the latest image using the following command:

```bash
docker pull qredence/agenticfleet:latest
```

To run the Docker container, use the following command:

```bash
docker run -d -p 8001:8001 qredence/agenticfleet:latest
```
