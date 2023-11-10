# from pathlib import Path
from urllib.request import urlopen
import yaml

import pytest
from linkml.validator import validate

pytest.skip("validation tests are not working", allow_module_level=True)


valid_gene = {
    "id": "BOGUS:12345",
    "name": "Bogus Gene 12345",
    "category": ["biolink:NamedThing", "biolink:Gene"],
}
invalid_gene = {"name": "Bogus Gene 98765", "type": "biolink:NamedThing"}

# model_url = "https://raw.githubusercontent.com/biolink/biolink-model/latest/biolink-model.yaml"
model_url = "https://raw.githubusercontent.com/monarch-initiative/monarch-app/main/backend/src/monarch_py/datamodels/similarity.yaml"

with urlopen(model_url) as f:
    biolink_model = yaml.load(f, Loader=yaml.FullLoader)

@pytest.mark.parametrize("gene", [valid_gene])
def test_valid_input(gene):
    v = validate(instance=gene, target_class="gene", schema=model_url)
    result = v.results[0]
    print(result)
    assert result.valid == True


@pytest.mark.parametrize("gene", [invalid_gene])
def test_invalid_input(gene):
    v = validate(instance=gene, target_class="gene", schema=model_url)
    result = v.results[0]
    # assert result.valid == False
