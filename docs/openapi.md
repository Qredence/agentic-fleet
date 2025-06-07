# OpenAPI Documentation

This document describes the OpenAPI documentation feature added to Agentic Fleet.

## Overview

Agentic Fleet now provides comprehensive OpenAPI documentation for its REST API, making it easy for developers to understand and interact with the system.

## Accessing the Documentation

The API documentation is available in multiple formats:

### Interactive Swagger UI
- **URL**: `/docs`
- **Description**: Interactive documentation where you can test API endpoints directly
- **Features**: 
  - Try out API calls directly from the browser
  - View request/response schemas
  - See example requests and responses

### ReDoc Documentation
- **URL**: `/redoc`
- **Description**: Clean, readable documentation with a focus on readability
- **Features**:
  - Beautiful, responsive design
  - Detailed schema documentation
  - Code samples in multiple languages

### OpenAPI JSON Specification
- **URL**: `/openapi.json`
- **Description**: Raw OpenAPI 3.0 specification in JSON format
- **Use cases**:
  - Generate client SDKs
  - Import into API testing tools
  - Integrate with other documentation systems

## API Endpoints

The API is organized into the following main categories:

### Health & Status
- `GET /` - API information and status
- `GET /health` - Detailed health check with system information

### Agent Management
- `GET /agents` - List all agents
- `POST /agents` - Create a new agent
- `GET /agents/{agent_id}` - Get agent details
- `PUT /agents/{agent_id}` - Update an agent
- `DELETE /agents/{agent_id}` - Delete an agent

### Task Management
- `GET /tasks` - List all tasks
- `POST /tasks` - Create a new task
- `GET /tasks/{task_id}` - Get task details
- `PUT /tasks/{task_id}` - Update a task
- `DELETE /tasks/{task_id}` - Delete a task
- `POST /tasks/{task_id}/assign/{agent_id}` - Assign task to agent

### Chat Interface
- `GET /chat/messages` - Get chat history
- `POST /chat/messages` - Send a message
- `WebSocket /chat/ws` - Real-time chat connection

### System Configuration
- `GET /api/models` - Get available LLM models.
- `GET /api/profiles` - Get available LLM configuration profiles.

## Running the API

To start the API server with OpenAPI documentation:

```bash
# Using the main entry point
python -m agentic_fleet.main

# Or run the API module directly
python src/agentic_fleet/api/main.py
```
The Chainlit UI will be available at `/ui` and the API documentation at `/docs` and `/redoc`.

The server will start on `http://localhost:8000` by default.

## Environment Variables

You can configure the API using environment variables:

- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8000`)
- `RELOAD` - Enable auto-reload for development (default: `False`)
- `ENVIRONMENT` - Environment name (default: `development`)

## Testing the API

A test script is provided to verify the API functionality:

```bash
python test_api.py
```

This script will test:
- Root endpoint accessibility
- OpenAPI JSON generation
- Swagger UI availability
- ReDoc availability
- Health check functionality

## Features

### Comprehensive Documentation
- Detailed descriptions for all endpoints
- Request/response schema documentation
- Example requests and responses
- Error response documentation

### Interactive Testing
- Test API endpoints directly from the Swagger UI
- Real-time validation of requests
- Immediate feedback on responses

### Developer-Friendly
- Clear organization with tags
- Consistent naming conventions
- Proper HTTP status codes
- Detailed error messages

### Standards Compliant
- OpenAPI 3.0 specification
- RESTful API design
- Standard HTTP methods and status codes

## Future Enhancements

Planned improvements for the OpenAPI documentation:

1. **Authentication Documentation**: Once authentication is implemented
2. **Rate Limiting Information**: Documentation of rate limits
3. **Webhook Documentation**: If webhook support is added
4. **SDK Generation**: Automated client SDK generation
5. **API Versioning**: Support for multiple API versions

## Troubleshooting

### Common Issues

1. **Documentation not loading**
   - Ensure the server is running
   - Check that you're accessing the correct URL
   - Verify no firewall is blocking the port

2. **Missing endpoints in documentation**
   - Ensure all route modules are properly imported
   - Check that routers are included in the main app
   - Verify endpoint decorators are correct

3. **Schema validation errors**
   - Check Pydantic model definitions
   - Ensure all required fields are documented
   - Verify response model annotations

### Getting Help

If you encounter issues with the OpenAPI documentation:

1. Check the server logs for error messages
2. Verify the OpenAPI JSON is valid at `/openapi.json`
3. Test individual endpoints using curl or similar tools
4. Report issues on the GitHub repository

## Contributing

To contribute to the API documentation:

1. Follow the existing documentation patterns
2. Add comprehensive docstrings to new endpoints
3. Include proper type hints and response models
4. Test the documentation after changes
5. Update this README if adding new features