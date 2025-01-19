"""
Web interface example demonstrating AgenticFleet with Chainlit.
"""

import logging
from typing import Optional

import chainlit as cl
from chainlit.input_widget import Select, Slider
from agentic_fleet.app import initialize_session, handle_message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UI Elements
model_selector = Select(
    label="Model",
    values=["gpt-4", "gpt-3.5-turbo"],
    initial_value="gpt-4"
)

temperature_slider = Slider(
    label="Temperature",
    min_value=0.0,
    max_value=1.0,
    step=0.1,
    initial_value=0.7
)

@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    try:
        # Initialize session
        await initialize_session()
        
        # Send welcome message
        await cl.Message(
            content="""Welcome to AgenticFleet! 👋

I can help you with:
- Code generation and analysis
- Data processing
- File operations
- And more!

How can I assist you today?""",
            elements=[model_selector, temperature_slider]
        ).send()
        
    except Exception as e:
        logger.error(f"Error in chat start: {str(e)}")
        await cl.Message(
            content="Error initializing chat. Please try again.",
            type="error"
        ).send()

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    try:
        await handle_message(message)
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await cl.Message(
            content="Error processing your message. Please try again.",
            type="error"
        ).send()

@cl.on_settings_update
async def handle_settings_update(settings: dict):
    """Handle settings changes."""
    try:
        # Update model configuration
        if "model" in settings:
            await cl.Message(
                content=f"Switched to {settings['model']}"
            ).send()
            
        # Update temperature
        if "temperature" in settings:
            await cl.Message(
                content=f"Temperature set to {settings['temperature']}"
            ).send()
            
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")

@cl.on_chat_end
async def end():
    """Clean up resources when chat ends."""
    try:
        logger.info("Cleaning up resources...")
        # Add any cleanup code here
        
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")
