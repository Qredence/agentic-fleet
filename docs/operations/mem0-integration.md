# Mem0 Integration

This document explains how `mem0` is integrated into the AgenticFleet project to provide a persistent memory layer for the agents.

## Overview

`mem0` is an open-source memory layer for AI agents. It allows agents to remember past
conversations and user preferences, enabling more personalized and context-aware
interactions. In AgenticFleet, `mem0` is used to provide a shared memory for all the agents
in the workflow.

## Architecture

The `mem0` integration is based on a `Mem0ContextProvider` class, which is responsible for interacting with the `mem0ai` library. This class is located in `src/agenticfleet/context/mem0_provider.py`.

The `Mem0ContextProvider` configures Mem0 to use the standard OpenAI API for both language
model responses and embeddings. A lightweight embedded Qdrant store (managed by Mem0) keeps
vector data on disk, so no external Azure dependencies are required.

## Configuration

The `mem0` integration requires the following environment variables to be set in the `.env`
file:

- `OPENAI_API_KEY`: Your OpenAI API key (required).
- `OPENAI_MODEL`: Optional override for the chat model used when extracting and updating
  memories (defaults to `gpt-4o-mini`).
- `OPENAI_EMBEDDING_MODEL`: Optional override for the embedding model used to store and
  retrieve memories (defaults to `text-embedding-3-small`).
- `MEM0_HISTORY_DB_PATH`: Optional path to the on-disk history database (defaults to
  `var/memories/history.db`).

## Usage

The `Mem0ContextProvider` is instantiated via the settings module and can be injected where
long-term context is needed. Agent prompts include a `{memory}` placeholder, which is
replaced with the retrieved context before the agent speaks. The orchestration loop adds
relevant user inputs and agent outputs back into Mem0 so future runs can recall them.

Checkpointing (see `operations/checkpointing.md`) complements Mem0 by preserving the
short-term Magentic ledger, while Mem0 retains cross-run knowledge about the user and the
tasks they have completed.
