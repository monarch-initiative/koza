#!/usr/bin/env python3

import typer

app = typer.Typer()


@app.command()
def run(
        name: str = typer.Argument(..., help="The name of the user to greet")
):
    """
    Run a single file through koza
    """
    typer.echo(f"Creating item: {name}")


@app.command()
def batch(item: str):
    """
    TODO
    Run a group of files through koza
    """


@app.command()
def create():
    """
    TODO
    Create a new koza project
    """


if __name__ == "__main__":
    app()
