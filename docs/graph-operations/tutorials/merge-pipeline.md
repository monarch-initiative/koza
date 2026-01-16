# Complete Merge Workflow

Master the full graph merge pipeline by combining data from multiple sources with different identifier schemes.

> **Note**: If running from a source checkout, use `uv run koza` instead of `koza`. If installed via pip, use `koza` directly.

## What You'll Learn

- Prepare input files from multiple sources
- Create SSSOM mapping files for identifier harmonization
- Run the complete merge pipeline
- Customize pipeline steps for your use case
- Troubleshoot common issues

## Prerequisites

- Completed the "Build Your First Graph" tutorial
- Understanding of KGX format (nodes and edges as TSV/JSONL/Parquet)
- Basic familiarity with identifier namespaces (e.g., HGNC, OMIM, MONDO)

## Scenario

You are building a knowledge graph that integrates data from three sources:

1. **HGNC genes**: Gene nodes with HGNC identifiers
2. **OMIM diseases**: Disease nodes with OMIM identifiers
3. **Gene-disease associations**: Edges connecting genes to diseases, but using MONDO identifiers for diseases

The challenge: Your edges reference MONDO disease IDs, but your disease nodes use OMIM IDs. Without normalization, these edges would be "dangling" (referencing nodes that do not exist in your graph).

The solution: Use SSSOM mappings to normalize OMIM identifiers to MONDO, allowing edges to connect properly to your disease nodes.

## Sample Data

Create a working directory and add these sample files.

### Source 1: Gene Nodes (genes_nodes.tsv)

```tsv
id	name	category	provided_by
HGNC:1100	BRCA1	biolink:Gene	hgnc
HGNC:1101	BRCA2	biolink:Gene	hgnc
HGNC:7989	TP53	biolink:Gene	hgnc
HGNC:3689	CFTR	biolink:Gene	hgnc
```

### Source 2: Disease Nodes (diseases_nodes.tsv)

```tsv
id	name	category	provided_by
OMIM:114480	Breast Cancer	biolink:Disease	omim
OMIM:219700	Cystic Fibrosis	biolink:Disease	omim
OMIM:151623	Li-Fraumeni Syndrome	biolink:Disease	omim
```

### Source 3: Gene-Disease Edges (associations_edges.tsv)

Note: These edges use MONDO identifiers for diseases (not OMIM).

```tsv
id	subject	predicate	object	primary_knowledge_source	provided_by
uuid:1	HGNC:1100	biolink:gene_associated_with_condition	MONDO:0007254	infores:monarch	associations
uuid:2	HGNC:1101	biolink:gene_associated_with_condition	MONDO:0007254	infores:monarch	associations
uuid:3	HGNC:7989	biolink:gene_associated_with_condition	MONDO:0007903	infores:monarch	associations
uuid:4	HGNC:3689	biolink:gene_associated_with_condition	MONDO:0009061	infores:monarch	associations
```

### Mapping File (mondo_omim.sssom.tsv)

This SSSOM file maps OMIM identifiers (object_id) to their equivalent MONDO identifiers (subject_id).

```tsv
#curie_map:
#  MONDO: http://purl.obolibrary.org/obo/MONDO_
#  OMIM: https://omim.org/entry/
#mapping_set_id: https://example.org/mappings/mondo-omim
subject_id	predicate_id	object_id	mapping_justification
MONDO:0007254	skos:exactMatch	OMIM:114480	semapv:ManualMappingCuration
MONDO:0009061	skos:exactMatch	OMIM:219700	semapv:ManualMappingCuration
MONDO:0007903	skos:exactMatch	OMIM:151623	semapv:ManualMappingCuration
```

## Step 1: Prepare Input Files

First, let's understand what each file contributes and verify they exist.

### Examine the Input Files

```bash
# Check file contents
head -5 genes_nodes.tsv
head -5 diseases_nodes.tsv
head -5 associations_edges.tsv
head -10 mondo_omim.sssom.tsv
```

### Understanding the ID Mismatch Problem

Look at the edge file - it references MONDO identifiers:

```bash
# See what disease IDs the edges reference
cut -f4 associations_edges.tsv | tail -n +2 | sort -u
```

Output:
```
MONDO:0007254
MONDO:0007903
MONDO:0009061
```

But the disease nodes use OMIM identifiers:

```bash
# See what IDs the disease nodes have
cut -f1 diseases_nodes.tsv | tail -n +2
```

Output:
```
OMIM:114480
OMIM:219700
OMIM:151623
```

Without normalization, all four edges would be dangling because `MONDO:0007254` does not match `OMIM:114480`, even though they represent the same disease.

## Step 2: Create SSSOM Mappings

The SSSOM (Simple Standard for Sharing Ontological Mappings) file defines how identifiers map to each other.

### SSSOM File Structure

An SSSOM file has two parts:

1. **Header** (optional): YAML metadata starting with `#`
2. **Data**: Tab-separated mappings

