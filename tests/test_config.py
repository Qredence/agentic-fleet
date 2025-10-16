"""
Configuration Testing for AgenticFleet
======================================

This module contains pytest tests that validate the configuration system
and verify that all components are properly set up before running the main application.

Tests performed:
1. Environment variable validation
2. Configuration file loading
3. Agent configuration loading
4. Tool imports
5. Agent factory functions
"""

from pathlib import Path

# Color codes for terminal output (kept for backward compatibility if run as script)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def test_environment():
    """Test environment variables and .env file."""
    import os

    from agenticfleet.config import settings

    # Check if .env file exists OR environment variables are set (for CI)
    env_file = Path(".env")
    openai_key_from_env = os.getenv("OPENAI_API_KEY")

    if not env_file.exists() and not openai_key_from_env:
        msg = ".env file not found and OPENAI_API_KEY not in environment. Copy .env.example to .env"
        assert False, msg

    # Check OpenAI API key is available (from .env or environment)
    assert settings.openai_api_key or openai_key_from_env, "OPENAI_API_KEY not set"


def test_workflow_config():
    """Test workflow configuration file."""
    from agenticfleet.config import settings

    config = settings.workflow_config

    # Check if workflow section exists
    assert "workflow" in config, "Missing 'workflow' section"

    workflow = config["workflow"]

    # Check required fields
    required_fields = ["max_rounds", "max_stalls", "max_resets"]
    for field in required_fields:
        assert field in workflow, f"Missing required field: {field}"


def test_agent_configs():
    """Test agent configuration files."""
    agents = ["orchestrator", "researcher", "coder", "analyst"]

    from agenticfleet.config import settings

    for agent_name in agents:
        config = settings.load_agent_config(agent_name)

        # Check if agent section exists
        assert "agent" in config, f"Missing 'agent' section for {agent_name}"

        agent_config = config["agent"]

        # Check required fields in agent section
        assert "name" in agent_config, f"Missing 'name' field for {agent_name}"
        assert "model" in agent_config, f"Missing 'model' field for {agent_name}"


def test_tool_imports():
    """Test that all tools can be imported."""
    tools = [
        ("agenticfleet.agents.researcher.tools.web_search_tools", "web_search_tool"),
        ("agenticfleet.agents.analyst.tools.data_analysis_tools", "data_analysis_tool"),
        ("agenticfleet.agents.analyst.tools.data_analysis_tools", "visualization_suggestion_tool"),
    ]

    for module_name, tool_name in tools:
        module = __import__(module_name, fromlist=[tool_name])
        tool = getattr(module, tool_name)
        assert tool is not None, f"Could not import {tool_name} from {module_name}"


def test_agent_factories():
    """Test that all agent factory functions work."""
    factories = [
        ("agenticfleet.agents.orchestrator.agent", "create_orchestrator_agent"),
        ("agenticfleet.agents.researcher.agent", "create_researcher_agent"),
        ("agenticfleet.agents.coder.agent", "create_coder_agent"),
        ("agenticfleet.agents.analyst.agent", "create_analyst_agent"),
    ]

    for module_name, factory_name in factories:
        module = __import__(module_name, fromlist=[factory_name])
        factory = getattr(module, factory_name)

        # Note: We don't actually create the agent here as it requires API key
        # We just verify the function exists and is callable
        assert callable(factory), f"Factory {factory_name} is not callable"


def test_fleet_import():
    """Test that fleet factory can be imported."""
    from agenticfleet.fleet import MagenticFleet, create_default_fleet

    assert callable(create_default_fleet)
    assert MagenticFleet is not None


def print_test(name, passed, message=""):
    """Print test result with color coding."""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {name}")
    if message:
        print(f"       {message}")


def main():
    """Run all configuration tests."""
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}AgenticFleet Configuration Test Suite{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # Run tests and capture results
    test_functions = {
        "Environment": test_environment,
        "Workflow Config": test_workflow_config,
        "Agent Configs": test_agent_configs,
        "Tool Imports": test_tool_imports,
        "Agent Factories": test_agent_factories,
        "Fleet Import": test_fleet_import,
    }

    results = {}
    for test_name, test_func in test_functions.items():
        try:
            test_func()
            results[test_name] = True
        except (AssertionError, ImportError) as e:
            results[test_name] = False
            print(f"  {RED}✗{RESET} {test_name}: {str(e)}")

    # Summary
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}Test Summary{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {test_name}: {status}")

    print(f"\n{BOLD}Overall: {passed}/{total} tests passed{RESET}")

    if passed == total:
        print(f"\n{GREEN}[OK] All tests passed! System is ready to run.{RESET}")
        print("\nNext steps:")
        print("  1. Make sure your .env file has a valid OPENAI_API_KEY")
        print("  2. Run: uv run fleet")
        return 0
    else:
        print(f"\n{RED}[FAIL] Some tests failed. Please fix the issues above.{RESET}")
        print("\nCommon fixes:")
        print("  - Copy .env.example to .env and add your OpenAI API key")
        print("  - Check YAML files for syntax errors")
        print("  - Ensure all dependencies are installed: uv sync")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
