# import pytest
# from linkml_validator.validator import Validator

# valid_gene = {
#     "id": "BOGUS:12345",
#     "name": "Bogus Gene 12345",
#     "category": ["biolink:NamedThing", "biolink:Gene"],
# }

# invalid_gene = {"name": "Bogus Gene 98765", "type": "biolink:NamedThing"}

# model_url = "https://raw.githubusercontent.com/biolink/biolink-model/latest/biolink-model.yaml"
# validator = Validator(schema=model_url)
# # model_schema = Path(__file__).parent.parent / 'resources' / 'biolink-model.yaml'
# # validator = Validator(schema="tests/resources/biolink-model.yaml")


# @pytest.mark.parametrize("gene", [valid_gene])
# def test_valid_input(gene):
#     v = validator.validate(obj=gene, target_class="Gene")
#     result = v.validation_results[0]
#     assert result.valid == True


# @pytest.mark.parametrize("gene", [invalid_gene])
# def test_invalid_input(gene):
#     v = validator.validate(obj=gene, target_class="Gene")
#     result = v.validation_results[0]
#     assert result.valid == False
