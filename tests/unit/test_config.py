"""
Testing the biolink config dataclasses + pydandic

"""

import pytest
from koza.model.config.source_config import KozaConfig, TransformConfig
from pydantic import TypeAdapter, ValidationError


@pytest.mark.parametrize(
    "inclusion, column, filter_code, value",
    (
        [
            ('include', 'combined_score', 'lt', '70'),
            ('exclude', 'combined_score', 'lt', '70'),
            ('include', 'combined_score', 'in', '70'),
            ('exclude', 'combined_score', 'in', '70'),
            ('exclude', 'combined_score', 'in', 70),
            ('exclude', 'combined_score', 'in', 0.7),
            ('include', 'combined_score', 'eq', ['goat', 'sheep']),
            ('include', 'combined_score', 'lt', ['goat', 'sheep']),
            ('include', 'combined_score', 'ge', ['goat', 'sheep']),
        ]
    ),
)
def test_wrong_filter_type_raises_exception(inclusion, column, filter_code, value):
    """
    Test if include and exclude raise a
    value error when handed an incompatible type,
    eg a string when using the lt operator
    """
    config = {
        "filters": [
            {
                'column': column,
                'inclusion': inclusion,
                'filter_code': filter_code,
                'value': value,
            }
        ],
    }
    with pytest.raises(ValidationError) as e:
        TypeAdapter(TransformConfig).validate_python(config)

    for error in e.value.errors():
        assert error["msg"].startswith("Input should be a")


@pytest.mark.parametrize(
    "inclusion, code",
    (
        [
            ('include', 'lgt'),
            ('exclude', 'ngte'),
        ]
    ),
)
def test_wrong_filter_code_raises_exception(inclusion, code):
    config = {
        "filters": [
            {
                "inclusion": inclusion,
                "filter_code": code,
            }
        ],
    }
    with pytest.raises(ValidationError) as e:
        TypeAdapter(TransformConfig).validate_python(config)

    assert e.value.error_count() == 1
    assert e.value.errors()[0]["msg"].startswith(
        f"Input tag '{code}' found using 'filter_code' does not match any of the expected tags:"
    )


def test_filter_on_nonexistent_column():
    config = {
        "name": "test_config",
        "reader": {
            "columns": ["a", "b", "c"],
        },
        "transform": {
            "filters": [
                {
                    "column": "a",
                    "inclusion": "include",
                    "filter_code": "gt",
                    "value": 0,
                },
                {
                    "column": "d",
                    "inclusion": "include",
                    "filter_code": "gt",
                    "value": 0,
                },
                {
                    "column": "e",
                    "inclusion": "include",
                    "filter_code": "gt",
                    "value": 0,
                },
            ],
        },
    }

    with pytest.raises(ValidationError) as e:
        TypeAdapter(KozaConfig).validate_python(config)

    assert e.value.error_count() == 1
    assert e.value.errors()[0]["msg"].startswith(
        f"Value error, One or more filter columns not present in designated CSV columns: 'd', 'e'"
    )
