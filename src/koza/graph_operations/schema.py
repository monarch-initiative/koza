"""
Schema management and analysis for KGX graph operations.

This module provides schema analysis, biolink compliance checking,
and schema report generation capabilities.
"""

import time
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from .utils import GraphDatabase


def generate_schema_report(db: GraphDatabase) -> dict[str, Any]:
    """
    Generate comprehensive schema analysis report from loaded files.

    Args:
        db: GraphDatabase instance with loaded files

    Returns:
        Schema report dictionary
    """
    return db.get_schema_report()


def write_schema_report_yaml(schema_report: dict[str, Any], output_path: Path, operation_name: str = "join") -> None:
    """
    Write schema report to YAML file.

    Args:
        schema_report: Schema report dictionary
        output_path: Path for output file (database path or directory)
        operation_name: Name of the operation (join, split, etc.)
    """
    try:
        # Determine output file path
        if output_path.is_dir():
            yaml_path = output_path / f"{operation_name}_schema_report.yaml"
        else:
            # Use same directory as database file
            yaml_path = output_path.parent / f"{output_path.stem}_schema_report.yaml"

        # Add metadata to report
        full_report = {
            "metadata": {
                "operation": operation_name,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "report_version": "1.0",
            },
            "schema_analysis": schema_report,
        }

        # Write YAML file
        with open(yaml_path, "w") as f:
            yaml.dump(full_report, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Schema report written to {yaml_path}")

    except Exception as e:
        logger.error(f"Failed to write schema report YAML: {e}")


def print_schema_summary(schema_report: dict[str, Any]) -> None:
    """
    Print concise schema summary to console.

    Args:
        schema_report: Schema report dictionary
    """
    try:
        if "error" in schema_report:
            print(f"  Schema analysis failed: {schema_report['error']}")
            return

        print(f"  Schema Analysis:")

        # Summary by table type
        if "summary" in schema_report:
            for table_type, info in schema_report["summary"].items():
                file_count = info.get("file_count", 0)
                unique_columns = info.get("unique_columns", 0)
                print(f"    - {table_type.title()}: {file_count} files, {unique_columns} unique columns")

        # Show schema variations
        if "files" in schema_report:
            files = schema_report["files"]

            # Group by column count to show schema variations (regardless of table type)
            column_counts = {}
            for file_info in files:
                count = file_info["column_count"]
                if count not in column_counts:
                    column_counts[count] = []
                column_counts[count].append((file_info["filename"], file_info["table_type"]))

            # Show schema variations
            variations = len(column_counts)
            if variations > 1:
                print(f"    - Schema variations: {variations} different column structures detected")

                # Show examples of different schemas
                shown = 0
                for col_count, file_entries in column_counts.items():
                    if shown >= 3:  # Limit to 3 examples
                        break
                    example_file = Path(file_entries[0][0]).name  # filename from tuple
                    print(f"      • {col_count} columns: {example_file} (+{len(file_entries) - 1} more)")
                    shown += 1

                if len(column_counts) > 3:
                    print(f"      • ... and {len(column_counts) - 3} more variations")
            else:
                print(f"    - Schema consistency: All files have matching column structures")

    except Exception as e:
        logger.error(f"Failed to print schema summary: {e}")
        print(f"   Schema summary failed: {e}")


def analyze_biolink_compliance(
    db: GraphDatabase,
    schema_path: str | None = None,
    sample_limit: int = 10,
) -> dict[str, Any]:
    """
    Analyze graph compliance against biolink model using ValidationEngine.

    Args:
        db: GraphDatabase instance with loaded data
        schema_path: Optional custom LinkML schema path (defaults to Biolink)
        sample_limit: Maximum number of sample violations per constraint

    Returns:
        Biolink compliance analysis dict with:
        - status: "passed", "failed", "warnings", or "error"
        - compliance_percentage: float
        - error_count: int
        - warning_count: int
        - violations: list of violation summaries
        - tables_validated: list of table names
        - constraints_checked: int
    """
    from .schema_utils import SchemaParser
    from .validation import ValidationEngine

    try:
        # Initialize schema parser and validation engine
        schema_parser = SchemaParser(schema_path)
        engine = ValidationEngine(db, schema_parser, sample_limit)

        # Run validation
        report = engine.validate()

        # Determine overall status
        if report.error_count > 0:
            status = "failed"
        elif report.warning_count > 0:
            status = "warnings"
        else:
            status = "passed"

        # Convert violations to serializable format
        violation_summaries = [
            {
                "constraint_type": v.constraint_type.value,
                "slot_name": v.slot_name,
                "table": v.table,
                "severity": v.severity,
                "description": v.description,
                "violation_count": v.violation_count,
                "violation_percentage": round(v.violation_percentage, 2),
            }
            for v in report.violations
        ]

        return {
            "status": status,
            "compliance_percentage": round(report.compliance_percentage, 2),
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "constraints_checked": report.constraints_checked,
            "tables_validated": report.tables_validated,
            "violations": violation_summaries,
        }

    except Exception as e:
        logger.error(f"Biolink compliance analysis failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "compliance_percentage": None,
            "error_count": 0,
            "warning_count": 0,
            "constraints_checked": 0,
            "tables_validated": [],
            "violations": [],
        }
