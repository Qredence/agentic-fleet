"""Build Agent using Microsoft Agent Framework in Python
# Run this python script
> pip install agent-framework
> python <this-script-path>.py
"""

import asyncio

from agent_framework import ChatAgent, MCPStdioTool, ToolProtocol
from agent_framework_azure_ai import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential

# Azure AI Foundry Agent Configuration
ENDPOINT = "https://qredence-foundry.services.ai.azure.com/api/projects/agentic-fleet"
MODEL_DEPLOYMENT_NAME = "gpt-5"

AGENT_NAME = "mcp-agent"
AGENT_INSTRUCTIONS = 'You are a web exploration assistant (BrowserAgent) that can navigate to websites, take screenshots, and provide summaries of web content. You\'ll help users explore the web by visiting sites and extracting useful information.\n\n  You are a researcher agent. Your role is to gather information from the web.\n  You have access to a web search tool.\n  Based on the user\'s request and the conversation history, you must perform a web search and return the results.\n\n  Conversation History:\n  {memory}\n\n# Instruction\nYou may receive instructions either from a user or from another agent (such as an orchestrator). Always treat the active instruction as your current objective, regardless of its origin. Your goal is to gather the required information from the web as directed.\n\n# Steps\n1. Analyze the instruction and determine the main objective(s).\n2. Identify if completing the objective may require visiting multiple web pages.\n3. Develop a plan for navigating through the necessary websites to fulfill the request.\n4. Carry out your plan, navigating across as many pages or performing as many browsing steps as required to fully satisfy the instruction.\n5. At each step, reason about what information you have acquired and what is still required—think carefully, step by step, before proceeding or concluding your actions.\n6. When you believe the task is complete, summarize your reasoning and provide the results as specified in the Output Format.\n- Think carefully step by step before concluding each action.\n\n# Tool Use Guidelines\n- Only terminate your turn when you are sure that the problem is fully solved and the objective is met.\n- If additional information or navigation is needed, continue using your browser tools until you\'ve gathered all that is required.\n- If unsure about any details needed for the request, use your browser tools to find out—do not guess or fabricate information.\n- For complex tasks, plan extensively before each tool usage and reflect on the outcome of each previous action.\n\n# Output Format\nProvide your output in XML format with two sections: a reasoning section and a result section.\nStructure:\n<thinking>\n[Step-by-step reasoning, plans, analysis of why each navigation or tool use is needed.]\n</thinking>\n<result>\n[Final answer, summary, or required information gathered from the web.]\n</result>\n\nExample:\n<thinking>\nAnalyzed the instruction to find the most recent academic articles on climate change. Planned to search Google Scholar and navigate through the first three result pages to find relevant papers. After reviewing abstracts and publication dates, selected the most up-to-date papers.\n</thinking>\n<result>\n1. "Recent Advances in Climate Change Science" - Nature, 2023.\n2. "Impacts of Global Warming" - Science, 2023.\n</result>'  # noqa: E501

# User inputs for the conversation
USER_INPUTS = [
    "use  browse internet to find any relevant link related to Qredence.\nMake sure to find the most relevant ones. Do multiturn if necessary",  # noqa: E501
]


def create_mcp_tools() -> list[ToolProtocol]:
    return [
        MCPStdioTool(
            name="aitk-playwright-example".replace("-", "_"),
            description="MCP server for aitk-playwright-example",
            command="npx",
            args=[
                "-y",
                "@playwright/mcp@latest",
            ],
        ),
    ]


async def main() -> None:
    async with (
        DefaultAzureCredential() as credential,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                project_endpoint=ENDPOINT,
                model_deployment_name=MODEL_DEPLOYMENT_NAME,
                async_credential=credential,
                agent_name=AGENT_NAME,
                agent_id=None,  # Since no Agent ID is provided, the agent will be automatically created and deleted after getting response  # noqa: E501
            ),
            instructions=AGENT_INSTRUCTIONS,
            tools=create_mcp_tools(),
        ) as agent,
    ):
        # Create a new thread that will be reused
        thread = agent.get_new_thread()

        # Process user messages
        for user_input in USER_INPUTS:
            print(f"\n# User: '{user_input}'")
            async for chunk in agent.run_stream([user_input], thread=thread):
                if chunk.text:
                    print(chunk.text, end="")
                elif (
                    chunk.raw_representation
                    and not isinstance(chunk.raw_representation, list)
                    and chunk.raw_representation.raw_representation
                    and hasattr(chunk.raw_representation.raw_representation, "status")
                    and hasattr(chunk.raw_representation.raw_representation, "type")
                    and chunk.raw_representation.raw_representation.status == "completed"
                    and hasattr(chunk.raw_representation.raw_representation, "step_details")
                    and hasattr(
                        chunk.raw_representation.raw_representation.step_details,
                        "tool_calls",
                    )
                ):
                    print("")
                    print(
                        "Tool calls: ",
                        chunk.raw_representation.raw_representation.step_details.tool_calls,
                    )
            print("")

        print("\n--- All tasks completed successfully ---")

    # Give additional time for all async cleanup to complete
    await asyncio.sleep(1.0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("Program finished.")
