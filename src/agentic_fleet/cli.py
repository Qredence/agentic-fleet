"""Command line interface for AgenticFleet."""

import os
import subprocess
import sys
from typing import Optional

import click
from dotenv import load_dotenv


def setup_environment(no_oauth: bool = False) -> None:
    """Setup environment variables based on OAuth setting."""
    load_dotenv()

    if no_oauth:
        # Disable OAuth by setting empty values
        os.environ["OAUTH_CLIENT_ID"] = ""
        os.environ["OAUTH_CLIENT_SECRET"] = ""
        os.environ["OAUTH_REDIRECT_URI"] = ""
        os.environ["OAUTH_SCOPES"] = ""
        os.environ["OAUTH_AUTHORIZE_URL"] = ""
        os.environ["OAUTH_TOKEN_URL"] = ""
        os.environ["OAUTH_USER_INFO_URL"] = ""

def get_app_path() -> str:
    """Get the absolute path to the app.py file."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "app.py"))

@click.group()
def cli():
    """AgenticFleet CLI - A multi-agent system for adaptive AI reasoning."""
    pass

@cli.command()
@click.option('--no-oauth', is_flag=True, help='Start without OAuth authentication')
@click.option('--port', default=8001, help='Port to run Magentic One server on')
@click.option('--host', default='localhost', help='Host to run the server on')
def start(no_oauth: bool, port: int, host: str):
    """Start the AgenticFleet server."""
    # Setup environment based on OAuth flag
    setup_environment(no_oauth)

    # Get app path
    app_path = get_app_path()

    # Print startup message
    auth_mode = "without" if no_oauth else "with"
    click.echo(f"Starting AgenticFleet {auth_mode} OAuth on {host}:{port}...")

    # Build chainlit command
    cmd = [
        "chainlit",
        "run",
        app_path,
        "--host", host,
        "--port", str(port)
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running chainlit: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        sys.exit(0)

def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
