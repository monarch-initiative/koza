This Python script is where you'll define the specific steps of your data transformation.
Koza will load this script and execute it for each row of data in your source file,  
applying any filters and mapping as defined in your source config yaml,  
and outputting the transformed data to the target csv/json/jsonl file.

When Koza is called, either by command-line or as a library,  
it creates a `KozaTransform` object for the specified ingest.  
This KozaTransform will be your entry point to Koza and is available as a global variable in your transform code.

The KozaTransform object has the following methods which can be used in your transform code:

| Method              | Description                                       |
| ------------------- | ------------------------------------------------- |
| `write(*args)`      | Writes the transformed data to the target file    |

Your transform code should define functions decorated with Koza decorators that process the data:

Once you have processed a row of data, and created a biolink entity node or edge object (or both),  
you can pass these to `koza.write()` to output the transformed data to the target file.

??? tldr "Example Python Transform Script"

    ```python
    import re
    import uuid
    from typing import Any
    from biolink_model.datamodel.pydanticmodel_v2 import PairwiseGeneToGeneInteraction, Protein

    import koza

    @koza.transform_record()
    def transform_record(koza: koza.KozaTransform, record: dict[str, Any]):
        # Process the record data
        protein_a = Protein(id="ENSEMBL:" + re.sub(r"\d+\.", "", record["protein1"]))
        protein_b = Protein(id="ENSEMBL:" + re.sub(r"\d+\.", "", record["protein2"]))

        # Create interaction
        pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
            id="uuid:" + str(uuid.uuid1()),
            subject=protein_a.id,
            object=protein_b.id,
            predicate="biolink:interacts_with",
            knowledge_level="not_provided",
            agent_type="not_provided",
        )

        # Write the transformed data
        koza.write(protein_a, protein_b, pairwise_gene_to_gene_interaction)
    ```

    The `@koza.transform_record()` decorator indicates that this function processes individual records.
    If you pass nodes as well as edges to `koza.write()`, Koza will automatically create a node file and an edge file.
    If you pass only nodes, Koza will create only a node file, and if you pass only edges, Koza will create only an edge file.
