from pathlib import Path

import pytest
from linkml_validator.validator import Validator

valid_gene = {
    "id": "BOGUS:12345",
    "name": "Bogus Gene 12345",
    "category": ["biolink:NamedThing", "biolink:Gene"],
}

invalid_gene = {"name": "Bogus Gene 98765", "type": "biolink:NamedThing"}

model_schema = Path(__file__).parent.parent / 'resources' / 'biolink-model.yaml'


@pytest.mark.parametrize("gene", [valid_gene])
def test_valid_input(gene):
    validator = Validator(schema="tests/resources/biolink-model.yaml")
    v = validator.validate(obj=gene, target_class="NamedThing")
    result = v.validation_results[0]
    assert result.valid == True


@pytest.mark.parametrize("gene", [invalid_gene])
def test_invalid_input(gene):
    validator = Validator(schema="tests/resources/biolink-model.yaml")
    v = validator.validate(obj=gene, target_class="NamedThing")
    result = v.validation_results[0]
    assert result.valid == False
