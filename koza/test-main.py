# test

from glom import glom, Path
import json

from koza.io.reader.csv_reader import CSVReader
from koza.io.utils import open_resource

foo = "https://raw.githubusercontent.com/monarch-initiative/koza/dev/tests/resources/source-files/string.tsv"
# foo = "https://github.com/monarch-initiative/koza/raw/dev/tests/resources/source-files/ZFIN_PHENOTYPE_0.jsonl.gz"

small_ontology = "https://raw.githubusercontent.com/obophenotype/dicty-phenotype-ontology/master/ddpheno.json"
#with open_resource(foo) as bar:
#    reader = CSVReader(bar, delimiter=' ')
#    for row in reader:
#        print(row)


with open_resource(small_ontology) as small:
    doc = json.load(small)
    print(doc)
    print(glom(doc, Path(*[])))
    print(glom(doc, Path(*['graphs', 0])))
