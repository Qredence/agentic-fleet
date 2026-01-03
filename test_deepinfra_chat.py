#!/usr/bin/env python3
"""Test script to call DeepInfra models via LiteLLM proxy."""

import os
from dotenv import load_dotenv
import openai

# Load .env file
load_dotenv()

# Get LiteLLM proxy settings
proxy_url = os.environ.get("LITELLM_PROXY_URL", "http://localhost:6000")
service_key = os.environ.get("LITELLM_SERVICE_KEY")
if not service_key:
    raise ValueError("LITELLM_SERVICE_KEY not found in environment")

# Initialize OpenAI client pointing to LiteLLM proxy
client = openai.OpenAI(base_url=proxy_url, api_key=service_key)

# Test deepseek-v3.2
print("=" * 50)
print("Testing: deepinfra/deepseek-ai/deepseek-v3.2")
print("=" * 50)
try:
    response = client.chat.completions.create(
        model="deepseek-v3.2",
        messages=[{"role": "user", "content": "Explain quantum computing in 2 sentences."}],
        max_tokens=200,
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")

# Test nemotron-30b (DeepInfra Nvidia Nemotron)
print("\n" + "=" * 50)
print("Testing: deepinfra/nvidia/Nemotron-3-Nano-30B-A3B")
print("=" * 50)
try:
    response = client.chat.completions.create(
        model="nemotron-30b",
        messages=[{"role": "user", "content": "Explain quantum computing in 2 sentences."}],
        max_tokens=200,
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 50)
print("Testing: google/gemini-3-flash-preview (Google AI API)")
print("=" * 50)
try:
    response = client.chat.completions.create(
        model="gemini-3-flash-preview",
        messages=[{"role": "user", "content": "Explain quantum computing in 2 sentences."}],
        max_tokens=200,
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
