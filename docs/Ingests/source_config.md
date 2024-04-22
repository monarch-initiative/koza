This YAML file sets properties for the ingest of a single file type from a within a Source.

!!! tip "Paths are relative to the directory from which you execute Koza."

## Source Configuration Properties

| **Required properties**     |                                                                                                     |
| --------------------------- | --------------------------------------------------------------------------------------------------- |
| `name`                      | Name of the data ingest, as `<data source>_<type_of_ingest>`, <br/>ex. `hpoa_gene_to_disease`       |
| `files`                     | List of files to process                                                                            |
|                             |                                                                                                     |
| **Optional properties**     |                                                                                                     |
| `file_archive`              | Path to a file archive containing the file(s) to process <br/> Supported archive formats: zip, gzip |
| `format`                    | Format of the data file(s) (CSV or JSON)                                                            |
| `sssom_config`              | Configures usage of SSSOM mapping files                                                             |
| `depends_on`                | List of map config files to use                                                                     |
| `metadata`                  | Metadata for the source, either a list of properties,<br/>or path to a `metadata.yaml`              |
| `transform_code`            | Path to a python file to transform the data                                                         |
| `transform_mode`            | How to process the transform file                                                                   |
| `global_table`              | Path to a global translation table file                                                             |
| `local_table`               | Path to a local translation table file                                                              |
| `field_type_map`            | Dict of field names and their type (using the FieldType enum)                                       |
| `filters`                   | List of filters to apply                                                                            |
| `json_path`                 | Path within JSON object containing data to process                                                  |
| `required_properties`       | List of properties that must be present in output (JSON only)                                       |
|                             |                                                                                                     |
| **CSV-Specific Properties** |                                                                                                     |
| `delimiter`                 | Delimiter for csv files (**Required for CSV format**)                                               |
| **Optional CSV Properties** |                                                                                                     |
| `columns`                   | List of columns to include in output (CSV only)                                                     |
| `header`                    | Header row index for csv files                                                                      |
| `header_delimiter`          | Delimiter for header in csv files                                                                   |
| `header_prefix`             | Prefix for header in csv files                                                                      |
| `comment_char`              | Comment character for csv files                                                                     |
| `skip_blank_lines`          | Skip blank lines in csv files                                                                       |

## Metadata Properties

Metadata is optional, and can be defined as a list of properties and values, or as a path to a `metadata.yaml` file,
for example - `metadata: "./path/to/metadata.yaml"`.  
Remember that the path is relative to the directory from which you execute Koza.

| **Metadata Properties** |                                                                                          |
| ----------------------- | ---------------------------------------------------------------------------------------- |
| name                    | Name of data source, ex. "FlyBase"                                                       |
| description             | Description of data/ingest                                                               |
| ingest_title            | \*Title of source of data, map to biolink name                                           |
| ingest_url              | \*URL to source of data, Maps to biolink iri                                             |
| provided_by             | `<data source>_<type_of_ingest>`, ex. `hpoa_gene_to_disease` (see config propery "name") |
| rights                  | Link to license information for the data source                                          |

**\*Note**: For more information on `ingest_title` and `ingest_url`, see the [infores catalog](https://biolink.github.io/information-resource-registry/infores_catalog.yaml)

## Composing Configuration from Multiple Yaml Files

Koza's custom YAML Loader supports importing/including other yaml files with an `!include` tag.

For example, if you had a file named `standard-columns.yaml`:

```yaml
- "column_1"
- "column_2"
- "column_3"
- "column_4": "int"
```

Then in any ingests you wish to use these columns, you can simply `!include` them:

```yaml
columns: !include "./path/to/standard-columns.yaml"
```

---

**Next Steps: [Mapping and Additional Data](./mapping.md)**
