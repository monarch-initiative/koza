Koza includes a `mock_koza` fixture (see `src/koza/utils/testing_utils`) that can be used to test your ingest configuration. This fixture accepts the following arguments:

| Argument           | Type                      | Description                           |
| ------------------ | ------------------------- | ------------------------------------- |
| Required Arguments |
| `name`             | `str`                     | The name of the ingest                |
| `data`             | `Union[Dict, List[Dict]]` | The data to be ingested               |
| `transform_code`   | `str`                     | Path to the transform code to be used |
| Optional Arguments |
| `map_cache`        | `Dict`                    | Map cache to be used                  |
| `filters`          | `List(str)`               | List of filters to apply to data      |
| `global_table`     | `str`                     | Path to the global table              |
| `local_table`      | `str`                     | Path to the local table               |

The `mock_koza` fixture returns a list of entities that would be generated by the ingest configuration.  
This list can then be used to test the output based on the transform script.

Here is an example of how to use the `mock_koza` fixture to test an ingest configuration:

```python
import pytest

from koza.utils.testing_utils import mock_koza

# Define the source name and transform script path
INGEST_NAME = "your_ingest_name"
TRANSFORM_SCRIPT = "./src/{{cookiecutter.__project_slug}}/transform.py"

# Define an example row to test (as a dictionary)
@pytest.fixture
def example_row():
    return {
        "example_column_1": "entity_1",
        "example_column_2": "entity_6",
        "example_column_3": "biolink:related_to",
    }

# Or a list of rows
@pytest.fixture
def example_list_of_rows():
    return [
        {
            "example_column_1": "entity_1",
            "example_column_2": "entity_6",
            "example_column_3": "biolink:related_to",
        },
        {
            "example_column_1": "entity_2",
            "example_column_2": "entity_7",
            "example_column_3": "biolink:related_to",
        },
    ]

# Define the mock koza transform
@pytest.fixture
def mock_transform(mock_koza, example_row):
    return mock_koza(
        INGEST_NAME,
        example_row,
        TRANSFORM_SCRIPT,
    )

# Or for multiple rows
@pytest.fixture
def mock_transform_multiple_rows(mock_koza, example_list_of_rows):
    return mock_koza(
        INGEST_NAME,
        example_list_of_rows,
        TRANSFORM_SCRIPT,
    )

# Test the output of the transform

def test_single_row(mock_transform):
    assert len(mock_transform) == 1
    entity = mock_transform[0]
    assert entity
    assert entity.subject == "entity_1"


def test_multiple_rows(mock_transform_multiple_rows):
    assert len(mock_transform_multiple_rows) == 2
    entity_1 = mock_transform_multiple_rows[0]
    entity_2 = mock_transform_multiple_rows[1]
    assert entity_1.subject == "entity_1"
    assert entity_2.subject == "entity_2"
```