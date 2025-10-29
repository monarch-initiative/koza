import koza
from biolink_model.datamodel.pydanticmodel_v2 import Gene


@koza.transform_record()
def transform_record(koza_transform, row):
    # This transform expects the column 'species_A'
    gene = Gene(
        id=row['gene_id'],
        in_taxon=[row['species_A']],  # Uses species_A column
        provided_by=["infores:test_source_a"],
    )
    return [gene]
