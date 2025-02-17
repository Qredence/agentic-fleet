from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from chainlit import chainlit_app
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Include Chainlit app as a sub-application
app.mount("/chainlit", chainlit_app)

# Add CORS middleware
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the AgenticFleet FastAPI app!"}

# Define OAuth callback endpoint
@app.get("/auth/callback")
async def oauth_callback(request: Request):
    try:
        # Handle OAuth callback logic here
        return JSONResponse(content={"message": "OAuth callback successful"})
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Define chat start endpoint
@app.post("/chat/start")
async def chat_start(request: Request):
    try:
        # Initialize a new chat session
        return JSONResponse(content={"message": "Chat session started"})
    except Exception as e:
        logger.error(f"Chat start error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Define message handling endpoint
@app.post("/chat/message")
async def handle_message(request: Request):
    try:
        # Handle incoming messages
        return JSONResponse(content={"message": "Message received"})
    except Exception as e:
        logger.error(f"Message handling error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Define settings update endpoint
@app.post("/chat/settings")
async def update_settings(request: Request):
    try:
        # Handle settings update
        return JSONResponse(content={"message": "Settings updated"})
    except Exception as e:
        logger.error(f"Settings update error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Define stop endpoint
@app.post("/chat/stop")
async def stop(request: Request):
    try:
        # Handle cleanup when the application stops
        return JSONResponse(content={"message": "Application stopped"})
    except Exception as e:
        logger.error(f"Stop error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
