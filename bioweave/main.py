#!/usr/bin/env python3

import typer

app = typer.Typer()


@app.command()
def run(name: str = typer.Argument(..., help="The name of the user to greet")):
    """
    Run a single file through bioweave
    """
    typer.echo(f"Creating item: {name}")


@app.command()
def batch(item: str):
    """
    Run a group of files through bioweave
    """
    typer.echo(f"Deleting item: {item}")


@app.command()
def create(item: str):
    """
    Create a new bioweave project
    """
    typer.echo(f"Deleting item: {item}")


if __name__ == "__main__":
    app()
