# Mem0 Integration

This document explains how `mem0` is integrated into the AgenticFleet project to provide a persistent memory layer for the agents.

## Overview

`mem0` is an open-source memory layer for AI agents. It allows agents to remember past conversations and user preferences, enabling more personalized and context-aware interactions. In AgenticFleet, `mem0` is used to provide a shared memory for all the agents in the workflow.

## Architecture

The `mem0` integration is based on a `Mem0ContextProvider` class, which is responsible for interacting with the `mem0ai` library. This class is located in the `context_provider/mem0_context_provider.py` file.

The `Mem0ContextProvider` is configured to use Azure AI Search as a vector store for the memories. This allows the memories to be persisted across sessions and queried efficiently.

## Configuration

The `mem0` integration requires the following environment variables to be set in the `.env` file:

- `AZURE_AI_PROJECT_ENDPOINT`: The endpoint of your Azure AI project.
- `OPENAI_API_KEY`: Your OpenAI API key.
- `AZURE_AI_SEARCH_ENDPOINT`: The endpoint of your Azure AI Search service.
- `AZURE_AI_SEARCH_KEY`: The API key for your Azure AI Search service.
- `AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME`: The name of your deployed chat completion model in Azure OpenAI.
- `AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME`: The name of your deployed embedding model in Azure OpenAI.

## Usage

The `Mem0ContextProvider` is instantiated in the `workflows/magentic_workflow.py` file and passed to each agent during its creation. The agents' system prompts have been updated to include a `{memory}` placeholder, which is replaced with the conversation history from the context provider.

The orchestration loop in the `run_workflow` function has been updated to use the context provider to manage the conversation history. The user's input and each agent's response are added to the memory, and the memory is passed to the agents in each turn.
