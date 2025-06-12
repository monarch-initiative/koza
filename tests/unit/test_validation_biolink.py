from urllib.request import urlopen

import pytest
import yaml
from linkml.validator import validate

pytest.skip("LinkML issue with `category` slot has `designates_type: true`", allow_module_level=True)

model_url = "https://raw.githubusercontent.com/biolink/biolink-model/latest/biolink-model.yaml"
with urlopen(model_url) as f:  # noqa: S310
    model = yaml.load(f, Loader=yaml.FullLoader)  # noqa: S506

valid_input = {
    "id": "BOGUS:12345",
    "name": "Bogus Gene 12345",
    "category": ["biolink:NamedThing", "biolink:Gene"],
}
invalid_input = {"name": "Bogus Gene 98765", "type": "biolink:NamedThing"}


@pytest.mark.parametrize("gene", [valid_input])
def test_valid_input(gene):
    v = validate(instance=gene, target_class="gene", schema=model)
    assert len(v.results) == 0


@pytest.mark.parametrize("gene", [invalid_input])
def test_invalid_input(gene):
    v = validate(instance=gene, target_class="gene", schema=model)
    assert v.results[0].severity == "ERROR"
