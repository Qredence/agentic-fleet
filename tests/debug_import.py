import os
import sys


def test_debug_imports():
    print("\n--- DEBUG INFO ---")
    print(f"CWD: {os.getcwd()}")
    print(f"sys.path: {sys.path}")

    try:
        import agent_framework

        print(f"agent_framework file: {agent_framework.__file__}")
        print(f"agent_framework dir: {dir(agent_framework)}")

        from agent_framework import ExecutorCompletedEvent  # noqa: F401

        print("Successfully imported ExecutorCompletedEvent")
    except ImportError as e:
        print(f"ImportError: {e}")
    except Exception as e:
        print(f"Error: {e}")
    print("------------------")
