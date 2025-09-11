"""
Schema management and analysis for KGX graph operations.

This module provides schema analysis, biolink compliance checking,
and schema report generation capabilities.
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from loguru import logger

from .utils import GraphDatabase


def generate_schema_report(db: GraphDatabase) -> Dict[str, Any]:
    """
    Generate comprehensive schema analysis report from loaded files.
    
    Args:
        db: GraphDatabase instance with loaded files
        
    Returns:
        Schema report dictionary
    """
    return db.get_schema_report()


def write_schema_report_yaml(
    schema_report: Dict[str, Any], 
    output_path: Path,
    operation_name: str = "join"
) -> None:
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
                "report_version": "1.0"
            },
            "schema_analysis": schema_report
        }
        
        # Write YAML file
        with open(yaml_path, 'w') as f:
            yaml.dump(full_report, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Schema report written to {yaml_path}")
        
    except Exception as e:
        logger.error(f"Failed to write schema report YAML: {e}")


def print_schema_summary(schema_report: Dict[str, Any]) -> None:
    """
    Print concise schema summary to console.
    
    Args:
        schema_report: Schema report dictionary
    """
    try:
        if "error" in schema_report:
            print(f"  ⚠️  Schema analysis failed: {schema_report['error']}")
            return
        
        print(f"  📋 Schema Analysis:")
        
        # Summary by table type
        if "summary" in schema_report:
            for table_type, info in schema_report["summary"].items():
                file_count = info.get("file_count", 0)
                unique_columns = info.get("unique_columns", 0)
                print(f"    - {table_type.title()}: {file_count} files, {unique_columns} unique columns")
        
        # Show schema variations
        if "files" in schema_report:
            files = schema_report["files"]
            
            # Group by column count to show schema variations
            column_counts = {}
            for file_info in files:
                count = file_info["column_count"]
                table_type = file_info["table_type"]
                key = f"{table_type}_{count}"
                if key not in column_counts:
                    column_counts[key] = []
                column_counts[key].append(file_info["filename"])
            
            # Show schema variations
            variations = len(column_counts)
            if variations > 1:
                print(f"    - Schema variations: {variations} different column structures detected")
                
                # Show examples of different schemas
                shown = 0
                for key, filenames in column_counts.items():
                    if shown >= 3:  # Limit to 3 examples
                        break
                    table_type, col_count = key.split("_")
                    example_file = Path(filenames[0]).name
                    print(f"      • {col_count} columns: {example_file} (+{len(filenames)-1} more)")
                    shown += 1
                    
                if len(column_counts) > 3:
                    print(f"      • ... and {len(column_counts) - 3} more variations")
            else:
                print(f"    - Schema consistency: All files have matching column structures")
        
    except Exception as e:
        logger.error(f"Failed to print schema summary: {e}")
        print(f"  ⚠️  Schema summary failed: {e}")


def analyze_biolink_compliance(schema_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze schema compliance against biolink model.
    
    This is a placeholder for Phase 1 biolink compliance analysis.
    
    Args:
        schema_report: Schema report dictionary
        
    Returns:
        Biolink compliance analysis
    """
    # TODO: Implement biolink model comparison
    # - Load biolink model definitions
    # - Compare against required slots
    # - Calculate compliance percentages
    # - Identify missing/extra fields
    
    return {
        "status": "not_implemented",
        "message": "Biolink compliance analysis will be implemented in Phase 1"
    }