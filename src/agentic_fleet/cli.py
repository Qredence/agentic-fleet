"""Command line interface for AgenticFleet."""

import os
import subprocess
import sys
from typing import Optional  # noqa: F401

import click
from dotenv import load_dotenv


def get_app_path() -> str:
    """Get the absolute path to the app.py file."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "app.py"))

def get_config_path(no_oauth: bool = False) -> str:
    """Get the path to the appropriate config file."""
    config_name = "config.no-oauth.toml" if no_oauth else "config.oauth.toml"
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".chainlit", config_name))

@click.group()
def cli():
    """AgenticFleet CLI - A multi-agent system for adaptive AI reasoning."""
    pass

@cli.command()
@click.argument('mode', type=click.Choice(['default', 'no-oauth']), default='default')
def start(mode: str):
    """Start the AgenticFleet server.

    MODE can be either 'default' (with OAuth) or 'no-oauth'
    """
    # Load environment variables
    load_dotenv()

    # Set OAuth mode
    no_oauth = mode == 'no-oauth'

    # Get paths
    app_path = get_app_path()
    config_path = get_config_path(no_oauth)

    # Set environment variables
    os.environ['USE_OAUTH'] = str(not no_oauth).lower()
    os.environ['CHAINLIT_CONFIG'] = config_path

    # Print startup message
    auth_mode = "without" if no_oauth else "with"
    click.echo(f"Starting AgenticFleet {auth_mode} OAuth...")

    # Build chainlit command
    cmd = ["chainlit", "run", app_path]

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
