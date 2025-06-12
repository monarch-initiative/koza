import re


class CurieCleaner:
    def __init__(self):
        self.mappings = {"taxon": "NCBITaxon", "NCBI_Gene": "NCBIGene"}

    def clean(self, curie: str) -> str:
        for curie_synonym in self.mappings:
            curie = re.sub(f"^{curie_synonym}:", self.mappings[curie_synonym] + ":", curie)
        return curie
