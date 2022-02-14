"""
End to end test of String load from examples/string
"""

from pathlib import Path

import pytest

from koza.cli_runner import transform_source
from koza.model.config.source_config import OutputFormat


@pytest.mark.parametrize(
    "ingest, output_names, output_format",
    [
        (
            "string",
            [
                "protein-links-detailed",
            ],
            OutputFormat.tsv,
        ),
        (
            "string",
            [
                "protein-links-detailed",
            ],
            OutputFormat.jsonl,
        ),
        (
            "string-declarative",
            [
                "protein-links-detailed",
            ],
            OutputFormat.tsv,
        ),
        (
            "string-declarative",
            [
                "protein-links-detailed",
            ],
            OutputFormat.jsonl,
        ),
        ("string-w-map", ["protein-links-detailed"], OutputFormat.tsv),
        ("string-w-map", ["protein-links-detailed"], OutputFormat.jsonl),
        ("string-w-custom-map", ["protein-links-detailed"], OutputFormat.tsv),
        ("string-w-custom-map", ["protein-links-detailed"], OutputFormat.jsonl),
    ],
)
def test_examples(ingest, output_names, output_format):

    source = f"examples/{ingest}/protein-links-detailed.yaml"
    output_suffix = str(output_format).split('.')[1]
    output_dir = f"./test-output/{ingest}-{output_suffix}"

    output_files = [
        output_file
        for file in output_names
        for output_file in [
            f"{output_dir}/{file}_nodes.{output_suffix}",
            f"{output_dir}/{file}_edges.{output_suffix}",
        ]
    ]

    transform_source(source, output_dir, output_format, "examples/translation_table.yaml", None)

    for file in output_files:
        assert Path(file).exists()
        assert Path(file).stat().st_size > 0

    # TODO: at some point, these assertions could get more rigorous, but knowing if we have errors/exceptions is a start
