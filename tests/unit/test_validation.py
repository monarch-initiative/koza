from pathlib import Path
import yaml

import pytest
from linkml.validator import validate

# pytest.skip("validation tests are not working", allow_module_level=True)


###################################################################################################
# Monarch model test

valid_input = {
    "id": "BOGUS:12345",
    "name": "Bogus Gene 12345",
    "category": "biolink:Gene",
}
invalid_input = {"name": "Bogus Gene 98765", "type": "biolink:NamedThing"}

model_path  = Path(__file__).parent.parent / 'resources' / 'test-model.yaml'
with open(model_path) as f:    
    model = yaml.load(f, Loader=yaml.FullLoader)    

@pytest.mark.parametrize("entity", [valid_input])
def test_valid_input(entity):
    v = validate(instance=entity, target_class="Entity", schema=model)
    assert len(v.results) == 0


@pytest.mark.parametrize("entity", [invalid_input])
def test_invalid_input(entity):
    v = validate(instance=entity, target_class="Entity", schema=model)
    assert v.results[0].severity == "ERROR"

###################################################################################################
# Generic model test


# model_path  = Path(__file__).parent.parent / 'resources' / 'test-model.yaml'
# with open(model_path) as f:    
#     model = yaml.load(f, Loader=yaml.FullLoader)    

# valid_input = {
#     "id": "BOGUS:12345",
#     "name": "Bogus Thing 12345",
#     "type": "X"
# }

# invalid_input = {
#     "id": "BOGUS:987654",
#     "name": "Bogus Thing 987654",
#     "type": "A"
# }

# @pytest.mark.parametrize("entity", [valid_input])
# def test_valid_input(entity):
#     v = validate(instance=entity, target_class="named thing", schema=model)
#     print(f"v: {v}")
#     assert len(v.results) == 0


# @pytest.mark.parametrize("entity", [invalid_input])
# def test_invalid_input(entity):
#     v = validate(instance=entity, target_class="named thing", schema=model)
#     print(f"v: {v}")
#     result = v.results[0]
#     print(f"result: {result}")
#     assert 1 == 2
#     assert result.severity == "ERROR"