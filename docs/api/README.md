# AgenticFleet API Documentation

## Overview

AgenticFleet is a powerful multi-agent system that combines Chainlit's interactive interface with AutoGen's multi-agent capabilities. This documentation provides detailed information about the API, its components, and usage patterns.

## Table of Contents

1. [Getting Started](./getting-started.md)
2. [Core Components](./core-components.md)
3. [Agents](./agents.md)
4. [Models](./models.md)
5. [Configuration](./configuration.md)
6. [Message Handling](./messages.md)
7. [Web Interface](./web-interface.md)
8. [Authentication](./authentication.md)
9. [Error Handling](./error-handling.md)
10. [Best Practices](./best-practices.md)

## Quick Start

```python
from agentic_fleet.models import create_agent_team
from agentic_fleet.app import initialize_session

# Create an agent team
team = await create_agent_team("Solve complex coding tasks")

# Initialize a session
session = await initialize_session()

# Start interaction
await session.start()
```

For detailed installation instructions, see our [Installation Guide](../installation.md).

## Support

For support, please:
1. Check our [documentation](https://docs.agenticfleet.ai)
2. Open an issue on our [GitHub repository](https://github.com/qredence/agenticfleet)
3. Contact us at support@qredence.ai
