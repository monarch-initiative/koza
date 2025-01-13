"""
End to end test of String load from examples/string

TODO:
- May want to change to not make/assert both node and edge files now that ingests are either node or edge only
"""

from pathlib import Path
from urllib.request import urlopen
import yaml

import pytest

from koza.cli_utils import transform_source
from koza.model.formats import OutputFormat

# pytest.skip("LinkML issue with `category` slot has `designates_type: true`", allow_module_level=True)

model_url = "https://raw.githubusercontent.com/biolink/biolink-model/latest/biolink-model.yaml"
with urlopen(model_url) as f:
    model = yaml.load(f, Loader=yaml.FullLoader)


@pytest.mark.parametrize(
    "source_name, ingest, output_format, schema",
    [
        ("string", "protein-links-detailed", OutputFormat.tsv, model),
        ("string", "protein-links-detailed", OutputFormat.jsonl, model),
        ("string-declarative", "declarative-protein-links-detailed", OutputFormat.tsv, model),
        ("string-declarative", "declarative-protein-links-detailed", OutputFormat.jsonl, model),
        ("string-w-map", "map-protein-links-detailed", OutputFormat.tsv, model),
        ("string-w-map", "map-protein-links-detailed", OutputFormat.jsonl, model),
        ("string-w-custom-map", "custom-map-protein-links-detailed", OutputFormat.tsv, model),
        ("string-w-custom-map", "custom-map-protein-links-detailed", OutputFormat.jsonl, model),
    ],
)
def test_validator(source_name, ingest, output_format, schema):
    source_config = f"examples/{source_name}/{ingest}.yaml"

    output_suffix = str(output_format).split('.')[1]
    output_dir = "./output/tests/string-test-validator"

    output_files = [f"{output_dir}/{ingest}_nodes.{output_suffix}", f"{output_dir}/{ingest}_edges.{output_suffix}"]

    transform_source(
        source_config,
        output_dir,
        output_format,
        global_table="tests/resources/translation_table.yaml",
        schema=schema,
        node_type="named thing",
        edge_type="association",
    )

    for file in output_files:
        assert Path(file).exists()
        # assert Path(file).stat().st_size > 0  # Removed this line because now node files are not
