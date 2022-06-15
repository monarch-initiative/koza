## Ingests

An **ingest** is the process of using Koza to process and transform existing data into a target csv/json/jsonl format.  

Ingests are defined by:  

- **Source config yaml**: specifies metadata, formats, required columns, etc. for the ingest
- **Map config yaml**: (Optional) configures creation of mapping dictionary 
- **Transform code**: a Python script, with specific transform instructions

--

Now, let's say you have some data, and you want to save certain bits of that data, with maybe some changes or translations along the way.  

Let's look at what we'll need to make that ingest: 

### Source Config File

This YAML file sets properties for the ingest of a single file type from a within a Source.

Available properties are listed in Koza's <a href="https://github.com/monarch-initiative/koza/blob/main/koza/model/config/source_config.py#L148" target="_blank">SourceConfig()</a> and <a href="https://github.com/monarch-initiative/koza/blob/main/koza/model/config/source_config.py#L324" target="_blank">PrimarySourceConfig()</a> classes.

???+ tip 
    Relative paths are relative to the directory where you execute Koza.

??? tldr "Example Source Config YAML"

    ```yaml
    name: 'name-of-ingest'

    format: 'json' # Options are json or csv, default is csv

    # Sets file compression, options are gzip and none, default is none
    compression: 'gzip'

    # list of files to be ingested
    files:
    - './data/really-cool-data-1.json.gz'
    - './data/really-cool-data-2.json.gz'

    # The dataset description
    metadata:
    description: 'SomethingBase: A Website With Some Data'
    rights: 'https://somethingbase.org/rights.html'

    # The local and global tables can be specified either in the command line or the config
    global_table: './path_to/translation_table.yaml'
    local_table: './somethingbase/something-translation.yaml'

    # in addition to specifying yaml files, it's also possible to define the tables inline
    # local_table: 
    #   "around here somewhere": "RO:9999999"


    # in a JSON ingest, this will be the path to the array to be iterated over as the input collection
    json_path:
    - 'data'

    # Ordered list of columns for CSV files, data type can be specified as float, int or str
    columns:
    - 'protein1'
    - 'protein2'
    - 'combined_score' : 'int'

    # Specify a delimiter for CSV files, default is a comma
    delimiter: '\t'

    # Optional delimiter for header row
    header_delimiter: '|' 

    # Optional, int | 'infer' | 'none', Default = 'infer'
    # The index (0 based) in which the header appears in the file.
    #
    # If header is set to 'infer' the headers will be set to the first
    # line that is not blank or commented with a hash.
    #
    # If header is set to 'none' then the columns field will be used,
    # or raise a ValueError if columns are not supplied
    header: 0

    # Boolean to skip blank lines, default is true
    skip_blank_lines: True

    # include a map file
    depends_on:
    - './examples/maps/alliance-gene.yaml'

    # The filter DSL allows including or excluding rows based on filter blocks
    filters: 
    - inclusion: 'include' # 'include' to include rows matching, 'exclude' to exclude rows that match
        column: 'combined_score'
        # filter_code  (with 'in' expecting a list of values)
        filter_code: 'lt' # options: 'gt', 'ge', 'lt', 'le', 'eq', 'ne', 'in'  
        value: 700
    - inclusion: 'exclude'
        column: 'protein1'
        filter_code: 'in' # 'in' expects the value to be a list and checks that the column value is matched within the list
        value: 
        - 'ABC1'
        - 'XYZ4'

    # node and edge categories are required to avoid empty KGX files, the order here isn't important  
    node_properties:
    - 'id'
    - 'category'
    - 'provided_by'

    edge_properties:
    - 'id'
    - 'subject'
    - 'predicate'
    - ...

    #In 'flat' mode, the transform operates on a single row and looping doesn't need to be specified
    #In 'loop' mode, the transform code is executed only once and so the loop code that iterates over rows must be contained within the transform code
    # The default is 'flat'
    transform_mode: 'loop'

    # Python code to run for ingest. Default is the same file name as the source_file yaml, but with a .py extension
    # You probably don't need to set this property
    transform_code: 'name-of-ingest.py'
    ```

**Composing Configuration from Multiple Yaml Files**

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
metadata: !include './path/to/metadata.yaml'
columns: !include './path/to/standard-columns.yaml'
```

### Map File(s)

This YAML file sets properties for creating a mapping dictionary that an ingest may depend on.

Available properties are listed in Koza's <a href="https://github.com/monarch-initiative/koza/blob/main/koza/model/config/source_config.py#L148" target="_blank">SourceConfig()</a> and <a href="https://github.com/monarch-initiative/koza/blob/main/koza/model/config/source_config.py#L311" target="_blank">MapFileConfig()</a> classes.

??? tldr "Example Map Config YAML"

    ```yaml
    name: 'genepage-2-gene'
    metadata:
        description: 'Mapping file provided by Xenbase that maps from GENEPAGE to GENE'

    delimiter: '\t'

    files:
        - './examples/data/XenbaseGenepageToGeneIdMapping.txt'

    columns:
        - 'gene_page_id'
        - 'gene_page_label'
        - 'tropicalis_id'
        - 'tropicalis_label'
        - 'laevis_l_id'
        - 'laevis_l_label'
        - 'laevis_s_id'
        - 'laevis_s_label'

    # The column to save as a key in the map dictionary
    key: 'gene_page_id'

    # The column(s) to save as nested keys under 'key'
    values:
        - 'tropicalis_id'
        - 'laevis_l_id'
        - 'laevis_s_id'
    ```

    This example map yields a map dictionary: 

    ```json
    {
        gene_page_id: {
            tropicalis_id: somevalue1, 
            laevis_l_id: somevalue2,
            laevis_s_id: somevalue3
        }
    }
    ```
    
### Transform Code

This Python script is where you'll define the specific steps of your data transformation. 

???+ tip

    When Koza is called (either by command-line or as a library using `transform_source()`),  
    it creates a `KozaApp` for the ingest it was called to transform.  
    This KozaApp will be your entry point to Koza.


??? tldr "Example Python Transform Script"

    ```python
    import uuid
    from biolink_model_pydantic.model import Gene, PairwiseGeneToGeneInteraction

    # Get the KozaApp for your ingest
    from koza.cli_runner import get_koza_app
    source_name = 'map-protein-links-detailed'
    koza_app = get_koza_app(source_name)
        
    # If your ingest depends on a map
    map_name = 'entrez-2-string'
    koza_map = koza_app.get_map(map_name)

    # This grabs the first/next row from the source data
    # Koza will reload this script and return the next row until it reaches EOF or row-limit
    row = koza_app.get_row()
    
    # Now you can lay out your actual transformations, and define your output

    gene_a = Gene(id='NCBIGene:' + koza_map[row['protein1']]['entrez'])
    gene_b = Gene(id='NCBIGene:' + koza_map[row['protein2']]['entrez'])

    pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
        id="uuid:" + str(uuid.uuid1()),
        subject=gene_a.id,
        object=gene_b.id,
        predicate="biolink:interacts_with"
    )

    koza_app.write(gene_a, gene_b, pairwise_gene_to_gene_interaction)
    ```