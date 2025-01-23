"""Script to run the Chainlit server."""

import os
import signal
import subprocess


def run_server() -> None:
    """Run the Chainlit server."""
    # Start Chainlit server
    chainlit_process = subprocess.Popen(
        ["chainlit", "run", "src/app/app.py", "-w", "--port", "8001"],
        env={**os.environ}
    )

    print(f"\n✨ Service started:")
    print(f"🌐 Chainlit interface available at http://localhost:8001")
    print("\nPress Ctrl+C to stop the service\n")

    try:
        # Wait for the process
        chainlit_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping service...")
        # Kill process
        chainlit_process.terminate()
        try:
            chainlit_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chainlit_process.kill()
        print("✅ Service stopped successfully")

if __name__ == "__main__":
    run_server()
