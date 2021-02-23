#!/usr/bin/env python3

import typer

bioweave_cli = typer.Typer()


@bioweave_cli.command()
def run(name: str = typer.Argument(..., help="The name of the user to greet")):
    """
    Run a single file through bioweave
    """
    typer.echo(f"Creating item: {name}")


@bioweave_cli.command()
def batch(item: str):
    """
    Run a group of files through bioweave
    """
    typer.echo(f"Deleting item: {item}")


@bioweave_cli.command()
def create(item: str):
    """
    Create a bioweave stub with config files
    """
    typer.echo(f"Deleting item: {item}")


if __name__ == "__main__":
    bioweave_cli()
