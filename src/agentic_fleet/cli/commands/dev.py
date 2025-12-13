"""Development server command - runs backend + frontend together."""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

if TYPE_CHECKING:
    from types import FrameType

console = Console()


def dev(
    backend_port: int = typer.Option(8000, "--backend-port", "-b", help="Backend server port"),
    frontend_port: int = typer.Option(5173, "--frontend-port", "-f", help="Frontend server port"),
    no_frontend: bool = typer.Option(False, "--no-frontend", help="Run backend only"),
    no_backend: bool = typer.Option(False, "--no-backend", help="Run frontend only"),
) -> None:
    """Start both backend and frontend development servers.

    This command launches the FastAPI backend and the Vite frontend dev server
    together, managing both processes and handling graceful shutdown on Ctrl+C.

    Examples:
        agentic-fleet dev                    # Start both servers
        agentic-fleet dev --backend-port 8080
        agentic-fleet dev --no-frontend      # Backend only
    """
    # Resolve frontend directory relative to project structure
    # Path: src/agentic_fleet/cli/commands/dev.py -> src/frontend
    frontend_dir = Path(__file__).parent.parent.parent.parent / "frontend"

    if not frontend_dir.exists() and not no_frontend:
        console.print(f"[yellow]Warning:[/yellow] Frontend directory not found at {frontend_dir}")
        console.print("Run with --no-frontend to start backend only")
        raise typer.Exit(1)

    processes: list[subprocess.Popen] = []

    def cleanup(sig: int, frame: FrameType | None) -> None:  # noqa: ARG001
        """Clean up processes on signal."""
        console.print("\n[yellow]Shutting down servers...[/yellow]")
        for proc in processes:
            if proc.poll() is None:  # Process still running
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        console.print("[green]Servers stopped.[/green]")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    console.print("[bold blue]AgenticFleet Development Server[/bold blue]")
    console.print()

    # Start backend
    if not no_backend:
        console.print(f"[cyan]Starting backend on http://localhost:{backend_port}[/cyan]")
        backend_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "agentic_fleet.main:app",
                "--reload",
                "--port",
                str(backend_port),
                "--log-level",
                "info",
            ],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        processes.append(backend_proc)
        # Give backend a moment to start before frontend
        time.sleep(1)

    # Start frontend
    if not no_frontend:
        console.print(f"[cyan]Starting frontend on http://localhost:{frontend_port}[/cyan]")
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(frontend_port)],
            cwd=frontend_dir,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        processes.append(frontend_proc)

    console.print()
    console.print("[green]Press Ctrl+C to stop all servers[/green]")
    console.print()

    # Wait for processes - if any exits, we'll handle it
    try:
        while True:
            for proc in processes:
                ret = proc.poll()
                if ret is not None:
                    # A process exited
                    console.print(f"[yellow]A server exited with code {ret}[/yellow]")
                    cleanup(signal.SIGTERM, None)
            time.sleep(0.5)
    except KeyboardInterrupt:
        cleanup(signal.SIGINT, None)
