
Mapping with Koza is optional, but can be done in two ways:  

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

---

**Next Steps: [Transform Code](./transform.md)**