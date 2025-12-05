import koza
from biolink_model.datamodel.pydanticmodel_v2 import Gene


@koza.transform_record()
def transform_record(koza_transform, row):
    # This transform expects the column 'species_B'
    gene = Gene(
        id=row['gene_id'],
        in_taxon=[row['species_B']],  # Uses species_B column (different!)
        provided_by=["infores:test_source_b"],
    )
    return [gene]
