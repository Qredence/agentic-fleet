from __future__ import annotations

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


def main() -> None:
    """AgenticFleet CLI"""
    pass


app.callback()(main)


if __name__ == "__main__":
    app()
