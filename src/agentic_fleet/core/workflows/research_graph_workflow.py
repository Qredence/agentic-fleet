import asyncio
import logging

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow, MagenticOneGroupChat
# Assuming OpenAIChatCompletionClient or similar is available and configured
# For now, let's assume a way to get a pre-configured client (e.g., from agentic_fleet.services.client_factory)
# from agentic_fleet.services.client_factory import get_cached_client # Placeholder
from autogen_ext.models.openai import OpenAIChatCompletionClient # Using this directly for now as per AutoGen examples
from autogen_ext.teams.magentic_one import MagenticOne # For the bundled MagenticOne team experience

logger = logging.getLogger(__name__)

# Placeholder for getting a configured model client
# In a real scenario, this would come from AgenticFleet's config
# For this subtask, we might need to mock it or use a default.
# For now, let's follow AutoGen examples and instantiate it directly.
# Ensure OPENAI_API_KEY is set in the environment for this to work if not mocked.
try:
    # This assumes OPENAI_API_KEY is available in the environment for direct instantiation
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini") # Use a small, fast model for testing
except Exception as e:
    logger.error(f"Failed to create OpenAIChatCompletionClient: {e}. Ensure OPENAI_API_KEY is set or mock the client.")
    # Fallback or mock client if necessary for the subtask's environment
    model_client = None # Or a mock object

# Agent 1: MagenticOne team for research and summarization
# MagenticOne bundles its own agents (WebSurfer, Coder, etc.)
# We pass the client to MagenticOne, and it handles its internal agents.
# magentic_one_team = MagenticOne(client=model_client) # MagenticOne itself can be used as a runnable team/agent
# For this subtask, we are using a placeholder orchestrator agent instead of full MagenticOne.
    # UPDATE: Replacing placeholder with actual MagenticOne

if model_client:
    magentic_one_orchestrator_team = MagenticOne(
        client=model_client,
        # Default configuration for MagenticOne.
        # Its internal system messages and agent setup will be used.
        # The MagenticOne class is designed to manage its own team (MagenticOneGroupChat).
    )
    # The node for the graph should be the MagenticOneGroupChat instance,
    # which is typically available as `chat_manager` on the MagenticOne instance.
    actual_orchestrator_node = magentic_one_orchestrator_team.chat_manager
    # We need to ensure this node has a `name` attribute for logging and comparison.
    # MagenticOneGroupChat should have a name, often based on its agents.
    # If not, we might need to assign one or use a default.
    # For now, let's assume `actual_orchestrator_node.name` is valid.
    # If MagenticOneGroupChat's default name is too generic, we might need to customize it.
    # Let's give it a more specific name if possible, or use its default.
    # Default name for MagenticOneGroupChat might be "MagenticOneChat".
    # To be safe, let's try to set a name if it's not set, or use a fixed one for logic.
    # However, BaseAgent instances (which GroupChat inherits from) should have a .name attribute.
else:
    magentic_one_orchestrator_team = None
    actual_orchestrator_node = None
    logger.error("MagenticOne orchestrator could not be initialized as model_client is None.")

# Agent 2: AssistantAgent for writing a blog post based on the summary
blog_writer_agent = AssistantAgent(
    name="Blog_Writer",
    model_client=model_client, # Assuming model_client is available and initialized
    system_message="You are a blog post writer. You will receive a summary of a research topic. Your task is to write a short, engaging blog post based on this summary."
)

builder = DiGraphBuilder()

if actual_orchestrator_node:
    builder.add_node(actual_orchestrator_node)
    builder.add_node(blog_writer_agent)
    builder.add_edge(actual_orchestrator_node, blog_writer_agent)
else:
    logger.error("Cannot build graph: MagenticOne orchestrator node is not available.")

