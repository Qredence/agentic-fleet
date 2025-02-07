# Usage Guide

This guide provides instructions on how to use AgenticFleet, covering both the web interface and the command-line interface (CLI).

## Getting Started

After installing and configuring AgenticFleet (see the [Installation](./installation.md) guide), you can start using it in two main ways:

1.  **Web Interface:** This is the primary way to interact with AgenticFleet, providing a user-friendly chat interface.
2.  **Command-Line Interface (CLI):** The CLI offers advanced options and is useful for scripting and automation.

### Basic Usage (Web Interface)

1.  **Start the Server:**

    Open your terminal and run:

    ```bash
    agenticfleet start
    ```

2.  **Access the Web Interface:**

    Open your web browser and go to `http://localhost:8001`.

3.  **Start a Conversation:**

    Type your task or question in the chat input box and press Enter (or click the send button). AgenticFleet will use the configured agents (powered by Autogen) to process your request.

### Example Interaction
**User Input:**
```
Write a python function to reverse a string, and test it.
```

**AgenticFleet Response (example):**

```
### 💻 Code Assistant
Here's a Python function to reverse a string, along with a test case:

```python
def reverse_string(s: str) -> str:
    """Reverses a string.

    Args:
        s: The string to reverse.

    Returns:
        The reversed string.
    """
    return s[::-1]

# Test the function
test_string = "hello"
reversed_string = reverse_string(test_string)
print(f"Original string: {test_string}")
print(f"Reversed string: {reversed_string}")

```

## Web Interface Features

The AgenticFleet web interface provides a rich set of features for interacting with agents:

*   **Chat Interface:**
    *   **Code Highlighting:** Automatic syntax highlighting for code blocks in various programming languages.
    *   **Markdown Support:** Rich text formatting using Markdown.
    *   **File Upload:** Drag and drop files directly into the chat to provide context for your tasks.
    *   **Progress Indicators:** Real-time visualization of task progress.
*   **Agent Interaction:**
    *   **Task Submission:** Type your task in natural language, attach files if needed, and submit.
    *   **Response Interpretation:** Agent responses are color-coded for clarity. Code blocks are automatically formatted. File operations and web search results are clearly indicated.
    *   **Task Control:**  Options to pause, resume, or cancel ongoing tasks (functionality may depend on the underlying Autogen agents).
    * **Conversation History:** Ability to save and load conversation history.
* **Settings:**
    * **Dark/Light Mode:** Switch between dark and light themes.

## Command Line Interface (CLI)

The AgenticFleet CLI provides several commands for managing the system:

```bash
# Start the server with default settings
agenticfleet start

# Start the server without OAuth authentication
agenticfleet start --no-oauth

# Start the server on a custom port
agenticfleet start --port 8080

# Start the server with debug logging enabled
agenticfleet start --debug
```

## Advanced Features

### OAuth Authentication (Optional)

For secure access, you can enable OAuth authentication:

1.  **Configure OAuth variables:** Set the `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, and `OAUTH_REDIRECT_URI` environment variables in your `.env` file.
2.  **Start the server:**  The `agenticfleet start` command will automatically use the OAuth settings if they are configured.
3.  **Login:** Users will be redirected to the configured OAuth provider (e.g., GitHub) for login.

### Agent Interaction and Autogen

AgenticFleet leverages the Microsoft Autogen framework for agent creation and management.  Understanding Autogen concepts will help you utilize AgenticFleet effectively.

*   **Agents:** AgenticFleet uses Autogen's agents, such as `AssistantAgent` and `UserProxyAgent`. These agents can communicate with each other and with LLMs to perform tasks.
*   **Workflows:**  You can define complex workflows involving multiple agents collaborating to achieve a goal.
* **Customization:** While AgenticFleet provides a user-friendly interface, you can customize agent behavior by modifying the underlying Autogen configurations.  Refer to the Autogen documentation for more details: [https://microsoft.github.io/autogen/](https://microsoft.github.io/autogen/)

*   **Examples:** Explore the official Autogen examples for inspiration and practical use cases: [https://github.com/microsoft/autogen/tree/main/samples](https://github.com/microsoft/autogen/tree/main/samples)

## Best Practices

*   **Task Description:**
    *   Be as specific as possible when describing your tasks.
    *   Provide sufficient context for the agents to understand your requirements.
    *   Break down complex tasks into smaller, more manageable steps.
*   **Code Generation:**
    *   Specify the desired programming language.
    *   Include requirements for error handling and performance.
*   **File Management:**
    *   Organize files logically within your project.
    *   Use consistent naming conventions.
*   **Error Handling:**
    *   Monitor agent progress and review any error messages.
    *   Adjust settings or task descriptions as needed.

## Troubleshooting

Here are some solutions to common issues:

*   **Connection Issues:**
    *   Ensure the AgenticFleet server is running.
    *   Check that the specified port (default: 8001) is not blocked by a firewall.
    *   Verify your OAuth configuration if you are using authentication.
*   **Performance Problems:**
    *   If you are experiencing slow performance, try reducing the `max_rounds` setting (if applicable).
    *   Limit the number of concurrent tasks.
*   **Authentication Errors:**
    *   Verify your OAuth credentials (client ID, client secret, redirect URI).
    *   Ensure that the redirect URI is correctly configured in your OAuth provider's settings.
