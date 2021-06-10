"""
End to end test of String load from examples/string

"""

import os

import pytest
from kgx.cli.cli_utils import validate

from koza.koza_runner import transform_source
from koza.model.config.source_config import OutputFormat


@pytest.mark.parametrize(
    "ingest, output_names, output_format",
    [
        # (
        #     "string",
        #     [
        #         "stringdb.protein-links-detailed",
        #     ],
        #     OutputFormat.tsv,
        # ),
        (
            "string",
            [
                "stringdb.protein-links-detailed",
            ],
            OutputFormat.jsonl,
        ),
        # (
        #     "examples/string-declarative/metadata.yaml",
        #     [
        #         "stringdb.protein-links-detailed",
        #     ],
        #     OutputFormat.tsv,
        # ),
        # (
        #     "examples/string-declarative/metadata.yaml",
        #     [
        #         "stringdb.protein-links-detailed",
        #     ],
        #     OutputFormat.jsonl,
        # ),
        # (
        #     "examples/string-w-map/metadata.yaml",
        #     [
        #         "stringdb.protein-links-detailed",
        #     ],
        #     OutputFormat.tsv,
        # ),
        # (
        #     "examples/string-w-map/metadata.yaml",
        #     [
        #         "stringdb.protein-links-detailed",
        #     ],
        #     OutputFormat.jsonl,
        # ),
    ],
)
def test_examples(ingest, output_names, output_format):

    source = f"examples/{ingest}/metadata.yaml"
    output_suffix = str(output_format).split('.')[1]
    output_dir = f"./test-output/{ingest}-{output_suffix}"


    output_files = [
        f(file)
        for file in output_names
        for f in (
            lambda file: f"{output_dir}/{file}.{output_suffix}_nodes.{output_suffix}",
            lambda file: f"{output_dir}/{file}.{output_suffix}_edges.{output_suffix}",
        )
    ]

    transform_source(source, output_dir, output_format, None, None)

    for file in output_files:
        assert os.path.exists(file)
        assert os.path.getsize(file) > 0

    validate(output_files, output_suffix, None, None, False)
