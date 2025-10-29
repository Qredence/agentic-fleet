"""
Memory CLI - Command-line interface for AgenticFleet Memory System.

Provides interactive commands for testing, managing, and exploring
the memory system using OpenMemory MCP server integration.
"""

import asyncio
import logging
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from agenticfleet.memory import (
    MemoryContextProvider,
    MemoryManager,
    MemoryPriority,
    MemoryType,
    memory_config,
    memory_policy,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CLI app
memory_app = typer.Typer(
    name="memory",
    help="AgenticFleet Memory System CLI - Manage and explore agent memories",
    no_args_is_help=True,
)

# Console for rich output
console = Console()

# Global memory manager
memory_manager: MemoryManager | None = None
context_provider: MemoryContextProvider | None = None


async def initialize_memory_system() -> tuple[MemoryManager, MemoryContextProvider]:
    """Initialize the memory system."""
    global memory_manager, context_provider

    if memory_manager is None or context_provider is None:
        # Initialize memory manager (without MCP client for CLI)
        memory_manager = MemoryManager()
        await memory_manager.initialize()

        # Initialize context provider
        context_provider = MemoryContextProvider(memory_manager)

    return memory_manager, context_provider


@memory_app.command()
def status() -> None:
    """Show memory system status and configuration."""
    console.print("[bold blue]AgenticFleet Memory System Status[/bold blue]")
    console.print()

    # Configuration
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("OpenMemory Enabled", str(memory_config.openmemory_enabled))
    config_table.add_row("Cache TTL (minutes)", str(memory_config.memory_cache_ttl_minutes))
    config_table.add_row("Max Memories per Context", str(memory_config.max_memories_per_context))
    config_table.add_row("Enable Learning Memories", str(memory_config.enable_learning_memories))
    config_table.add_row("Enable Pattern Memories", str(memory_config.enable_pattern_memories))
    config_table.add_row("Enable Error Memories", str(memory_config.enable_error_memories))

    console.print(config_table)
    console.print()

    # Policies
    policy_table = Table(title="Policies")
    policy_table.add_column("Policy", style="cyan")
    policy_table.add_column("Value", style="green")

    policy_table.add_row("Auto-store Conversations", str(memory_policy.auto_store_conversations))
    policy_table.add_row("Auto-store Errors", str(memory_policy.auto_store_errors))
    policy_table.add_row("Auto-store Patterns", str(memory_policy.auto_store_patterns))
    policy_table.add_row(
        "Require Approval for Patterns", str(memory_policy.require_user_approval_patterns)
    )

    console.print(policy_table)


@memory_app.command()
def store(
    title: str = typer.Argument(..., help="Memory title"),
    content: str = typer.Argument(..., help="Memory content"),
    memory_type: str = typer.Option("learning", "--type", "-t", help="Memory type"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Memory priority"),
    keywords: str | None = typer.Option(None, "--keywords", "-k", help="Comma-separated keywords"),
) -> None:
    """Store a new memory."""

    async def _store() -> None:
        manager, _ = await initialize_memory_system()

        # Convert string parameters
        try:
            mem_type = MemoryType(memory_type.lower())
        except ValueError as err:
            console.print(f"[red]Invalid memory type: {memory_type}[/red]")
            console.print(f"Available types: {[t.value for t in MemoryType]}")
            raise typer.Exit(1) from err

        try:
            mem_priority = MemoryPriority(priority.lower())
        except ValueError as err:
            console.print(f"[red]Invalid priority: {priority}[/red]")
            console.print(f"Available priorities: {[p.value for p in MemoryPriority]}")
            raise typer.Exit(1) from err

        context_keywords = []
        if keywords:
            context_keywords = [k.strip() for k in keywords.split(",")]

        # Store the memory
        memory_id = await manager.store_memory(
            title=title,
            content=content,
            memory_type=mem_type,
            priority=mem_priority,
            context_keywords=context_keywords,
        )

        console.print("[green]✓[/green] Memory stored successfully!")
        console.print(f"  ID: {memory_id}")
        console.print(f"  Type: {mem_type.value}")
        console.print(f"  Priority: {mem_priority.value}")
        console.print(f"  Keywords: {', '.join(context_keywords) if context_keywords else 'None'}")

    asyncio.run(_store())


@memory_app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    memory_type: str | None = typer.Option(None, "--type", "-t", help="Filter by memory type"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of results"),
    conversation_id: str | None = typer.Option(
        None, "--conversation", "-c", help="Filter by conversation ID"
    ),
) -> None:
    """Search for memories."""

    async def _search() -> None:
        manager, _ = await initialize_memory_system()

        # Build query
        memory_types = []
        if memory_type:
            try:
                memory_types = [MemoryType(memory_type.lower())]
            except ValueError as err:
                console.print(f"[red]Invalid memory type: {memory_type}[/red]")
                console.print(f"Available types: {[t.value for t in MemoryType]}")
                raise typer.Exit(1) from err

        # Search memories
        results = await manager.retrieve_memories(
            query=query,
            memory_types=memory_types,
            limit=limit,
            conversation_id=conversation_id,
        )

        # Display results
        console.print("[bold blue]Search Results[/bold blue]")
        console.print(f"Query: '{query}'")
        console.print(f"Found: {results.total_found} memories (showing {len(results.memories)})")
        console.print(f"Query time: {results.query_time_ms:.2f}ms")
        console.print()

        if not results.memories:
            console.print("[yellow]No memories found matching your query.[/yellow]")
            return

        # Results table
        results_table = Table()
        results_table.add_column("ID", style="cyan", width=10)
        results_table.add_column("Type", style="green", width=12)
        results_table.add_column("Priority", style="yellow", width=10)
        results_table.add_column("Title", style="white", width=30)
        results_table.add_column("Content Preview", style="white", width=50)
        results_table.add_column("Created", style="magenta", width=12)

        for memory in results.memories:
            content_preview = (
                memory.content[:47] + "..." if len(memory.content) > 50 else memory.content
            )
            created_str = memory.metadata.created_at.strftime("%Y-%m-%d")

            results_table.add_row(
                memory.id[:8],
                memory.type.value,
                memory.priority.value,
                memory.title[:28] + "..." if len(memory.title) > 30 else memory.title,
                content_preview,
                created_str,
            )

        console.print(results_table)

    asyncio.run(_search())


@memory_app.command()
def show(
    memory_id: str = typer.Argument(..., help="Memory ID to display"),
) -> None:
    """Show detailed information about a specific memory."""

    async def _show() -> None:
        manager, _ = await initialize_memory_system()

        # Search for the specific memory
        results = await manager.retrieve_memories(query=memory_id, limit=1)

        if not results.memories:
            console.print(f"[red]Memory not found: {memory_id}[/red]")
            return

        memory = results.memories[0]

        # Display memory details
        console.print("[bold blue]Memory Details[/bold blue]")
        console.print()

        # Basic info
        console.print(f"[cyan]ID:[/cyan] {memory.id}")
        console.print(f"[cyan]Type:[/cyan] {memory.type.value}")
        console.print(f"[cyan]Priority:[/cyan] {memory.priority.value}")
        console.print(f"[cyan]Title:[/cyan] {memory.title}")
        console.print()

        # Content
        console.print("[cyan]Content:[/cyan]")
        console.print(memory.content)
        console.print()

        # Metadata
        console.print("[cyan]Metadata:[/cyan]")
        console.print(f"  Created: {memory.metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if memory.metadata.updated_at:
            console.print(f"  Updated: {memory.metadata.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"  Access Count: {memory.metadata.access_count}")
        if memory.metadata.last_accessed:
            console.print(
                f"  Last Accessed: {memory.metadata.last_accessed.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        console.print(f"  Source Agent: {memory.metadata.source_agent or 'None'}")
        console.print(f"  Conversation ID: {memory.metadata.conversation_id or 'None'}")
        console.print(f"  Relevance Score: {memory.metadata.relevance_score:.2f}")

        # Keywords
        if memory.context_keywords:
            console.print(f"[cyan]Keywords:[/cyan] {', '.join(memory.context_keywords)}")

        # Related memories
        if memory.related_memories:
            console.print(f"[cyan]Related Memories:[/cyan] {', '.join(memory.related_memories)}")

    asyncio.run(_show())


@memory_app.command()
def stats() -> None:
    """Show memory system statistics."""

    async def _stats() -> None:
        manager, _ = await initialize_memory_system()

        # Get statistics
        stats = await manager.get_memory_stats()

        console.print("[bold blue]Memory System Statistics[/bold blue]")
        console.print()

        # Overview
        console.print(f"[cyan]Total Memories:[/cyan] {stats.total_memories}")
        console.print(f"[cyan]Storage Usage:[/cyan] {stats.storage_usage_mb:.2f} MB")
        console.print(f"[cyan]Average Access Count:[/cyan] {stats.average_access_count:.2f}")
        console.print()

        # Memories by type
        console.print("[bold]Memories by Type:[/bold]")
        type_table = Table()
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", style="green")

        for mem_type, count in stats.memories_by_type.items():
            type_table.add_row(mem_type.value, str(count))

        console.print(type_table)
        console.print()

        # Memories by priority
        console.print("[bold]Memories by Priority:[/bold]")
        priority_table = Table()
        priority_table.add_column("Priority", style="cyan")
        priority_table.add_column("Count", style="green")

        for priority, count in stats.memories_by_priority.items():
            priority_table.add_row(priority.value, str(count))

        console.print(priority_table)
        console.print()

        # Most accessed memories
        if stats.most_accessed_memories:
            console.print("[bold]Most Accessed Memories:[/bold]")
            for i, memory_id in enumerate(stats.most_accessed_memories[:5], 1):
                console.print(f"  {i}. {memory_id}")

        console.print()

        # Recently created memories
        if stats.recently_created:
            console.print("[bold]Recently Created Memories (last 24h):[/bold]")
            for i, memory_id in enumerate(stats.recently_created[:5], 1):
                console.print(f"  {i}. {memory_id}")

    asyncio.run(_stats())


@memory_app.command()
def demo() -> None:
    """Run a demo of the memory system capabilities."""

    async def _demo() -> None:
        console.print("[bold blue]AgenticFleet Memory System Demo[/bold blue]")
        console.print()

        manager, provider = await initialize_memory_system()

        # Demo workflow
        demo_workflow_id = f"demo_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        console.print("[cyan]Step 1: Storing learning memories...[/cyan]")

        # Store some learning memories
        learning_1 = await manager.store_memory(
            title="Async Best Practices",
            content="Always use the await keyword when calling async functions in Python. "
            "This ensures the coroutine is properly executed and its result is obtained.",
            memory_type=MemoryType.LEARNING,
            priority=MemoryPriority.HIGH,
            context_keywords=["python", "async", "await", "best-practices"],
        )

        console.print(f"  ✓ Stored: {learning_1}")

        learning_2 = await manager.store_memory(
            title="Error Handling Patterns",
            content="Wrap async operations in try-catch blocks to handle exceptions gracefully. "
            "Common async errors include RuntimeError and TimeoutError.",
            memory_type=MemoryType.ERROR,
            priority=MemoryPriority.HIGH,
            context_keywords=["error", "exception", "async", "try-catch"],
        )

        console.print(f"  ✓ Stored: {learning_2}")
        console.print()

        # Store pattern memory
        console.print("[cyan]Step 2: Storing pattern memory...[/cyan]")
        pattern_1 = await manager.store_memory(
            title="Async Context Manager Pattern",
            content="Use 'async with' statements for managing async resources like "
            "database connections or file handles. This ensures proper cleanup.",
            memory_type=MemoryType.PATTERN,
            priority=MemoryPriority.MEDIUM,
            context_keywords=["pattern", "async-with", "resource-management"],
        )

        console.print(f"  ✓ Stored: {pattern_1}")
        console.print()

        # Store conversation memory
        console.print("[cyan]Step 3: Storing conversation memory...[/cyan]")
        conversation_1 = await provider.store_conversation_memory(
            conversation_id=demo_workflow_id,
            agent_name="demo_agent",
            message="How do I handle multiple async operations?",
            response="Use asyncio.gather() to run multiple async operations concurrently, "
            "or process them sequentially with await statements.",
        )

        console.print(f"  ✓ Stored: {conversation_1}")
        console.print()

        # Search and retrieve memories
        console.print("[cyan]Step 4: Searching for relevant memories...[/cyan]")
        search_results = await manager.retrieve_memories(
            query="async programming best practices error handling",
            memory_types=[MemoryType.LEARNING, MemoryType.ERROR, MemoryType.PATTERN],
            limit=5,
        )

        console.print(f"  Found {search_results.total_found} relevant memories:")

        for i, memory in enumerate(search_results.memories, 1):
            console.print(f"    {i}. [{memory.type.value.upper()}] {memory.title}")

        console.print()

        # Get context for an agent
        console.print("[cyan]Step 5: Getting context for an agent...[/cyan]")
        context = await provider.get_context(
            conversation_id=demo_workflow_id,
            agent_name="demo_agent",
            current_message="I need help with async error handling",
        )

        console.print(f"  Provided {context['memory_count']} memories to agent")
        console.print(f"  Query time: {context['query_time_ms']:.2f}ms")

        if context["memories"]:
            console.print("  Relevant memories:")
            for memory in context["memories"]:
                console.print(f"    - [{memory['type']}] {memory['title']}")

        console.print()

        # Get final statistics
        console.print("[cyan]Step 6: Final statistics...[/cyan]")
        final_stats = await manager.get_memory_stats()

        console.print(f"  Total memories in system: {final_stats.total_memories}")
        console.print(f"  Storage used: {final_stats.storage_usage_mb:.2f} MB")
        console.print(f"  Types stored: {list(final_stats.memories_by_type.keys())}")

        console.print()
        console.print("[bold green]✓ Demo completed successfully![/bold green]")
        console.print()
        console.print(
            "The memory system is now ready for integration with your AgenticFleet workflows!"
        )

    asyncio.run(_demo())


@memory_app.command()
def test() -> None:
    """Run memory system tests."""
    console.print("[bold blue]Running Memory System Tests[/bold blue]")
    console.print()

    import subprocess
    import sys

    try:
        # Run the memory system tests
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_memory_system.py", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=".",
        )

        if result.returncode == 0:
            console.print("[bold green]✓ All tests passed![/bold green]")
            console.print()
            console.print(result.stdout)
        else:
            console.print("[bold red]✗ Some tests failed![/bold red]")
            console.print()
            console.print(result.stdout)
            console.print(result.stderr)

    except Exception as e:
        console.print(f"[red]Error running tests: {e}[/red]")


if __name__ == "__main__":
    memory_app()
