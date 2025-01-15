"""
Test the row_limit argument for transforms
Assert correct number of rows has been processed
"""

from pathlib import Path

import pytest

from koza.model.formats import OutputFormat
from koza.runner import KozaRunner

# TODO: Parameterize row_limit, and test reading from JSON and JSONL
# TODO: Address filter in examples/string-declarative/protein-links-detailed.yaml


@pytest.mark.parametrize(
    "source_name, ingest, output_format, row_limit, header_len, expected_node_len, expected_edge_len",
    [
        (
            "string-declarative",  # ingest
            "declarative-protein-links-detailed",  # output_names
            OutputFormat.tsv,  # output_format
            3,  # row_limit
            1,  # header_len
            11,  # expected_node_leng
            6,  # expected_edge_leng
        )
    ],
)
def test_examples(source_name, ingest, output_format, row_limit, header_len, expected_node_len, expected_edge_len):
    config_filename = f"examples/{source_name}/{ingest}.yaml"

    output_suffix = str(output_format).split(".")[1]
    output_dir = "./output/tests/string-test-examples"

    output_files = [f"{output_dir}/{ingest}_nodes.{output_suffix}", f"{output_dir}/{ingest}_edges.{output_suffix}"]

    for file in output_files:
        Path(file).unlink(missing_ok=True)

    config, runner = KozaRunner.from_config_file(config_filename, output_dir, output_format, row_limit)
    runner.run()

    # hacky check that correct number of rows was processed
    # node_file = f"{output_dir}/string/{ingest}-row-limit_nodes{output_suffix}"
    # edge_file = f"{output_dir}/string/{ingest}-row-limit_edges{output_suffix}"

    with open(output_files[0], "r") as fp:
        assert expected_node_len == len([line for line in fp])

    with open(output_files[1], "r") as fp:
        assert expected_edge_len == len([line for line in fp])
