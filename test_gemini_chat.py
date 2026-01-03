#!/usr/bin/env python3
"""Test script to call Gemini API via Google AI."""

import os
from dotenv import load_dotenv
from google import genai

# Load .env file
load_dotenv()

# Load API key from .env
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment")

# Initialize the client for Google AI API
client = genai.Client(api_key=api_key)

# Make a chat completion request
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Explain quantum computing in 2 sentences.",
)

print("Response:")
print(response.text)
