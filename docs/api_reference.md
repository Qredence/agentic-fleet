# API Reference

This document provides an overview of AgenticFleet's HTTP API endpoints. For detailed request/response schemas, Pydantic models, and interactive testing, please refer to the auto-generated OpenAPI documentation available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the server is running.

## HTTP API Endpoints

The API is organized into the following categories:

### Health & Status

-   **`GET /`**
    -   Returns basic information about the API, its version, and links to the interactive documentation.
-   **`GET /health`**
    -   Provides a detailed health check of the API, including database connectivity status and system information.

### Agent Management

-   **`GET /agents`**
    -   Retrieves a list of all available agents.
-   **`POST /agents`**
    -   Creates a new agent. The request body should conform to the agent creation schema.
-   **`GET /agents/{agent_id}`**
    -   Fetches detailed information for a specific agent identified by `agent_id`.
-   **`PUT /agents/{agent_id}`**
    -   Updates an existing agent identified by `agent_id`. The request body should contain the fields to be updated.
-   **`DELETE /agents/{agent_id}`**
    -   Deletes a specific agent identified by `agent_id`.

### Task Management

-   **`GET /tasks`**
    -   Retrieves a list of all tasks.
-   **`POST /tasks`**
    -   Creates a new task. The request body should conform to the task creation schema.
-   **`GET /tasks/{task_id}`**
    -   Fetches detailed information for a specific task identified by `task_id`.
-   **`PUT /tasks/{task_id}`**
    -   Updates an existing task identified by `task_id`. The request body should contain the fields to be updated.
-   **`DELETE /tasks/{task_id}`**
    -   Deletes a specific task identified by `task_id`.
-   **`POST /tasks/{task_id}/assign/{agent_id}`**
    -   Assigns a task (identified by `task_id`) to an agent (identified by `agent_id`).

### Chat Interface

-   **`GET /chat/messages`**
    -   Retrieves chat history, typically requiring a session identifier as a query parameter.
-   **`POST /chat/messages`**
    -   Sends a new message to a chat session. The request body should include the message content and session identifier.
-   **`WebSocket /chat/ws`**
    -   The WebSocket endpoint for establishing a real-time, bidirectional communication channel for interactive chat.

### System Configuration

-   **`GET /api/models`**
    -   Retrieves a list of available Language Learning Models (LLMs) configured in the system.
-   **`GET /api/profiles`**
    -   Retrieves a list of available configuration profiles for LLMs.

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of a request. When an error occurs, the response body will typically contain a JSON object with a "detail" field explaining the error. For more specific error structures, refer to the exception handlers in `src/agentic_fleet/api/main.py`.
