"""
Split operation for dividing KGX files by specified fields with format conversion support.
"""

import time
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from koza.model.graph_operations import KGXFormat, OperationSummary, SplitConfig, SplitResult

from .utils import GraphDatabase, print_operation_summary


def split_graph(config: SplitConfig) -> SplitResult:
    """
    Split a KGX file into multiple output files based on field values.

    This operation partitions a single KGX file (nodes or edges) into separate files
    based on the unique values of one or more specified fields. Supports format
    conversion between TSV, JSONL, and Parquet during the split.

    The split process:
    1. Loads the input file into an in-memory DuckDB database
    2. Identifies all unique value combinations for the specified split fields
    3. For each unique combination, exports matching records to a separate file
    4. Output filenames are generated from the split field values

    Handles multivalued fields (arrays) by using list_contains() for filtering,
    allowing records to appear in multiple output files if they contain multiple
    values in the split field.

    Args:
        config: SplitConfig containing:
            - input_file: FileSpec for the input KGX file
            - split_fields: List of column names to split on (e.g., ["provided_by"])
            - output_directory: Path where split files will be written
            - output_format: Target format (TSV, JSONL, Parquet); defaults to input format
            - remove_prefixes: Strip CURIE prefixes from values in output filenames
            - quiet: Suppress console output
            - show_progress: Display progress bar during splitting

    Returns:
        SplitResult containing:
            - input_file: The original input FileSpec
            - output_files: List of Path objects for created files
            - total_records_split: Total number of records processed
            - split_values: List of dicts showing the field value combinations
            - total_time_seconds: Operation duration

    Raises:
        FileNotFoundError: If input file does not exist
        Exception: If loading or export operations fail
    """
    start_time = time.time()
    output_files = []

    try:
        # Validate input file exists
        if not config.input_file.path.exists():
            raise FileNotFoundError(f"Input file not found: {config.input_file.path}")

        # Create output directory
        config.output_directory.mkdir(parents=True, exist_ok=True)

        # Determine output format
        output_format = config.output_format or config.input_file.format

        # Initialize database
        with GraphDatabase() as db:  # Use in-memory database for split operations
            # Load the input file
            if not config.quiet:
                print(f"Loading {config.input_file.path.name}...")

            file_result = db.load_file(config.input_file)

            if file_result.errors:
                raise Exception(f"Failed to load input file: {file_result.errors[0]}")

            # Create final table from loaded data
            db.create_final_tables([file_result])

            # Get distinct values for split fields
            table_name = config.input_file.file_type.value

            # Check which fields are array types (for multivalued field handling)
            array_fields = set()
            schema_result = db.conn.execute(f"DESCRIBE {table_name}").fetchall()
            for col_name, col_type, *_ in schema_result:
                if col_name in config.split_fields and "[]" in col_type:
                    array_fields.add(col_name)

            # Build query for distinct values, using UNNEST for array fields
            if array_fields:
                # For array fields, we need to unnest to get individual values
                # Also handle NULL arrays separately since UNNEST(NULL) returns nothing
                select_parts = []
                for field in config.split_fields:
                    if field in array_fields:
                        select_parts.append(f"UNNEST({field}) as {field}")
                    else:
                        select_parts.append(field)
                fields_str = ", ".join(select_parts)

                # Get non-NULL values via UNNEST
                non_null_query = f"SELECT DISTINCT {fields_str} FROM {table_name} WHERE {list(array_fields)[0]} IS NOT NULL"

                # Also get NULL values if any exist (for single array field case)
                if len(config.split_fields) == 1 and len(array_fields) == 1:
                    field = config.split_fields[0]
                    null_check = f"SELECT DISTINCT NULL as {field} FROM {table_name} WHERE {field} IS NULL"
                    distinct_query = f"{non_null_query} UNION {null_check}"
                else:
                    distinct_query = non_null_query
            else:
                fields_str = ", ".join(config.split_fields)
                distinct_query = f"SELECT DISTINCT {fields_str} FROM {table_name}"

            split_values_raw = db.conn.execute(distinct_query).fetchall()

            # Convert to list of dictionaries
            split_values_raw_dicts = [
                dict(zip(config.split_fields, values, strict=False)) for values in split_values_raw
            ]

            if not config.quiet:
                print(f"Found {len(split_values_raw_dicts)} unique combinations to split on")

            # Generate output files for each combination
            if config.show_progress:
                progress = tqdm(split_values_raw_dicts, desc="Splitting files", unit="file")
            else:
                progress = split_values_raw_dicts

            total_records_split = 0

            for values_dict in progress:
                # Generate filename from split values
                filename = _generate_filename(
                    config.input_file.path, values_dict, output_format, config.remove_prefixes
                )

                output_path = config.output_directory / filename

                if config.show_progress:
                    progress.set_description(f"Creating {filename}")

                # Build WHERE clause (use list_contains for array fields)
                where_conditions = []
                for field, value in values_dict.items():
                    if value is not None:
                        # Escape single quotes in the value
                        escaped_value = str(value).replace("'", "''")
                        if field in array_fields:
                            # For array fields, check if the array contains the value
                            where_conditions.append(f"list_contains({field}, '{escaped_value}')")
                        else:
                            where_conditions.append(f"{field} = '{escaped_value}'")
                    else:
                        where_conditions.append(f"{field} IS NULL")

                where_clause = " AND ".join(where_conditions)

                # Export filtered data
                _export_split_data(db, table_name, where_clause, output_path, output_format)

                # Count records in this split
                count_query = f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
                count_result = db.conn.execute(count_query).fetchone()
                records_in_split = count_result[0] if count_result else 0
                total_records_split += records_in_split

                output_files.append(output_path)

                if not config.quiet and not config.show_progress:
                    print(f"  - {filename}: {records_in_split:,} records")

        total_time = time.time() - start_time

        # Convert None values to empty strings for Pydantic validation
        split_values_for_result = []
        for values_dict in split_values_raw_dicts:
            converted_dict = {k: str(v) if v is not None else "" for k, v in values_dict.items()}
            split_values_for_result.append(converted_dict)

        # Create result
        result = SplitResult(
            input_file=config.input_file,
            output_files=output_files,
            total_records_split=total_records_split,
            split_values=split_values_for_result,
            total_time_seconds=total_time,
        )

        # Print summary if not quiet
        if not config.quiet:
            _print_split_summary(result, output_format)

        return result

    except Exception as e:
        total_time = time.time() - start_time

        if not config.quiet:
            summary = OperationSummary(
                operation="Split",
                success=False,
                message=f"Operation failed: {e}",
                files_processed=len(output_files),
                total_time_seconds=total_time,
                errors=[str(e)],
            )
            print_operation_summary(summary)

        raise


