"""Development server launcher for AgenticFleet.

This module provides a unified entry point to start both the backend (haxui-server)
and frontend development servers concurrently, similar to `make dev`.
"""

import signal
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Start both backend and frontend development servers."""
    print("=" * 60)
    print("Starting AgenticFleet Development Environment")
    print("=" * 60)
    print("")
    print("Backend:  http://localhost:8000")
    print("Frontend: http://localhost:5173")
    print("")
    print("Press Ctrl+C to stop both services")
    print("")

    # Find the frontend directory
    frontend_dir = Path(__file__).parent.parent.parent.parent / "frontend"
    if not frontend_dir.exists():
        print(f"Error: Frontend directory not found at {frontend_dir}")
        print("Please ensure you've run 'make frontend-install' first.")
        sys.exit(1)

    # List to track spawned processes
    processes: list[subprocess.Popen[str]] = []

    def signal_handler(signum: int, frame: object) -> None:
        """Handle SIGINT/SIGTERM to cleanly shut down both servers."""
        print("\n\nShutting down servers...")
        for proc in processes:
            if proc.poll() is None:  # Process is still running
                try:
                    proc.terminate()
                except Exception as e:
                    print(f"Error terminating process: {e}")
        # Wait for processes to terminate
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception as e:
                    print(f"Error killing process: {e}")
            except Exception as e:
                print(f"Error waiting for process: {e}")
        print("Servers stopped.")
        sys.exit(0)

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start backend server (uvicorn)
        print("Starting backend server...")
        backend = subprocess.Popen(
            [
                "uvicorn",
                "agenticfleet.haxui.api:app",
                "--reload",
                "--port",
                "8000",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(backend)

        # Start frontend server (npm)
        print("Starting frontend server...")
        frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(frontend)

        print("\n✓ Both servers started successfully!\n")

        # Stream output from both processes
        streams = [
            (backend.stdout, "backend"),
            (frontend.stdout, "frontend"),
        ]

        while True:
            # Check if either process has died
            if backend.poll() is not None:
                print("\n⚠ Backend server exited unexpectedly")
                frontend.terminate()
                sys.exit(backend.returncode)

            if frontend.poll() is not None:
                print("\n⚠ Frontend server exited unexpectedly")
                backend.terminate()
                sys.exit(frontend.returncode)

            # Read and display output from both processes
            for stream, label in streams:
                if stream and stream.readable():
                    try:
                        line = stream.readline()
                        if line:
                            print(f"[{label}] {line.rstrip()}")
                    except Exception:
                        pass

    except Exception as e:
        print(f"\nError starting servers: {e}")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        sys.exit(1)


if __name__ == "__main__":
    main()