async def run_research_graph(task_description: str) -> dict[str, str | None]:
    if model_client is None or actual_orchestrator_node is None:
        error_msg = "Model client not initialized."
        if actual_orchestrator_node is None:
            error_msg = "MagenticOne orchestrator node not initialized."
        logger.error(error_msg)
        return {"error": error_msg, "research_summary": None, "blog_post": None}

    graph = builder.build()
    graph_flow_team = GraphFlow(
        participants=builder.get_participants(), # Should include actual_orchestrator_node and blog_writer_agent
        graph=graph
    )

    research_summary = None
    blog_post = None

    logger.info(f"Starting graph execution for task: {task_description} with orchestrator {actual_orchestrator_node.name if actual_orchestrator_node else 'N/A'}")

    async for event_data in graph_flow_team.run_stream(task=task_description):
        source_agent_name = None
        content = None

        if isinstance(event_data, dict):
            source_agent_name = event_data.get("source")
            content = event_data.get("content")
        elif hasattr(event_data, 'message') and event_data.message:
             source_agent_name = event_data.message.source
             content = event_data.message.content
        elif hasattr(event_data, 'messages') and event_data.messages:
            for msg in event_data.messages:
                logger.info(f"Processing message from TaskResult: Source='{msg.source}', Content='{msg.content[:100]}...'")
                # Check if actual_orchestrator_node is not None before accessing its name
                if actual_orchestrator_node and msg.source == actual_orchestrator_node.name and msg.content:
                    # MagenticOne's final output is taken as the summary.
                    research_summary = msg.content
                    logger.info(f"Captured research summary from {actual_orchestrator_node.name} (TaskResult): {research_summary[:100]}...")
                elif msg.source == blog_writer_agent.name and msg.content:
                    blog_post = msg.content
                    logger.info(f"Captured blog post from TaskResult: {blog_post[:100]}...")
            # No early break here, process all messages in TaskResult
        else:
            logger.info(f"Graph Event (unparsed structure or different type): {type(event_data)} - {str(event_data)[:200]}")

        if source_agent_name and content:
             logger.info(f"Message from {source_agent_name}: {str(content)[:200]}...")
             # Check if actual_orchestrator_node is not None before accessing its name
             if actual_orchestrator_node and source_agent_name == actual_orchestrator_node.name:
                 # MagenticOne's output is taken as the summary.
                 # Unlike the placeholder, it won't have "RESEARCH SUMMARY:" prefix unless specifically engineered.
                 research_summary = str(content)
                 logger.info(f"Captured research summary from {actual_orchestrator_node.name}: {research_summary[:100]}...")
             elif source_agent_name == blog_writer_agent.name:
                 blog_post = str(content)
                 logger.info(f"Captured blog post: {blog_post[:100]}...")

    final_result = {
        "task_description": task_description,
        "research_summary": research_summary,
        "blog_post": blog_post
    }
    summary_len = len(research_summary) if research_summary else 0
    post_len = len(blog_post) if blog_post else 0
    logger.info(f"Graph execution finished. Result: {{'task': '{task_description}', 'summary_len': {summary_len}, 'post_len': {post_len}}}")
    return final_result

# Example of how to run it (for testing within the module if needed)
async def main():
    logger.info("Starting main function for research_graph_workflow.")
    if not model_client:
        logger.error("Cannot run main: model_client is not initialized. Set OPENAI_API_KEY.")
        return
    if not actual_orchestrator_node:
        logger.error("Cannot run main: actual_orchestrator_node is not initialized.")
        return

    result = await run_research_graph("Research the benefits of renewable energy and its impact on climate change.")
    logger.info("--- Research Graph Execution Complete ---")
    logger.info(f"Task: {result.get('task_description')}")
    logger.info(f"Research Summary (from {actual_orchestrator_node.name if actual_orchestrator_node else 'N/A'}):\n{result.get('research_summary')}")
    logger.info(f"Final Blog Post:\n{result.get('blog_post')}")

if __name__ == "__main__":
    # Basic logging setup for standalone execution
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # This requires an event loop.
    # To run this directly for testing (requires OPENAI_API_KEY to be set and Playwright installed)
    # try:
    #     asyncio.run(main())
    # except RuntimeError as e:
    #     if "cannot be called from a running event loop" in str(e):
    #         logger.info("main() was called from within an existing event loop. This is fine if run by FastAPI/Uvicorn.")
    #     else:
    #         raise
    pass
