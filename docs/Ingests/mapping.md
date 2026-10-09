
Mapping with Koza is optional, but can be done in two ways:  

- Automated mapping with SSSOM files  
- Manual mapping with a map config yaml

### SSSOM Mapping

Koza supports mapping with SSSOM files (Semantic Similarity of Source and Target Ontology Mappings).
SSSOM mapping can be applied to any field in your data (subject, object, predicate, category, etc.)
with flexible file organization and preservation control.

#### Basic Configuration

```yaml
sssom_config:
  files:
    - './path/to/shared_mappings.sssom.tsv'
  filter_prefixes:
    - 'DOID'        # Only use SSSOM rows with DOID subjects/objects, only map DOID IDs from source
    - 'OMIM'        # Only use SSSOM rows with OMIM subjects/objects, only map OMIM IDs from source
  field_mappings:
    subject:
      target_prefixes: ['MONDO', 'HP']    # Map TO these prefixes
      preserve_original: true
    object:
      target_prefixes: ['CHEBI']          # Map TO this prefix
      preserve_original: false
  use_match:
    - 'exact'
```

#### Advanced Configuration with Per-Field Files

You can specify different SSSOM files for different fields, allowing for specialized mappings:

**Understanding filter_prefixes vs target_prefixes:**
- `filter_prefixes`: Controls which SSSOM file content to use and which source IDs to consider
- `target_prefixes`: Controls what prefixes to map TO for each field

Example: If your SSSOM file contains mappings like `DOID:123 → MONDO:456`, `HP:789 → MONDO:999`, `OMIM:111 → CHEBI:222`

```yaml
sssom_config:
  # Optional global files applied to all fields
  files:
    - './shared_mappings.sssom.tsv'
  filter_prefixes: ['DOID', 'HP']  # Only use DOID/HP rows from SSSOM, ignore OMIM→CHEBI
  field_mappings:
    subject:
      files: ['./subject_specific.sssom.tsv']  # Additional files for this field
      target_prefixes: ['MONDO', 'HP']
      preserve_original: true
      original_field_name: 'original_subject'  # Optional: custom field name
    object:
      target_prefixes: ['CHEBI']  # Uses only global files
      preserve_original: false
    predicate:
      files: ['./predicate_mappings.sssom.tsv']  # Field-specific only
      target_prefixes: ['RO']
      preserve_original: true
      original_field_name: 'source_predicate'  # Custom preservation field
    category:
      target_prefixes: ['BIOLINK']
      preserve_original: true
  use_match:
    - 'exact'
```

#### Global Files Only

```yaml
sssom_config:
  files:
    - './all_mappings.sssom.tsv'
    - './additional_mappings.sssom.tsv'
  field_mappings:
    subject:
      target_prefixes: ['MONDO']
      preserve_original: true
    object:
      target_prefixes: ['CHEBI']
      preserve_original: false
```

#### Per-Field Files Only

```yaml
sssom_config:
  # No global files
  field_mappings:
    subject:
      files: ['./subject_mappings.sssom.tsv']
      target_prefixes: ['MONDO']
      preserve_original: true
    object:
      files: ['./object_mappings.sssom.tsv']
      target_prefixes: ['CHEBI']
      preserve_original: false
```

#### Configuration Options

- **files**: (Optional) Global SSSOM files applied to all field mappings
- **field_mappings**: Dictionary defining mapping behavior per field
  - **files**: (Optional) Field-specific SSSOM files (merged with global files)
  - **target_prefixes**: List of prefixes to map TO for this field
  - **preserve_original**: Boolean - whether to preserve the original value
  - **original_field_name**: (Optional) Custom name for the preservation field
- **filter_prefixes**: List of prefixes to filter SSSOM file content and source data for mapping (dual-level inclusion filter)
  - **SSSOM content filtering**: Only keeps rows from SSSOM files where subject_id or object_id match these prefixes
  - **Source data filtering**: Only considers source data IDs with these prefixes for mapping
  - Example: If SSSOM contains `DOID→MONDO`, `HP→MONDO`, `OMIM→CHEBI` and `filter_prefixes: ['DOID', 'HP']`, then only the first two mappings are used and only `DOID:123`/`HP:456` IDs from source data will be mapped
  - If empty, all SSSOM content and source prefixes are considered
- **use_match**: Match types to use (currently only 'exact' is supported)

#### Validation Rules

- At least one SSSOM file must be specified (either globally or in field_mappings)
- Each field uses the combination of global files + field-specific files
- If `preserve_original: true`, the original value is stored in `original_{field_name}` (or custom name)
- Field-specific files are merged with global files for that field's mappings

#### Backward Compatibility

The following legacy configurations are still supported but deprecated:

```yaml
# DEPRECATED - use field_mappings instead
sssom_config:
  files: ['./mappings.sssom.tsv']
  subject_target_prefixes: ['MONDO']  # Use field_mappings.subject.target_prefixes
  object_target_prefixes: ['CHEBI']   # Use field_mappings.object.target_prefixes
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