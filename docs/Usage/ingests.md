# Ingests

<sub>
(For CLI usage, see the [CLI commands](./CLI.md) page.)
</sub>  

!!! tip "Ingest Overview"
    Koza is designed to process and transform existing data into a target csv/json/jsonl format.  

    This process is internally known as an **ingest**. Ingests are defined by:  

    - **Source config yaml**: Ingest configuration, including:
        -  metadata, formats, required columns, any SSSOM files, etc. 
    - **Map config yaml**: (Optional) configures creation of mapping dictionary  
    - **Transform code**: a Python script, with specific transform instructions 

-----

Let's say you have some data, and you want to save certain bits of that data,   
with maybe some changes or translations along the way.  
Creating this ingest will require three things: 

!!! list ""
    ## 1. Source Config File

    This YAML file sets properties for the ingest of a single file type from a within a Source.

    ???+ tip "Paths are relative to the directory from which you execute Koza."
    
    | __Required properties__ | | 
    | --- | --- |
    | `name` | Name of the source |
    | `files` | List of files to process |
    |||
    | __Optional properties__ | |
    | `file_archive` | Path to a file archive containing the files to process |
    | `format` | Format of the data file(s) (CSV or JSON) |
    | `sssom_config` | Configures usage of SSSOM mapping files |
    | `depends_on` | List of map config files to use |
    | `metadata` | Metadata for the source |
    | `transform_code` | Path to a python file to transform the data |
    | `transform_mode` | How to process the transform file |
    | `global_table` | Path to a global translation table file |
    | `local_table` | Path to a local translation table file |
    | `filters` | List of filters to apply |
    | `json_path` | Path within JSON object containing data to process |
    | `required_properties` | List of properties that must be present in output (JSON only) |
    |||
    | __Optional CSV Specific Properties__ | |
    | `columns` | List of columns to include in output (CSV only) |
    | `delimiter` | Delimiter for csv files |
    | `header_delimiter` | Delimiter for header in csv files |
    | `header` | Header row index for csv files |
    | `comment_char` | Comment character for csv files |
    | `skip_blank_lines` | Skip blank lines in csv files |
    
  
    ### Composing Configuration from Multiple Yaml Files

    The Koza yaml loader supports importing/including other yaml files with an `!include` tag.

    For example, if you had a file named `standard-columns.yaml`:
    ```yaml
    - 'column_1'
    - 'column_2'
    - 'column_3'
    - 'column_4' : 'int'
    ```

    Then in any ingests you wish to use these columns, you can simply `!include` them:
    ```yaml
    columns: !include './path/to/standard-columns.yaml'
    ```

!!! list ""
    ## 2. Mapping and Additional Data

    Mapping with Koza can be done in two ways:  

    - Automated mapping with SSSOM files  
    - Manual mapping with a map config yaml

    ### SSSOM Mapping

    Koza supports mapping with SSSOM files (Semantic Similarity of Source and Target Ontology Mappings).  
    Simply add the path to the SSSOM file to your source config, the desired target prefixes,  
    and any prefixes you want to use to filter the SSSOM file.  
    Koza will automatically create a mapping lookup table which will automatically  
    attempt to map any values in the source file to an ID with the target prefix.

    ```yaml
    sssom_config:
        sssom_file: './path/to/your_mapping_file.sssom.tsv'
        filter_prefixes: 
            - 'SOMEPREFIX'
            - 'OTHERPREFIX'
        target_prefixes: 
            - 'OTHERPREFIX'
        use_match:
            - 'exact'
    ```

    **Note:** Currently, only the `exact` match type is supported (`narrow` and `broad` match types will be added in the future).

    ### Manual Mapping / Additional Data

    The map config yaml allows you to include data from other sources in your ingests,  
    which may have different columns or formats.  
    
    If you don't have an SSSOM file, or you want to manually map some values, you can use a map config yaml.  
    You can then add this map to your source config yaml in the `depends_on` property.  
    
    Koza will then create a nested dictionary with the specified key and values.  
    For example, the following map config yaml maps values from the `STRING` column to the `entrez` and `NCBI taxid` columns.

    ```yaml
    # koza/examples/maps/entrez-2-string.yaml
    name: ...
    files: ...

    columns:
    - 'NCBI taxid'
    - 'entrez'
    - 'STRING'

    key: 'STRING'

    values:
    - 'entrez'
    - 'NCBI taxid'
    ```

     
    The mapping dict will be available in your transform script from the `koza_app` object (see the Transform Code section below).
    

!!! list ""     
    ## 3. Transform Code

    This Python script is where you'll define the specific steps of your data transformation. 
    Koza will load this script and execute it for each row of data in your source file,  
    applying any filters and mapping as defined in your source config yaml,  
    and outputting the transformed data to the target csv/json/jsonl file.

    When Koza is called, either by command-line or as a library using `transform_source()`,  
    it creates a `KozaApp` object for the specified ingest.  
    This KozaApp will be your entry point to Koza:

    ```python
    from koza.cli_runner import get_koza_app
    koza_app = get_koza_app('your-source-name')
    ```
  
    The KozaApp object has the following methods:

    | Method | Description |
    | --- | --- |
    | `get_row()` | Returns the next row of data from the source file |
    | `get_map(map_name)` | Returns the mapping dict for the specified map |
    | `get_global_table()` | Returns the global translation table |
    | `get_local_table()` | Returns the local translation table |

    ??? tldr "Example Python Transform Script"

        ```python
        # other imports, eg. uuid, pydantic, etc.
        import uuid
        from biolink.pydanticmodel import Gene, PairwiseGeneToGeneInteraction
        
        # Koza imports
        from koza.cli_runner import get_koza_app

        # This is the name of the ingest you want to run
        source_name = 'map-protein-links-detailed'
        koza_app = get_koza_app(source_name)
            
        # If your ingest depends_on a mapping file, you can access it like this:
        map_name = 'entrez-2-string'
        koza_map = koza_app.get_map(map_name)

        # This grabs the first/next row from the source data
        # Koza will reload this script and return the next row until it reaches EOF or row-limit
        row = koza_app.get_row()
        
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