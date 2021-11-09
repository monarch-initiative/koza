## Ingest Configuration

Ingests are configured via a single source file yaml, and optional mapping file yaml(s)

### Source File(s)

This YAML file sets properties for the ingest of a single file type from a within a Source.

Tip: relative paths are relative to the directory where you execute Koza.

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

### Map File(s)

This YAML file sets properties for creating a dictionary that an ingest depends on.
It contains the same options as a source file, excluding depends_on, node_properties,
edge_properties, and on_map_failure.  It adds the following options:

```yaml
# The column name in which to get the key for the dictionary
key: someKey

# The column(s) in which to store as values for the key
values:
  - value1
  - value2
```

### Composing Configuration from Multiple Yaml Files

The Koza yaml loader supports importing/including other yaml files via an !include tag.
To reuse fields that appear in multiple ingests, such as metadata and columns:

```yaml
metadata: !include './path/to/metadata.yaml'
columns: !include './path/to/standard-columns.yaml'
```

For example, a standard column file will be formatted as a yaml list, i.e. the parent key is omitted:

```yaml
- 'column_1'
- 'column_2'
- 'column_3'
- 'column_4' : 'int'
```

Tip: '!include' tags must be values in a yaml file
