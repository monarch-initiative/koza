import re


class CurieCleaner:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            print('Creating the object')
            cls._instance = super(CurieCleaner, cls).__new__(cls)
            # TODO: these belong in yaml, might already exist somewhere
            cls._instance.mappings = {"taxon": "NCBITaxon", "NCBI_Gene": "NCBIGene"}
        return cls._instance

    def clean(self, curie: str) -> str:
        for curie_synonym in self.mappings:
            curie = re.sub("^%s:" % curie_synonym, self.mappings[curie_synonym] + ":", curie)
        return curie