```tsv
#curie_map:
#  MONDO: http://purl.obolibrary.org/obo/MONDO_
#  OMIM: https://omim.org/entry/
#mapping_set_id: https://example.org/mappings/mondo-omim
subject_id	predicate_id	object_id	mapping_justification
MONDO:0007254	skos:exactMatch	OMIM:114480	semapv:ManualMappingCuration
```

### Key Columns for Normalization

| Column | Purpose | Direction |
|--------|---------|-----------|
| `subject_id` | Target identifier (normalize TO this) | Output |
| `object_id` | Source identifier (normalize FROM this) | Input |
| `predicate_id` | Relationship type | Metadata |
| `mapping_justification` | How mapping was determined | Metadata |

During normalization, Koza replaces `object_id` values in your edges with the corresponding `subject_id` values.

### Finding SSSOM Mappings

For real projects, you can obtain SSSOM mappings from:

- [Mondo disease ontology mappings](https://mondo.monarchinitiative.org/)
- [OBO Foundry ontologies](http://obofoundry.org/)
- [SSSOM-Py tools](https://github.com/mapping-commons/sssom-py) for creating your own
- Biomedical identifier registries

## Step 3: Run the Merge Pipeline

Now run the complete merge pipeline with a single command.

### Basic Merge Command

```bash
koza merge \
  -n genes_nodes.tsv \
  -n diseases_nodes.tsv \
  -e associations_edges.tsv \
  -m mondo_omim.sssom.tsv \
  -o merged_graph.duckdb
```

### Understanding the Command Options

| Option | Purpose |
|--------|---------|
| `-n`, `--nodes` | Node files to load (use `-n` multiple times for multiple files) |
| `-e`, `--edges` | Edge files to load (use `-e` multiple times for multiple files) |
| `-m`, `--mappings` | SSSOM mapping files for normalization |
| `-o`, `--output` | Output DuckDB database file |

### Expected Output

```
Starting merge pipeline...
Pipeline: join -> normalize -> prune
Output database: merged_graph.duckdb
Step 1: Join - Loading input files...
Join completed: 3 files | 7 nodes | 4 edges
Step 2: Normalize - Applying SSSOM mappings...
Normalize completed: 1 mapping files | 3 edge references normalized
Step 3: Prune - Cleaning graph structure...
Prune completed: 0 dangling edges moved | 0 singleton nodes handled
Merge pipeline completed successfully!
```

## Step 4: Understand the Output

Let's examine what happened at each pipeline step.

### Pipeline Steps Explained

1. **Join**: Loaded all node and edge files into a unified database
2. **Normalize**: Applied SSSOM mappings to convert OMIM IDs to MONDO IDs in edge references
3. **Prune**: Removed dangling edges and handled singleton nodes

### Verify Normalization Worked

Check that edge references were normalized. Normalization updates the `subject` and `object` columns in the edges table, preserving the original values in `original_subject` and `original_object`:

```bash
duckdb merged_graph.duckdb -c "
  SELECT subject, object, original_subject, original_object
  FROM edges
  WHERE original_object IS NOT NULL
"
```

Expected output:
```
subject   | object        | original_subject | original_object
----------+---------------+------------------+----------------
HGNC:1100 | MONDO:0007254 | NULL             | OMIM:114480
HGNC:1101 | MONDO:0007254 | NULL             | OMIM:114480
HGNC:7989 | MONDO:0007903 | NULL             | OMIM:151623
HGNC:3689 | MONDO:0009061 | NULL             | OMIM:219700
```

The `original_subject` and `original_object` columns preserve the original identifiers for provenance. Note that in this example, the edge objects were normalized from OMIM to MONDO IDs, so `original_object` contains the original OMIM ID while `object` now contains the MONDO equivalent.

### Verify Edges Connect Properly

```bash
duckdb merged_graph.duckdb -c "
  SELECT
    e.subject,
    n1.name as subject_name,
    e.object,
    n2.name as object_name
  FROM edges e
  JOIN nodes n1 ON e.subject = n1.id
  JOIN nodes n2 ON e.object = n2.id
"
```

All edges should now join successfully to nodes.

### Check for Dangling Edges

```bash
duckdb merged_graph.duckdb -c "
  SELECT COUNT(*) as dangling_count
  FROM edges e
  WHERE NOT EXISTS (SELECT 1 FROM nodes n WHERE n.id = e.subject)
     OR NOT EXISTS (SELECT 1 FROM nodes n WHERE n.id = e.object)
"
```

Expected output: `0` (no dangling edges)

## Step 5: Customize the Pipeline

The merge pipeline is flexible and can be customized for different needs.

### Skip Normalization

If you do not need identifier normalization (e.g., IDs already match):

```bash
koza merge \
  -n "*.nodes.tsv" \
  -e "*.edges.tsv" \
  -o graph.duckdb \
  --skip-normalize
```

### Skip Pruning

Keep all edges and nodes, even if some are dangling or disconnected:

```bash
koza merge \
  -n "*.nodes.tsv" \
  -e "*.edges.tsv" \
  -m "*.sssom.tsv" \
  -o graph.duckdb \
  --skip-prune
```

### Handle Singleton Nodes

By default, singleton nodes (nodes with no edges) are kept. To move them to a separate table:

```bash
koza merge \
  -n "*.nodes.tsv" \
  -e "*.edges.tsv" \
  -m "*.sssom.tsv" \
  -o graph.duckdb \
  --remove-singletons
```

### Export Final Data

Export the merged graph to files for use in other tools:

```bash
koza merge \
  -n "*.nodes.tsv" \
  -e "*.edges.tsv" \
  -m "*.sssom.tsv" \
  -o graph.duckdb \
  --export \
  --export-dir ./output/ \
  --graph-name my_knowledge_graph
```

This creates `my_knowledge_graph_nodes.tsv` and `my_knowledge_graph_edges.tsv`.

### Create a Compressed Archive

For distribution, create a compressed tar archive:

```bash
koza merge \
  -n "*.nodes.tsv" \
  -e "*.edges.tsv" \
  -m "*.sssom.tsv" \
  -o graph.duckdb \
  --export \
  --export-dir ./output/ \
  --archive \
  --compress \
  --graph-name monarch_kg
```

This creates `monarch_kg.tar.gz` containing both node and edge files.

### Auto-Discovery Mode

For directories with standard naming conventions, use auto-discovery:

```bash
koza merge \
  --input-dir ./data/ \
  --mappings-dir ./sssom/ \
  -o merged.duckdb
```

This automatically finds files matching patterns like `*_nodes.tsv` and `*.sssom.tsv`.

## Troubleshooting

### Error: No Mapping Files Found

```
Error: Must specify --mappings-dir, --mappings, or --skip-normalize
```

**Solution**: Either provide SSSOM mappings or skip normalization:

```bash
# Option 1: Provide mappings
koza merge -n "*.nodes.tsv" -e "*.edges.tsv" \
  -m mondo.sssom.tsv -o graph.duckdb

# Option 2: Skip normalization
koza merge -n "*.nodes.tsv" -e "*.edges.tsv" \
  --skip-normalize -o graph.duckdb
```

### Many Dangling Edges After Merge

If you see many dangling edges in the output, your mappings may be incomplete.

**Diagnose**:

```bash
# Check which edge objects are not in nodes
duckdb merged_graph.duckdb -c "
  SELECT DISTINCT e.object
  FROM edges e
  WHERE NOT EXISTS (SELECT 1 FROM nodes n WHERE n.id = e.object)
  LIMIT 20
"
```

**Solutions**:

1. Add more mappings to cover missing identifiers
2. Add the missing nodes from another source
3. Use `--skip-prune` to keep dangling edges for later resolution

### Duplicate Mappings Warning

```
Found 234 duplicate mappings (one object_id mapped to multiple subject_ids).
Keeping only one mapping per object_id.
```

This occurs when your SSSOM file contains one-to-many mappings (one source ID maps to multiple targets).

**Solution**: Order your mapping files with preferred mappings first, or curate your SSSOM files to have deterministic mappings:

```bash
# Preferred mappings file first
koza merge \
  -n "*.nodes.tsv" \
  -e "*.edges.tsv" \
  -m preferred_mappings.sssom.tsv \
  -m secondary_mappings.sssom.tsv \
  -o graph.duckdb
```

### Join Failed - No Files Loaded

```
Error: Join operation failed - no files were loaded
```

**Causes**:

- File paths are incorrect
- Glob patterns do not match any files
- Files are in an unsupported format

**Solution**: Verify files exist and use correct patterns:

```bash
# Check files exist
ls -la *.nodes.tsv *.edges.tsv

# Use explicit paths instead of patterns
koza merge \
  -n genes_nodes.tsv \
  -n diseases_nodes.tsv \
  -e associations_edges.tsv \
  -m mondo_omim.sssom.tsv \
  -o graph.duckdb
```

### Out of Memory for Large Graphs

For very large graphs, DuckDB handles most memory management automatically. If you encounter issues:

1. Use a persistent database (always use `--output`)
2. Process files in batches using `koza append`
3. Ensure sufficient disk space for temporary files

## What You Learned

In this tutorial, you learned how to:

- Prepare KGX files from multiple sources with different ID schemes
- Create SSSOM mapping files to harmonize identifiers
- Run the complete merge pipeline (join, deduplicate, normalize, prune)
- Customize the pipeline by skipping steps or changing options
- Verify the merge results using DuckDB queries
- Troubleshoot common issues with mappings and dangling edges

## Next Steps

Now that you understand the merge pipeline, explore these resources:

- [How to Normalize IDs](../how-to/normalize-ids.md) - Deep dive into SSSOM mappings
- [How to Join Files](../how-to/join-files.md) - Advanced file joining options
- [How to Clean Graphs](../how-to/clean-graph.md) - Graph pruning strategies
- [How to Generate Reports](../how-to/generate-reports.md) - QC and statistics
- [CLI Reference](../reference/cli.md) - Complete command documentation
