"""
Test the row_limit argument for transforms
Assert correct number of rows has been processed
"""
# TODO: Parameterize row_limit, and test reading from JSON and JSONL
# TODO: Address filter in examples/string-declarative/protein-links-detailed.yaml


import pytest

from koza.cli_runner import transform_source
from koza.model.config.source_config import OutputFormat


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
def test_examples(
    source_name, ingest, output_format, row_limit, header_len, expected_node_len, expected_edge_len
):

    source_config = f"examples/{source_name}/{ingest}.yaml"
    
    output_suffix = str(output_format).split('.')[1]
    output_dir = f"./test-output/string/test-row-limit"

    transform_source(
        source=source_config,
        output_dir=output_dir,
        output_format=output_format,
        global_table="examples/translation_table.yaml",
        row_limit=row_limit,
    )

    # hacky check that correct number of rows was processed
    #node_file = f"{output_dir}/string/{ingest}-row-limit_nodes{output_suffix}"
    #edge_file = f"{output_dir}/string/{ingest}-row-limit_edges{output_suffix}"

    output_files = [
        f"{output_dir}/{ingest}_nodes.{output_suffix}",
        f"{output_dir}/{ingest}_edges.{output_suffix}"
    ]

    number_of_lines = [
        sum(1 for line in open(output_files[0])),
        sum(1 for line in open(output_files[1]))
    ]

    assert number_of_lines == [expected_node_len, expected_edge_len]

    #assert node_lines == expected_node_len
    #assert edge_lines == expected_edge_len
