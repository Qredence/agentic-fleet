# AgenticFleet Roadmap

This roadmap outlines the planned development and future direction of AgenticFleet. The items are categorized by priority, reflecting their importance and estimated timeline.

## High Priority

These items are considered essential for the core functionality and usability of AgenticFleet.

*   **Unified REST API with FastAPI:** Establish a unified REST API using FastAPI to serve as the backend for AgenticFleet. This API will encompass existing Chainlit functionalities and provide a foundation for future feature extensions.
*   **Mount Chainlit App within FastAPI:** Integrate the existing Chainlit application as a component within the new FastAPI backend. This allows leveraging Chainlit's UI and features while transitioning to the unified API.
*   **Develop React Frontend (Figma-based):** Create a new React frontend for AgenticFleet, based on the Chainlit frontend's design but developed using a Figma-to-React workflow. This frontend should be production-ready and highly customizable.

## Medium Priority

These items enhance AgenticFleet's capabilities and integrations.

*   **Natively Support MCP Servers:** Integrate native support for Model Context Protocol (MCP) servers within AgenticFleet. This allows users to easily extend AgenticFleet's capabilities by connecting to external services.
*   **Integrate Composio FleetWorker:** Integrate Composio FleetWorker to enable communication and data exchange between AgenticFleet and other Composio applications.

## Low Priority

These items represent longer-term goals and improvements.

*   **Add PromptWizard Features:** Integrate specific features from PromptWizard into AgenticFleet.
*   **Core Principles Documentation:** Create documentation outlining AgenticFleet's core principles and their benefits.
*   **Early Access Program:** Define the scope and logistics of an early access program for pre-release versions of AgenticFleet.
*   **Figma File Synchronization:** Establish a process for keeping the Figma file and React components synchronized.
*   **Cloud/Local Deployment:** Define requirements and architecture for both cloud and on-premise (local-first) deployments of AgenticFleet.
