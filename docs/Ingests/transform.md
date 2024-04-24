This Python script is where you'll define the specific steps of your data transformation.
Koza will load this script and execute it for each row of data in your source file,  
applying any filters and mapping as defined in your source config yaml,  
and outputting the transformed data to the target csv/json/jsonl file.

When Koza is called, either by command-line or as a library using `transform_source()`,  
it creates a `KozaApp` object for the specified ingest.  
This KozaApp will be your entry point to Koza:

```python
from koza.cli_utils import get_koza_app
koza_app = get_koza_app('your-source-name')
```

The KozaApp object has the following methods which can be used in your transform code:

| Method              | Description                                       |
| ------------------- | ------------------------------------------------- |
| `get_row()`         | Returns the next row of data from the source file |
| `next_row()`        | Skip to the next row in the data file             |
| `get_map(map_name)` | Returns the mapping dict for the specified map    |
| `process_sources()` | TBD                                               |
| `process_maps()`    | Initializes the KozaApp's map cache               |
| `write(*args)`      | Writes the transformed data to the target file    |

Once you have processed a row of data, and created a biolink entity node or edge object (or both),  
you can pass these to `koza_app.write()` to output the transformed data to the target file.

??? tldr "Example Python Transform Script"

    ```python
    # other imports, eg. uuid, pydantic, etc.
    import uuid
    from biolink_model.datamodel.pydanticmodel_v2 import Gene, PairwiseGeneToGeneInteraction

    # Koza imports
    from koza.cli_utils import get_koza_app

    # This is the name of the ingest you want to run
    source_name = 'map-protein-links-detailed'
    koza_app = get_koza_app(source_name)

    # If your ingest depends_on a mapping file, you can access it like this:
    map_name = 'entrez-2-string'
    koza_map = koza_app.get_map(map_name)

    # This grabs the first/next row from the source data
    # Koza will reload this script and return the next row until it reaches EOF or row-limit
    while (row := koza_app.get_row()) is not None:
        # Now you can lay out your actual transformations, and define your output:

        gene_a = Gene(id='NCBIGene:' + koza_map[row['protein1']]['entrez'])
        gene_b = Gene(id='NCBIGene:' + koza_map[row['protein2']]['entrez'])

        pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
            id="uuid:" + str(uuid.uuid1()),
            subject=gene_a.id,
            object=gene_b.id,
            predicate="biolink:interacts_with"
        )

        # Finally, write the transformed row to the target file
        koza_app.write(gene_a, gene_b, pairwise_gene_to_gene_interaction)
    ```

    If you pass nodes, as well as edges, to `koza_app.write()`, Koza will automatically create a node file and an edge file.
    If you pass only nodes, Koza will create only a node file, and if you pass only edges, Koza will create only an edge file.
