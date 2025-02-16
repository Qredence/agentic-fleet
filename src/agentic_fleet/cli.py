"""Command line interface for AgenticFleet."""

import os
import subprocess
import sys

import click
from dotenv import load_dotenv


@click.group()
def cli():
    """AgenticFleet CLI - A multi-agent system for adaptive AI reasoning."""
    pass


@cli.command()
@click.argument('mode', type=click.Choice(['default', 'no-oauth']), default='default')
def start(mode: str):
    """Start AgenticFleet with or without OAuth."""
    try:
        # Load environment variables from .env file
        load_dotenv()

        # Set OAuth environment variables based on mode
        if mode == 'no-oauth':
            os.environ["USE_OAUTH"] = "false"
            os.environ["OAUTH_CLIENT_ID"] = ""
            os.environ["OAUTH_CLIENT_SECRET"] = ""
            print("Starting AgenticFleet without OAuth...")
        else:
            os.environ["USE_OAUTH"] = "true"
            print("Starting AgenticFleet with OAuth...")

        # Get the path to app.py
        app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        app_path = os.path.join(app_dir, "app.py")

        # Run chainlit directly using subprocess
        subprocess.run(["chainlit", "run", app_path], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Error running chainlit: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error starting AgenticFleet: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
