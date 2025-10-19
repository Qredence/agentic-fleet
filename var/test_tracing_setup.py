#!/usr/bin/env python3
"""
Test script to verify OpenTelemetry tracing is working.

Usage:
    uv run python test_tracing_setup.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def test_import() -> bool:
    \"\"\"Test that tracing module can be imported.\"\"\"
    print("✓ Testing imports...")
    try:
        from agenticfleet import setup_tracing  # type: ignore[attr-defined]  # noqa: F401

        print("  ✓ Successfully imported tracing functions")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_setup() -> bool:
    """Test that tracing can be initialized."""
    print("\n✓ Testing tracing setup...")
    try:
        from agenticfleet import is_tracing_enabled, setup_tracing  # type: ignore[attr-defined]

        # Setup with default endpoint
        setup_tracing()
        print("  ✓ setup_tracing() called successfully")

        # Check if enabled
        enabled = is_tracing_enabled()
        print(f"  ✓ Tracing enabled: {enabled}")

        return True
    except Exception as e:
        print(f"  ✗ Setup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_config() -> bool:
    """Test that config can be retrieved."""
    print("\n✓ Testing configuration retrieval...")
    try:
        from agenticfleet import get_trace_config  # type: ignore[attr-defined]

        config = get_trace_config()
        print(f"  ✓ Config retrieved: {config}")
        return True
    except Exception as e:
        print(f"  ✗ Config retrieval failed: {e}")
        return False


def test_environment_vars() -> bool:
    """Test environment variable handling."""
    print("\n✓ Testing environment variables...")
    import os

    env_vars = {
        "OTLP_ENDPOINT": os.getenv("OTLP_ENDPOINT", "(not set)"),
        "TRACING_ENABLED": os.getenv("TRACING_ENABLED", "(not set)"),
        "ENABLE_SENSITIVE_DATA": os.getenv("ENABLE_SENSITIVE_DATA", "(not set)"),
    }

    for key, value in env_vars.items():
        print(f"  {key}: {value}")

    return True


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("AgenticFleet OpenTelemetry Tracing Test")
    print("=" * 60)

    tests = [
        ("Import Test", test_import),
        ("Setup Test", test_setup),
        ("Config Test", test_config),
        ("Environment Variables", test_environment_vars),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests passed! Tracing is ready to use.")
        print("\nNext steps:")
        print("1. Start AI Toolkit tracing viewer (Cmd+Shift+P → 'AI Toolkit: Open Tracing Page')")
        print("2. Run backend: make haxui-server")
        print("3. Send a request and check AI Toolkit for traces")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
