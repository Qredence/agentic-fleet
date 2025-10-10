"""
Configuration Testing Script for AgenticFleet
============================================

This script validates the configuration system and verifies that all
components are properly set up before running the main application.

Tests performed:
1. Environment variable validation
2. Configuration file loading
3. Agent configuration loading
4. Tool imports
5. Agent factory functions

Run this script before the first deployment to catch configuration issues early.
"""

import sys
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_test(name, passed, message=""):
    """Print test result with color coding."""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {name}")
    if message:
        print(f"       {message}")


def test_environment():
    """Test environment variables and .env file."""
    print(f"\n{BOLD}1. Testing Environment Configuration{RESET}")

    try:
        from config.settings import settings

        # Check if .env file exists
        env_file = Path(".env")
        if not env_file.exists():
            print_test(
                "Environment file",
                False,
                f"{YELLOW}Warning: .env file not found. Copy .env.example to .env{RESET}",
            )
            return False

        print_test("Environment file", True, ".env file exists")

        # Check OpenAI API key
        if settings.openai_api_key:
            key_preview = (
                settings.openai_api_key[:10] + "..." if len(settings.openai_api_key) > 10 else "***"
            )
            print_test("OpenAI API Key", True, f"Key loaded: {key_preview}")
        else:
            print_test("OpenAI API Key", False, "OPENAI_API_KEY not set in .env")
            return False

        return True

    except Exception as e:
        print_test("Environment configuration", False, str(e))
        return False


def test_workflow_config():
    """Test workflow configuration file."""
    print(f"\n{BOLD}2. Testing Workflow Configuration{RESET}")

    try:
        from config.settings import settings

        config = settings.workflow_config

        # Check if workflow section exists
        if "workflow" not in config:
            print_test("Workflow configuration", False, "Missing 'workflow' section")
            return False

        workflow = config["workflow"]

        # Check required fields
        required_fields = ["max_rounds", "max_stalls", "max_resets"]
        for field in required_fields:
            if field in workflow:
                print_test(f"Workflow config: {field}", True, f"Value: {workflow[field]}")
            else:
                print_test(f"Workflow config: {field}", False, "Field missing")
                return False

        return True

    except Exception as e:
        print_test("Workflow configuration", False, str(e))
        return False


def test_agent_configs():
    """Test agent configuration files."""
    print(f"\n{BOLD}3. Testing Agent Configurations{RESET}")

    agents = ["orchestrator_agent", "researcher_agent", "coder_agent", "analyst_agent"]

    try:
        from config.settings import settings

        all_passed = True
        for agent_name in agents:
            try:
                config = settings.load_agent_config(f"agents/{agent_name}")

                # Check if agent section exists
                if "agent" not in config:
                    print_test(f"{agent_name} config", False, "Missing 'agent' section")
                    all_passed = False
                    continue

                agent_config = config["agent"]

                # Check required fields in agent section
                if "name" in agent_config and "model" in agent_config:
                    print_test(
                        f"{agent_name} config",
                        True,
                        f"Model: {agent_config['model']}, Temp: {agent_config.get('temperature', 'N/A')}",
                    )
                else:
                    print_test(f"{agent_name} config", False, "Missing required fields")
                    all_passed = False

            except Exception as e:
                print_test(f"{agent_name} config", False, str(e))
                all_passed = False

        return all_passed

    except Exception as e:
        print_test("Agent configurations", False, str(e))
        return False


def test_tool_imports():
    """Test that all tools can be imported."""
    print(f"\n{BOLD}4. Testing Tool Imports{RESET}")

    tools = [
        ("agents.researcher_agent.tools.web_search_tools", "web_search_tool"),
        ("agents.coder_agent.tools.code_interpreter", "code_interpreter_tool"),
        ("agents.analyst_agent.tools.data_analysis_tools", "data_analysis_tool"),
        ("agents.analyst_agent.tools.data_analysis_tools", "visualization_suggestion_tool"),
    ]

    all_passed = True
    for module_name, tool_name in tools:
        try:
            module = __import__(module_name, fromlist=[tool_name])
            tool = getattr(module, tool_name)
            print_test(f"Import {tool_name}", True, f"From {module_name}")
        except Exception as e:
            print_test(f"Import {tool_name}", False, str(e))
            all_passed = False

    return all_passed


def test_agent_factories():
    """Test that all agent factory functions work."""
    print(f"\n{BOLD}5. Testing Agent Factory Functions{RESET}")

    factories = [
        ("agents.orchestrator_agent.agent", "create_orchestrator_agent"),
        ("agents.researcher_agent.agent", "create_researcher_agent"),
        ("agents.coder_agent.agent", "create_coder_agent"),
        ("agents.analyst_agent.agent", "create_analyst_agent"),
    ]

    all_passed = True
    for module_name, factory_name in factories:
        try:
            module = __import__(module_name, fromlist=[factory_name])
            factory = getattr(module, factory_name)

            # Note: We don't actually create the agent here as it requires API key
            # We just verify the function exists and is callable
            if callable(factory):
                print_test(f"Factory {factory_name}", True, f"Callable from {module_name}")
            else:
                print_test(f"Factory {factory_name}", False, "Not callable")
                all_passed = False

        except Exception as e:
            print_test(f"Factory {factory_name}", False, str(e))
            all_passed = False

    return all_passed


def test_workflow_import():
    """Test that workflow can be imported."""
    print(f"\n{BOLD}6. Testing Workflow Import{RESET}")

    try:
        from workflows.magentic_workflow import workflow

        if workflow is not None:
            print_test("Workflow import", True, "workflow instance available")
            return True
        else:
            print_test("Workflow import", False, "workflow is None")
            return False

    except Exception as e:
        print_test("Workflow import", False, str(e))
        return False


def main():
    """Run all configuration tests."""
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}AgenticFleet Configuration Test Suite{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    results = {
        "Environment": test_environment(),
        "Workflow Config": test_workflow_config(),
        "Agent Configs": test_agent_configs(),
        "Tool Imports": test_tool_imports(),
        "Agent Factories": test_agent_factories(),
        "Workflow Import": test_workflow_import(),
    }

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
        print(f"\n{GREEN}✓ All tests passed! System is ready to run.{RESET}")
        print(f"\nNext steps:")
        print(f"  1. Make sure your .env file has a valid OPENAI_API_KEY")
        print(f"  2. Run: python main.py")
        return 0
    else:
        print(f"\n{RED}✗ Some tests failed. Please fix the issues above.{RESET}")
        print(f"\nCommon fixes:")
        print(f"  - Copy .env.example to .env and add your OpenAI API key")
        print(f"  - Check YAML files for syntax errors")
        print(f"  - Ensure all dependencies are installed: uv sync")
        return 1


if __name__ == "__main__":
    sys.exit(main())
