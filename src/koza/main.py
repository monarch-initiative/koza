#!/usr/bin/env python3
"""CLI for Koza - wraps the koza library to provide a command line interface"""

from collections import defaultdict
from pathlib import Path
from typing import Annotated, Optional

import typer
from loguru import logger
from tqdm import tqdm

from koza.model.formats import OutputFormat
from koza.runner import KozaRunner

typer_app = typer.Typer(
    no_args_is_help=True,
)


@typer_app.callback(invoke_without_command=True)
def callback(version: Optional[bool] = typer.Option(None, "--version", is_eager=True)):
    if version:
        from koza import __version__

        typer.echo(f"Koza version: {__version__}")
        raise typer.Exit()


def parse_input_files(args: list[str]):
    tagged_ret: defaultdict[str, list[str]] = defaultdict(list)
    untagged_ret: list[str] = []
    parse_as_single_arg: bool | None = None
    for arg in args:
        parts = arg.split(":", 1)
        is_single_arg = len(parts) == 1

        if parse_as_single_arg is None:
            parse_as_single_arg = is_single_arg
        elif is_single_arg != parse_as_single_arg:
            raise ValueError("Cannot mix tagged and untagged input files")

        if is_single_arg:
            untagged_ret.append(parts[0])
        else:
            tagged_ret[parts[0]].append(parts[1])
    return untagged_ret if untagged_ret else dict(tagged_ret)


@typer_app.command()
def transform(
    configuration_yaml: Annotated[
        str,
        typer.Argument(help="Configuration YAML file"),
    ],
    input_files: Annotated[
        Optional[list[str]],
        typer.Option("--input-file", "-i", help="Override input files"),
    ] = None,
    output_dir: Annotated[
        str,
        typer.Option("--output-dir", "-o", help="Path to output directory"),
    ] = "./output",
    output_format: Annotated[
        OutputFormat,
        typer.Option("--output-format", "-f", help="Output format"),
    ] = OutputFormat.tsv,
    row_limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of rows to process (if skipped, processes entire source file)"),
    ] = 0,
    show_progress: Annotated[
        bool,
        typer.Option("--progress", "-p", help="Display progress of transform"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Disable log output"),
    ] = False,
) -> None:
    """Transform a source file"""
    logger.remove()

    output_path = Path(output_dir)

    if output_path.exists() and not output_path.is_dir():
        raise NotADirectoryError(f"{output_dir} is not a directory")
    elif not output_path.exists():
        output_path.mkdir(parents=True)

    if not quiet:
        prompt = "{time:YYYY-MM-DD HH:mm:ss.SSS} | <level>{level}</level> | <level>{message}</level>"

        def log(msg: str):
            tqdm.write(msg, end="")

        logger.add(log, format=prompt, colorize=True)

    parsed_input_files = parse_input_files(input_files) if input_files else None

    # FIXME: Verbosity, logging
    config, runner = KozaRunner.from_config_file(
        configuration_yaml,
        input_files=parsed_input_files,
        output_dir=output_dir,
        output_format=output_format,
        row_limit=row_limit,
        show_progress=show_progress,
    )

    logger.info(f"Running transform for {config.name} with output to `{output_dir}`")

    runner.run()

    logger.info(f"Finished transform for {config.name}")


# @typer_app.command()
# def validate(
#     file: str = typer.Option(..., help="Path or url to the source file"),
#     format: InputFormat = InputFormat.csv,
#     delimiter: str = ",",
#     header_delimiter: str = None,
#     skip_blank_lines: bool = True,
# ) -> None:
#     """Validate a source file"""
#     validate_file(file, format, delimiter, header_delimiter, skip_blank_lines)
#
#
# @typer_app.command()
# def split(
#     file: str = typer.Argument(..., help="Path to the source kgx file to be split"),
#     fields: str = typer.Argument(..., help="Comma separated list of fields to split on"),
#     remove_prefixes: bool = typer.Option(
#         False,
#         help=(
#             "Remove prefixes from the file names for values from the specified fields. "
#             "(e.g, NCBIGene:9606 becomes 9606).",
#         )
#     ),
#     output_dir: str = typer.Option(default="output", help="Path to output directory"),
# ):
#     """Split a file by fields"""
#     split_file(file, fields, remove_prefixes=remove_prefixes, output_dir=output_dir)


if __name__ == "__main__":
    typer_app()
