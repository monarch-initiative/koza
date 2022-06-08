"""
End to end test of String load from examples/string

TODO:
- May want to change to not make/assert both node and edge files now that ingests are either node or edge only
"""

from pathlib import Path

import pytest

from koza.cli_runner import transform_source
from koza.model.config.source_config import OutputFormat

#model_schema = Path(__file__).parent.parent / 'resources' / 'biolink-model.yaml'
model_schema = "tests/resources/biolink-model.yaml"

@pytest.mark.parametrize(
    "source_name, ingest, output_format, schema",
    [
        ("string", "protein-links-detailed", OutputFormat.tsv, model_schema),
        ("string", "protein-links-detailed", OutputFormat.jsonl, model_schema),
        ("string-declarative", "declarative-protein-links-detailed", OutputFormat.tsv, model_schema),
        ("string-declarative", "declarative-protein-links-detailed", OutputFormat.jsonl, model_schema),
        ("string-w-map", "map-protein-links-detailed", OutputFormat.tsv, model_schema),
        ("string-w-map", "map-protein-links-detailed", OutputFormat.jsonl, model_schema),
        ("string-w-custom-map", "custom-map-protein-links-detailed", OutputFormat.tsv, model_schema),
        ("string-w-custom-map", "custom-map-protein-links-detailed", OutputFormat.jsonl, model_schema),
    ],
)
def test_validator(source_name, ingest, output_format, schema):

    source_config = f"examples/{source_name}/{ingest}.yaml"
    
    output_suffix = str(output_format).split('.')[1]
    output_dir = f"./test-output/string/test-validator"

    output_files = [
        f"{output_dir}/{ingest}_nodes.{output_suffix}",
        f"{output_dir}/{ingest}_edges.{output_suffix}"
    ]

    transform_source(
        source_config,
        output_dir,
        output_format,
        global_table="tests/resources/translation_table.yaml",
        schema=schema
        #schema="tests/resources/biolink-model.yaml",
    )

    for file in output_files:
        assert Path(file).exists()
        # assert Path(file).stat().st_size > 0  # Removed this line because now node files are not
