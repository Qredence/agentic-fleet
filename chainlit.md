---
chat_profiles:
  - name: MagenticFleet
    markdown_description: |
      **Standard AgenticFleet Profile** 🚀

      Engage with the core multi-agent system for adaptive reasoning and task automation. Uses the default Azure OpenAI model configured for general tasks.
    icon: "public/icons/rocket.svg" # Example icon path
    model_settings:
      model_name: "gpt-4o-mini-2024-07-18" # Default model

  - name: MCP Focus
    markdown_description: |
      **MCP Interaction Profile** 🔬

      Focus on interacting with connected Model Context Protocol (MCP) servers and tools. Ideal for tasks requiring external tool usage or specific data access via MCP.
    icon: "public/icons/microscope.svg" # Example icon path
    model_settings:
      model_name: "gpt-4o-mini-2024-07-18" # Can be same or different model
    # env: # Placeholder for potential MCP-specific environment variables
    #   MCP_SERVER_URL: "http://localhost:8001"

# Custom UI configuration
features:
  # Enable custom JS loading (syntax might vary based on Chainlit version)
  enable_custom_js: true

custom_js: /public/custom_renderer.js # Path relative to Chainlit server root

---

# Welcome to AgenticFleet! 🚀🤖

Hello, Developer! 👋 Welcome to AgenticFleet – a cutting-edge multi-agent system designed for adaptive AI reasoning and automation. Dive in to explore a platform where powerful AI agents, seamless task management, and intuitive interfaces come together to help you build intelligent applications.

Select a **Chat Profile** above to get started!

## Get Started

- **Documentation:** Learn how to harness the full potential of AgenticFleet in our comprehensive [README](README.md) and documentation.
- **Discord Community:** Join our friendly community on [Discord](https://discord.gg/ebgy7gtZHK) to share ideas, get support, and connect with fellow developers.
- **Twitter:** Stay updated with the latest news and insights by following us on [Twitter](https://x.com/agenticfleet).

Edit this file to tailor the welcome screen to your needs. Let’s innovate with AgenticFleet and redefine intelligent automation together!

Happy coding! 💻😊
