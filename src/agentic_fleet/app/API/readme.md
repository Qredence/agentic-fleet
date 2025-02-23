# AgenticFleet API

## Overview
AgenticFleet API is a FastAPI-based backend that provides authentication, messaging, and chat functionalities. It includes user authentication, message handling, and prompt management, integrating seamlessly with Chainlit functionalities.

## Installation & Setup
### Prerequisites
- Python 3.8+
- FastAPI
- Uvicorn
- SQLAlchemy
- Passlib
- Python-Jose

### Installation
1. Clone the repository:
   ```bash
   git clone <repo_url>
   cd AgenticFleet
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   uvicorn src.app.api:app --reload
   ```

## API Endpoints

### Authentication Endpoints
#### `POST /auth/`
Create a new user.

#### `POST /auth/token`
Authenticate and obtain an access token.

### Message Endpoints
#### `POST /message/chat/send`
Send a new message.

### Chat Endpoints
#### `POST /chat/prompt`
Send a prompt.

#### `PUT /chat/prompt`
Update a prompt.

#### `GET /chat/prompt`
Retrieve user-specific prompts.

## Usage
- Use `/auth/token` to get a bearer token.
- Include the token in the `Authorization` header for protected routes.

## License
Apache 2.0

