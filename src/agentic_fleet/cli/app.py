import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def main() -> None:
    """AgenticFleet CLI"""
    pass


if __name__ == "__main__":
    app()