def _generate_filename(
    original_path: Path, values_dict: dict[str, str], output_format: KGXFormat, remove_prefixes: bool
) -> str:
    """
    Generate output filename from split field values.

    Constructs a filename by combining the original file's prefix, the split
    field values, and the original suffix (e.g., "_nodes", "_edges").

    Example: "monarch_nodes.tsv" split on provided_by="infores:hgnc" produces
    "monarch_hgnc_nodes.tsv" (with remove_prefixes=True).

    Args:
        original_path: Path to the original input file
        values_dict: Dict mapping field names to their values for this split
        output_format: Target output format (determines file extension)
        remove_prefixes: If True, strip CURIE prefixes (e.g., "HP:0001234" -> "0001234")

    Returns:
        Generated filename string with appropriate extension
    """

    def clean_value_for_filename(value: str) -> str:
        """Sanitize a field value for use in a filename."""
        if remove_prefixes and ":" in value:
            value = value.split(":")[-1]
        return value.replace("biolink:", "").replace(" ", "_").replace(":", "_")

    # Get base filename parts
    base_name = original_path.stem

    # Remove standard suffixes to get prefix
    if base_name.endswith("_edges"):
        prefix = base_name[:-6]
        suffix = "_edges"
    elif base_name.endswith("_nodes"):
        prefix = base_name[:-6]
        suffix = "_nodes"
    else:
        prefix = base_name
        suffix = ""

    # Generate middle part from split values
    middle_parts = [clean_value_for_filename(str(value)) for value in values_dict.values() if value is not None]
    middle = "_".join(middle_parts)

    # Determine extension
    if output_format == KGXFormat.TSV:
        ext = ".tsv"
    elif output_format == KGXFormat.JSONL:
        ext = ".jsonl"
    elif output_format == KGXFormat.PARQUET:
        ext = ".parquet"
    else:
        ext = ".tsv"  # default

    return f"{prefix}_{middle}{suffix}{ext}"


def _export_split_data(
    db: GraphDatabase, table_name: str, where_clause: str, output_path: Path, output_format: KGXFormat
):
    """
    Export filtered records from a table to a file in the specified format.

    Uses DuckDB's COPY command to efficiently export records matching the
    WHERE clause to TSV, JSONL, or Parquet format.

    Args:
        db: GraphDatabase instance with active connection
        table_name: Name of the table to export from ("nodes" or "edges")
        where_clause: SQL WHERE clause to filter records (without "WHERE" keyword)
        output_path: Destination file path
        output_format: Target format (TSV, JSONL, or PARQUET)

    Raises:
        ValueError: If output_format is not supported
        Exception: If the COPY operation fails
    """

    try:
        if output_format == KGXFormat.TSV:
            copy_sql = f"""
                COPY (
                    SELECT * FROM {table_name}
                    WHERE {where_clause}
                ) TO '{output_path}' (HEADER, DELIMITER '\\t')
            """
        elif output_format == KGXFormat.PARQUET:
            copy_sql = f"""
                COPY (
                    SELECT * FROM {table_name}
                    WHERE {where_clause}
                ) TO '{output_path}' (FORMAT PARQUET)
            """
        elif output_format == KGXFormat.JSONL:
            copy_sql = f"""
                COPY (
                    SELECT * FROM {table_name}
                    WHERE {where_clause}
                ) TO '{output_path}' (FORMAT JSON)
            """
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        db.conn.execute(copy_sql)

    except Exception as e:
        logger.error(f"Failed to export {output_path}: {e}")
        raise


def _print_split_summary(result: SplitResult, output_format: KGXFormat):
    """Print formatted split summary."""

    print(f"✓ Split completed successfully")
    print(f"  📁 Input: {result.input_file.path.name} ({result.input_file.format.value} format)")
    print(f"  📂 Output directory: {result.output_files[0].parent}")
    print(f"  📊 Results:")
    print(f"    - Output files created: {len(result.output_files)}")
    print(f"    - Total records split: {result.total_records_split:,}")
    print(f"    - Output format: {output_format.value}")
    print(f"    - Split combinations: {len(result.split_values)}")
    print(f"  ⏱️  Total time: {result.total_time_seconds:.2f}s")

    # Show first few split values as examples
    if result.split_values:
        print(f"  📋 Example split values:")
        for i, values in enumerate(result.split_values[:3]):
            values_str = ", ".join([f"{k}={v}" for k, v in values.items()])
            print(f"    - {values_str}")
        if len(result.split_values) > 3:
            print(f"    - ... and {len(result.split_values) - 3} more")
