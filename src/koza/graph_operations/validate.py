"""
Validate graph operation for running declarative validation from config.
"""

import time
from pathlib import Path

import yaml

from koza.graph_operations.schema_utils import SchemaParser
from koza.graph_operations.utils import GraphDatabase
from koza.graph_operations.validation import ValidationContext, ValidationEngine, ValidationProfile
from koza.model.graph_operations import (
    ValidationConfig,
    ValidationReportModel,
    ValidationResult,
    ValidationViolationModel,
    ViolationSampleModel,
)


def validate_graph(config: ValidationConfig) -> ValidationResult:
    """
    Validate a graph database against Biolink model constraints.

    Args:
        config: ValidationConfig with database path and options

    Returns:
        ValidationResult with validation report
    """
    start_time = time.time()

    with GraphDatabase(config.database_path, read_only=True) as db:
        schema_parser = SchemaParser(config.schema_path)
        engine = ValidationEngine(db, schema_parser, sample_limit=config.sample_limit)

        # Create ValidationContext with profile from config (Phase 3)
        profile_map = {
            "minimal": ValidationProfile.MINIMAL,
            "standard": ValidationProfile.STANDARD,
            "full": ValidationProfile.FULL,
        }
        profile = profile_map.get(config.profile, ValidationProfile.STANDARD)
        context = ValidationContext(profile=profile)

        report = engine.validate(context=context)

        # Filter to errors only if requested
        if not config.include_warnings:
            report.violations = [v for v in report.violations if v.severity == "error"]
        if not config.include_info:
            report.violations = [v for v in report.violations if v.severity != "info"]

        # Convert dataclass report to Pydantic model
        pydantic_violations = [
            ValidationViolationModel(
                constraint_type=v.constraint_type.value,
                slot_name=v.slot_name,
                table=v.table,
                severity=v.severity,
                description=v.description,
                violation_count=v.violation_count,
                total_records=v.total_records,
                violation_percentage=v.violation_percentage,
                samples=[
                    ViolationSampleModel(values=s.values, count=s.count)
                    for s in v.samples
                ],
            )
            for v in report.violations
        ]

        pydantic_report = ValidationReportModel(
            violations=pydantic_violations,
            total_violations=report.total_violations,
            error_count=report.error_count,
            warning_count=report.warning_count,
            info_count=report.info_count,
            compliance_percentage=report.compliance_percentage,
            tables_validated=report.tables_validated,
            constraints_checked=report.constraints_checked,
        )

        # Write output file if specified
        if config.output_file:
            output_path = Path(config.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            report_dict = {
                "metadata": {
                    "database": str(config.database_path),
                    "schema": config.schema_path or "biolink-model (default)",
                },
                "summary": {
                    "compliance_percentage": pydantic_report.compliance_percentage,
                    "total_violations": pydantic_report.total_violations,
                    "error_count": pydantic_report.error_count,
                    "warning_count": pydantic_report.warning_count,
                    "tables_validated": pydantic_report.tables_validated,
                    "constraints_checked": pydantic_report.constraints_checked,
                },
                "violations": [
                    {
                        "constraint": v.constraint_type,
                        "field": v.slot_name,
                        "table": v.table,
                        "severity": v.severity,
                        "description": v.description,
                        "count": v.violation_count,
                        "percentage": round(v.violation_percentage, 2),
                        "samples": [{"values": s.values, "count": s.count} for s in v.samples],
                    }
                    for v in pydantic_violations
                ],
            }

            with open(output_path, "w") as f:
                yaml.dump(report_dict, f, default_flow_style=False, sort_keys=False)

        total_time = time.time() - start_time

        return ValidationResult(
            validation_report=pydantic_report,
            output_file=config.output_file,
            total_time_seconds=total_time,
        )
