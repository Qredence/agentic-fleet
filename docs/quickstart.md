# Quickstart

This guide will get you started with AgenticFleet in minutes.

## Installation

1.  **Install AgenticFleet:**

    The recommended way to install AgenticFleet is using `uv`:

    ```bash
    uv pip install agentic-fleet
    ```

    If you don't have `uv`, you can use `pip`:

    ```bash
    pip install agentic-fleet
    ```

## Configuration

1.  **Create a `.env` file:**

    Copy the `.env.example` file to `.env`:

    ```bash
    cp .env.example .env
    ```

2.  **Configure Azure OpenAI:**

    You'll need an Azure OpenAI account and API key. Update the following variables in your `.env` file:

    ```env
    AZURE_OPENAI_API_KEY=your_api_key
    AZURE_OPENAI_ENDPOINT=your_endpoint
    AZURE_OPENAI_DEPLOYMENT=your_deployment
    AZURE_OPENAI_MODEL=your_model
    ```

    Replace `your_api_key`, `your_endpoint`, `your_deployment`, and `your_model` with your actual Azure OpenAI credentials.

## Basic Usage

1.  **Start the server:**

    ```bash
    agenticfleet start
    ```

2.  **Access the web interface:**

    Open your web browser and go to `http://localhost:8001`.

3.  **Start a conversation:**

    Type your task or question in the chat input and press Enter. AgenticFleet will use the configured agents to process your request.

    For example, try typing: "Write a python function to reverse a string"

## Example Interaction
After starting the server and accessing the web interface, you can interact with AgenticFleet. Here's a simple example:

**User Input:**
```
Write a python function to reverse a string
```

**AgenticFleet Response (example):**

```
### 💻 Code Assistant
Here's a Python function to reverse a string:

```python
def reverse_string(s: str) -> str:
    """Reverses a string.

    Args:
        s: The string to reverse.

    Returns:
        The reversed string.
    """
    return s[::-1]
```

You can test the function like this:

```python
# Test the function
string_to_reverse = "hello"
reversed_string = reverse_string(string_to_reverse)
print(f"Original string: {string_to_reverse}")
print(f"Reversed string: {reversed_string}")

```

</final_file_content>
</write_to_file>
