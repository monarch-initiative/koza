"""
End to end test of String load from examples/string
"""

from pathlib import Path

import pytest

from koza.cli_runner import transform_source
from koza.model.config.source_config import OutputFormat


@pytest.mark.parametrize(
    "source_name, ingest, output_format",
    [
        ("string", "protein-links-detailed", OutputFormat.tsv),
        ("string", "protein-links-detailed", OutputFormat.jsonl),
        ("string-declarative", "declarative-protein-links-detailed", OutputFormat.tsv),
        ("string-declarative", "declarative-protein-links-detailed", OutputFormat.jsonl),
        ("string-w-map", "map-protein-links-detailed", OutputFormat.tsv),
        ("string-w-map", "map-protein-links-detailed", OutputFormat.jsonl),
        ("string-w-custom-map", "custom-map-protein-links-detailed", OutputFormat.tsv),
        ("string-w-custom-map", "custom-map-protein-links-detailed", OutputFormat.jsonl),
    ],
)
def test_examples(source_name, ingest, output_format):

    source_config = f"examples/{source_name}/{ingest}.yaml"
    
    output_suffix = str(output_format).split('.')[1]
    output_dir = f"./test-output/string/test-examples"

    output_files = [
        f"{output_dir}/{ingest}_nodes.{output_suffix}",
        f"{output_dir}/{ingest}_edges.{output_suffix}"
    ]


    transform_source(source_config, output_dir, output_format, "examples/translation_table.yaml", None)

    for file in output_files:
        assert Path(file).exists()
        # assert Path(file).stat().st_size > 0  # Removed this line because now node files are not

    # TODO: at some point, these assertions could get more rigorous, but knowing if we have errors/exceptions is a start
