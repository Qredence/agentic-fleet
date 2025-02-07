# Installation

This guide provides detailed instructions for installing AgenticFleet.

## Prerequisites

Before installing AgenticFleet, ensure you have the following:

*   **Python:** AgenticFleet requires Python 3.10, 3.11, or 3.12. Python 3.13 is not yet supported.
*   **Package Manager:** We recommend using `uv` for fast and reliable dependency management. However, `pip` is also supported.
*   **Azure OpenAI Account:** For production use and access to AI functionalities, you'll need an Azure OpenAI account with API access.
* **Git:** Required for development installation.

## Installation Methods

AgenticFleet offers several installation methods to suit different needs:

### 1. Using uv (Recommended)

`uv` is a fast and efficient package manager. If you don't have it installed, you can install it with pip: `pip install uv`

To install AgenticFleet using `uv`, run:

```bash
uv pip install agentic-fleet
```

### 2. Using pip (Alternative)

If you prefer using `pip`, you can install AgenticFleet with:

```bash
pip install agentic-fleet
```

### 3. Development Installation

For development purposes, you'll need to clone the repository and install the package in editable mode:

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/qredence/agenticfleet.git
    cd agenticfleet
    ```

2.  **Create and activate a virtual environment (recommended):**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate  # On Windows
    ```

3.  **Install `uv` (if not already installed):**
    ```bash
    pip install uv
    ```

4.  **Install AgenticFleet in development mode:**

    ```bash
    uv pip install -e ".[dev]"
    ```
    This command installs AgenticFleet along with its development dependencies.

### 4. Using Docker

AgenticFleet provides a Docker image for containerized deployment:

1.  **Pull the latest image from Docker Hub:**

    ```bash
    docker pull qredence/agenticfleet:latest
    ```

2.  **Run the Docker container:**

    ```bash
    docker run -d -p 8001:8001 -e AZURE_OPENAI_API_KEY=your_api_key -e AZURE_OPENAI_ENDPOINT=your_endpoint -e AZURE_OPENAI_DEPLOYMENT=your_deployment -e AZURE_OPENAI_MODEL=your_model qredence/agenticfleet:latest
    ```
    **Important:** Replace `your_api_key`, `your_endpoint`, `your_deployment`, and `your_model` with your actual Azure OpenAI credentials. You can also set other environment variables as needed (see the "Environment Configuration" section). It's highly recommended to use Docker secrets or environment files for managing sensitive information in a production environment.

## Environment Configuration

AgenticFleet uses environment variables for configuration. We provide a `.env.example` file as a template.

1.  **Copy the example environment file:**

    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**

    Open the `.env` file in a text editor and update the following settings:

    **Required Settings:**

    ```env
    # Azure OpenAI - Required for AI functionality
    AZURE_OPENAI_API_KEY=your_api_key          # Your Azure OpenAI API key
    AZURE_OPENAI_ENDPOINT=your_endpoint        # Your Azure OpenAI service endpoint
    AZURE_OPENAI_DEPLOYMENT=your_deployment    # Your model deployment name
    AZURE_OPENAI_MODEL=your_model             # Your model name (e.g., gpt-4)
    ```

    **Recommended Settings:**

    ```env
    # OAuth - Recommended for secure access (Optional)
    OAUTH_CLIENT_ID=your_client_id            # Your OAuth app client ID
    OAUTH_CLIENT_SECRET=your_client_secret    # Your OAuth app client secret
    OAUTH_REDIRECT_URI=http://localhost:8001/oauth/callback  # OAuth redirect URI
    ```
    The `.env.example` file contains detailed comments explaining each setting. Replace the placeholder values with your actual credentials.

## Verifying Installation

After installation, you can verify that AgenticFleet is set up correctly:

1.  **Start the server:**

    ```bash
    agenticfleet start
    ```

2.  **Access the web interface:**

    Open your web browser and navigate to `http://localhost:8001`.

3.  **Interact with the system:**

    You should see the AgenticFleet interface. Try typing a task or question to test the system.
