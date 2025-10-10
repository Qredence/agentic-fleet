#!/usr/bin/env python3
"""
AgenticFleet - Multi-Agent System with Microsoft Agent Framework
Phase 1: Core Foundation & Multi-Agent Validation

A sophisticated multi-agent system that coordinates specialized AI agents
to solve complex tasks through dynamic delegation and collaboration.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                    User Interface                        │
    │                    (REPL / CLI)                         │
    └────────────────────┬────────────────────────────────────┘
                         │
                         ▼
    ┌─────────────────────────────────────────────────────────┐
    │              Magentic Workflow Manager                   │
    │         (Coordination & State Management)               │
    └────────────────────┬────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
    ┌───────────────┐         ┌────────────────┐
    │ Orchestrator  │◄────────┤  Specialized   │
    │    Agent      │         │    Agents      │
    └───────┬───────┘         └────────┬───────┘
            │                          │
            │    ┌─────────────────────┼──────────────────┐
            │    │                     │                  │
            ▼    ▼                     ▼                  ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  Researcher  │  │    Coder     │  │   Analyst    │
    │  (Web Search)│  │ (Code Exec)  │  │ (Data Anal.) │
    └──────────────┘  └──────────────┘  └──────────────┘

Features:
- Dynamic task decomposition and agent delegation
- Multi-agent coordination with state management
- Event-driven architecture for real-time monitoring
- Structured tool responses with Pydantic models
- Configurable execution limits and safety controls

Author: Qredence
Version: 0.5.0 (Phase 1)
"""

import asyncio
import sys

from config.settings import settings
from workflows.magentic_workflow import create_magentic_workflow


async def main():
    """
    Main application entry point.

    This function:
    1. Validates configuration and environment setup
    2. Creates the multi-agent workflow
    3. Displays usage information and capabilities
    4. Runs an interactive REPL loop for user interaction
    5. Handles graceful shutdown and error recovery

    The REPL (Read-Eval-Print Loop) allows continuous interaction with
    the multi-agent system until the user exits.
    """
    # Display startup banner
    print("🚀 Starting AgenticFleet - Phase 1")
    print("📦 Powered by Microsoft Agent Framework")
    print("🔗 Using OpenAI with structured responses")

    # Validate configuration before proceeding
    # This ensures all required environment variables are set
    try:
        if not settings.openai_api_key:
            print("\n❌ ERROR: OPENAI_API_KEY environment variable is required")
            print("   Please copy .env.example to .env and add your OpenAI API key")
            print("   Example: OPENAI_API_KEY=sk-your-key-here")
            sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("   Please check your .env file and configuration")
        sys.exit(1)

    # Create the multi-agent workflow
    print("\n🔧 Initializing multi-agent workflow...")
    try:
        workflow = create_magentic_workflow()
        print("✅ Workflow created successfully!")
        print("   🤖 Agents: Orchestrator, Researcher, Coder, Analyst")
        print("   🛠️  Tools: Web search, Code interpreter, Data analysis")
    except Exception as e:
        print(f"\n❌ Failed to create workflow: {e}")
        print("   This might be due to:")
        print("   - Missing or invalid configuration files")
        print("   - Agent initialization errors")
        print("   - Tool setup issues")
        sys.exit(1)

    # Display usage information and capabilities
    print("\n" + "=" * 70)
    print("🤖 AGENTICFLEET READY FOR TASK EXECUTION")
    print("=" * 70)
    print("\n💡 Example tasks to try:")
    print("  • 'Research Python machine learning libraries and write example code'")
    print("  • 'Analyze e-commerce trends and suggest visualizations'")
    print("  • 'Help me understand web development best practices with code'")
    print("  • 'Write a Python function to process CSV data and explain it'")
    print("\n🛠️  The system will automatically coordinate between specialists:")
    print("  - Orchestrator: Plans and delegates tasks")
    print("  - Researcher: Gathers information and context")
    print("  - Coder: Writes and tests code")
    print("  - Analyst: Provides insights and visualization suggestions")
    print("\n⌨️  Commands:")
    print("  - Type your task and press Enter to execute")
    print("  - Type 'quit', 'exit', or 'q' to exit")
    print("  - Press Ctrl+C to interrupt")
    print()

    # Main interaction loop (REPL)
    # Continuously accepts user input and processes tasks
    while True:
        try:
            # Get user input
            user_input = input("🎯 Your task: ").strip()

            # Handle exit commands
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Thank you for using AgenticFleet!")
                break

            # Skip empty input
            if not user_input:
                continue

            # Process the task through the workflow
            print(f"\n🔄 Processing: '{user_input}'")
            print("-" * 50)

            # Execute workflow with the user's task
            # The workflow will coordinate agents and return the final result
            try:
                result = await workflow.run(user_input)

                # Display completion status
                print("\n" + "=" * 50)
                print("✅ TASK COMPLETED!")
                print("=" * 50)

                # Show the final synthesized result
                if result:
                    print(f"\n📋 Result:\n{result}")
                else:
                    print("\n📋 Task completed but no result was returned.")

            except Exception as e:
                # Handle workflow execution errors gracefully
                print(f"\n❌ Workflow execution failed: {e}")
                print("💡 This might be due to:")
                print("   - API rate limits or network issues")
                print("   - Complex task requirements")
                print("   - Invalid task format")
                print("   - Agent coordination failures")
                print("\nTry:")
                print("   - Simplifying your request")
                print("   - Breaking it into smaller tasks")
                print("   - Checking your API key and quota")

            # Prepare for next task
            print("\n" + "=" * 70)
            print("Ready for next task...")
            print("=" * 70 + "\n")

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\n\n🛑 Session interrupted by user")
            confirm = input("Do you want to exit? (y/n): ").strip().lower()
            if confirm in ["y", "yes"]:
                print("👋 Goodbye!")
                break
            else:
                print("Continuing...\n")
                continue

        except Exception as e:
            # Handle unexpected errors
            print(f"\n❌ Unexpected error: {e}")
            print("💡 Please check your configuration and try again")
            print("   If the problem persists, check logs and configuration files\n")


if __name__ == "__main__":
    """
    Entry point when script is run directly.
    
    Uses asyncio.run() to execute the async main() function.
    This is the standard pattern for async Python applications.
    """
    asyncio.run(main())
