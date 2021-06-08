import re


class CurieCleaner:
    def __init__(self):
        # TODO: these belong in yaml, might already exist somewhere
        self.mappings = {"taxon": "NCBITaxon", "NCBI_Gene": "NCBIGene"}

    def clean(self, curie: str) -> str:
        for curie_synonym in self.mappings:
            curie = re.sub("^%s:" % curie_synonym, self.mappings[curie_synonym] + ":", curie)
        return curie
