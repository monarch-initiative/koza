"""
Pydantic models and enums for graph operations.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator


class KGXFormat(str, Enum):
    """Supported KGX file formats"""

    TSV = "tsv"
    JSONL = "jsonl"
    PARQUET = "parquet"


class KGXFileType(str, Enum):
    """KGX file types"""

    NODES = "nodes"
    EDGES = "edges"


class FileSpec(BaseModel):
    """Specification for a KGX file"""

    path: Path
    source_name: str | None = Field(default=None,validate_default=True)
    format: KGXFormat | None = Field(default=None,validate_default=True)
    file_type: KGXFileType | None = Field(default=None,validate_default=True)

    @field_validator("format",mode="before")
    def generate_format(cls, format_value :KGXFormat|None, info:ValidationInfo) -> KGXFormat:
        """Auto-detect format and file_type from path if not provided.

        Uses model_validator(mode='after') to ensure path is fully validated
        and available as a Path object before detection runs.
        """
        # Detect format from file extension
        if format_value is None:
            path = info.data["path"]
            # Handle compressed files
            if path.suffix.lower() in [".gz", ".bz2", ".xz"]:
                path = path.with_suffix("")

            suffix = path.suffix.lower()
            if suffix in [".tsv", ".txt"]:
                return KGXFormat.TSV
            elif suffix in [".jsonl", ".json"]:
                return KGXFormat.JSONL
            elif suffix == ".parquet":
                return KGXFormat.PARQUET
        else: return format_value

    @field_validator("file_type",mode="before")
    def generate_file_type(cls, file_type_value :KGXFileType|None, info:ValidationInfo) -> KGXFileType:    
        # Detect file_type from filename
        if file_type_value is None:
            filename = Path(info.data["path"]).name.lower()
            if "_nodes." in filename or filename.startswith("nodes."):
                return KGXFileType.NODES
            elif "_edges." in filename or filename.startswith("edges."):
                return KGXFileType.EDGES
        return file_type_value
    
    @field_validator("source_name", mode="before")
    @classmethod
    def generate_source_name(cls, source_name_value, info:ValidationInfo):
        """Auto-generate source_name from file path if not provided"""
        """The default is the parent directory of the file path."""
        if source_name_value is None and "path" in info.data:
            return Path(info.data["path"]).stem
        return source_name_value

class DatabaseStats(BaseModel):
    """Database statistics model"""

    nodes: int = 0
    edges: int = 0
    dangling_edges: int = 0
    duplicate_nodes: int = 0
    singleton_nodes: int = 0
    database_size_mb: float | None = None


class GraphOperationConfig(BaseModel):
    """Base configuration for graph operations"""

    database_path: Path | None = None  # None = in-memory
    output_format: KGXFormat = KGXFormat.TSV
    quiet: bool = False
    show_progress: bool = True


class JoinConfig(GraphOperationConfig):
    """Configuration for join operation"""

    node_files: list[FileSpec] = Field(default_factory=list)
    edge_files: list[FileSpec] = Field(default_factory=list)
    output_database: Path | None = None
    schema_reporting: bool = True
    preserve_duplicates: bool = False
    generate_provided_by: bool = True  # Add provided_by column from filename (like cat-merge)

    @model_validator(mode="after")
    def set_database_path_from_output_database(self):
        """Set database_path from output_database for compatibility"""
        if self.output_database is not None:
            self.database_path = self.output_database
        return self


class SplitConfig(GraphOperationConfig):
    """Configuration for split operation"""

    input_file: FileSpec
    split_fields: list[str]
    output_directory: Path = Field(default=Path("./output"))
    remove_prefixes: bool = False
    output_format: KGXFormat | None = None  # None = preserve original format


class FileLoadResult(BaseModel):
    """Result of loading a file"""

    file_spec: FileSpec
    records_loaded: int
    detected_format: KGXFormat
    load_time_seconds: float
    errors: list[str] = Field(default_factory=list)
    temp_table_name: str | None = None  # Name of temp table for schema analysis


class JoinResult(BaseModel):
    """Result of join operation"""

    files_loaded: list[FileLoadResult]
    final_stats: DatabaseStats
    schema_report: dict[str, Any] | None = None
    total_time_seconds: float
    database_path: Path | None = None


class SplitResult(BaseModel):
    """Result of split operation"""

    input_file: FileSpec
    output_files: list[Path]
    total_records_split: int
    split_values: list[dict[str, str]]
    total_time_seconds: float


class PruneConfig(BaseModel):
    """Configuration for prune operation"""

    database_path: Path
    keep_singletons: bool = True  # Preserve isolated nodes
    remove_singletons: bool = False  # Move singletons to separate table
    min_component_size: int | None = None  # Minimum connected component size
    quiet: bool = False
    show_progress: bool = True
    output_format: KGXFormat | None = None  # For any exported files

    @field_validator("database_path")
    @classmethod
    def validate_database_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Database file not found: {v}")
        return v

    @model_validator(mode="after")
    def validate_singleton_options(self):
        """Ensure only one singleton option is selected"""
        if self.keep_singletons and self.remove_singletons:
            raise ValueError("Cannot both keep and remove singletons - choose one option")
        return self


class PruneResult(BaseModel):
    """Result of prune operation"""

    database_path: Path
    dangling_edges_moved: int
    singleton_nodes_moved: int
    singleton_nodes_kept: int
    final_stats: DatabaseStats
    dangling_edges_by_source: dict[str, int] = Field(default_factory=dict)
    missing_nodes_by_source: dict[str, int] = Field(default_factory=dict)
    total_time_seconds: float
    success: bool
    errors: list[str] = Field(default_factory=list)


class AppendConfig(BaseModel):
    """Configuration for append operation"""

    database_path: Path
    node_files: list[FileSpec] = Field(default_factory=list)
    edge_files: list[FileSpec] = Field(default_factory=list)
    deduplicate: bool = False  # Optional deduplication during append
    quiet: bool = False
    show_progress: bool = True
    schema_reporting: bool = False

    @field_validator("database_path")
    @classmethod
    def validate_database_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Database file not found: {v}")
        return v

    @model_validator(mode="after")
    def validate_files_provided(self):
        """Ensure at least some files are provided"""
        if not self.node_files and not self.edge_files:
            raise ValueError("Must provide at least one node or edge file")
        return self


class AppendResult(BaseModel):
    """Result of append operation"""

    database_path: Path
    files_loaded: list[FileLoadResult]
    records_added: int
    new_columns_added: int
    schema_changes: list[str] = Field(default_factory=list)
    final_stats: DatabaseStats
    schema_report: dict[str, Any] | None = None
    duplicates_handled: int = 0
    total_time_seconds: float


class NormalizeConfig(BaseModel):
    """Configuration for normalize operation"""

    database_path: Path
    mapping_files: list[FileSpec] = Field(default_factory=list)
    quiet: bool = False
    show_progress: bool = True

    @field_validator("database_path")
    @classmethod
    def validate_database_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Database file not found: {v}")
        return v

    @model_validator(mode="after")
    def validate_mapping_files_provided(self):
        """Ensure mapping files are provided"""
        if not self.mapping_files:
            raise ValueError("Must provide at least one SSSOM mapping file")
        return self


class NormalizeResult(BaseModel):
    """Result of normalize operation"""

    success: bool
    mappings_loaded: list[FileLoadResult]
    edges_normalized: int
    final_stats: DatabaseStats | None = None
    total_time_seconds: float
    summary: "OperationSummary"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DeduplicateConfig(BaseModel):
    """Configuration for deduplicate operation"""

    database_path: Path
    deduplicate_nodes: bool = True
    deduplicate_edges: bool = True
    quiet: bool = False
    show_progress: bool = True

    @field_validator("database_path")
    @classmethod
    def validate_database_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Database file not found: {v}")
        return v


class DeduplicateResult(BaseModel):
    """Result of deduplicate operation"""

    success: bool
    duplicate_nodes_found: int = 0
    duplicate_nodes_removed: int = 0  # Rows removed from nodes table
    duplicate_edges_found: int = 0
    duplicate_edges_removed: int = 0  # Rows removed from edges table
    final_stats: DatabaseStats | None = None
    total_time_seconds: float
    summary: "OperationSummary"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MergeConfig(BaseModel):
    """Configuration for merge operation - composite pipeline"""

    # Input files
    node_files: list[FileSpec] = Field(default_factory=list)
    edge_files: list[FileSpec] = Field(default_factory=list)
    mapping_files: list[FileSpec] = Field(default_factory=list)

    # Pipeline options
    skip_deduplicate: bool = False  # Skip deduplication step
    skip_normalize: bool = False  # Skip normalization step
    skip_prune: bool = False  # Skip pruning step
    generate_provided_by: bool = True  # Add provided_by column from filename (like cat-merge)
    continue_on_pipeline_step_error: bool = True # If there is an error for a non-critical pipeline step, append a warning and continue the merge.

    # Prune-specific options
    keep_singletons: bool = True
    remove_singletons: bool = False

    # Output options
    output_database: Path | None = None  # If None, uses temporary database
    output_format: KGXFormat = KGXFormat.TSV
    export_final: bool = False  # Export final clean data to files
    export_directory: Path | None = None
    archive: bool = False  # Export as archive instead of loose files
    compress: bool = False  # Compress archive as tar.gz
    graph_name: str | None = None  # Name for graph files in archive

    # General options
    quiet: bool = False
    show_progress: bool = True
    schema_reporting: bool = True

    @model_validator(mode="after")
    def validate_files_provided(self):
        """Ensure at least some input files are provided"""
        if not self.node_files and not self.edge_files:
            raise ValueError("Must provide at least one node or edge file")
        return self

    @model_validator(mode="after")
    def validate_normalize_requirements(self):
        """If normalize is enabled, ensure mapping files are provided"""
        if not self.skip_normalize and not self.mapping_files:
            raise ValueError("Must provide mapping files or set skip_normalize=True")
        return self

    @model_validator(mode="after")
    def validate_singleton_options(self):
        """Ensure only one singleton option is selected"""
        if self.keep_singletons and self.remove_singletons:
            raise ValueError("Cannot both keep and remove singletons - choose one option")
        return self

    @model_validator(mode="after")
    def validate_export_options(self):
        """If export is enabled, ensure export directory is provided"""
        if self.export_final and not self.export_directory:
            raise ValueError("Must provide export_directory when export_final=True")
        return self

    @model_validator(mode="after")
    def validate_archive_options(self):
        """Validate archive and compress options"""
        if self.compress and not self.archive:
            raise ValueError("compress option requires archive option to be enabled")
        return self


class MergeResult(BaseModel):
    """Result of merge operation - composite pipeline"""

    success: bool

    # Individual operation results
    join_result: Optional["JoinResult"] = None
    deduplicate_result: Optional["DeduplicateResult"] = None
    normalize_result: Optional["NormalizeResult"] = None
    prune_result: Optional["PruneResult"] = None

    # Pipeline summary
    operations_completed: list[str] = Field(default_factory=list)
    operations_skipped: list[str] = Field(default_factory=list)

    # Final statistics
    final_stats: DatabaseStats | None = None
    database_path: Path | None = None
    exported_files: list[Path] = Field(default_factory=list)

    # Timing and error reporting
    total_time_seconds: float
    summary: "OperationSummary"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class OperationSummary(BaseModel):
    """Summary statistics for CLI output"""

    operation: str
    success: bool
    message: str
    stats: DatabaseStats | None = None
    files_processed: int = 0
    total_time_seconds: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# Report Operation Models


class QCSummary(BaseModel):
    """Summary section of QC report."""

    total_nodes: int
    total_edges: int
    dangling_edges: int = 0
    duplicate_nodes: int = 0
    singleton_nodes: int = 0


class NodeSourceReport(BaseModel):
    """Node analysis for a specific data source."""

    name: str
    total_number: int
    categories: list[str] = Field(default_factory=list)
    namespaces: list[str] = Field(default_factory=list)


class PredicateReport(BaseModel):
    """Predicate analysis within an edge source."""

    uri: str
    count: int


class EdgeSourceReport(BaseModel):
    """Edge analysis for a specific data source."""

    name: str
    total_number: int
    predicates: list[PredicateReport] = Field(default_factory=list)
    namespaces: list[str] = Field(default_factory=list)


class QCReport(BaseModel):
    """Complete QC report structure."""

    summary: QCSummary
    nodes: list[NodeSourceReport] = Field(default_factory=list)
    edges: list[EdgeSourceReport] = Field(default_factory=list)
    dangling_edges: list[EdgeSourceReport] = Field(default_factory=list)
    duplicate_nodes: list[NodeSourceReport] = Field(default_factory=list)
    duplicate_edges: list[EdgeSourceReport] = Field(default_factory=list)


class CategoryStats(BaseModel):
    """Statistics for a node/edge category."""

    count: int
    provided_by: dict[str, dict[str, int]] = Field(default_factory=dict)


class PredicateStats(BaseModel):
    """Statistics for an edge predicate."""

    count: int
    provided_by: dict[str, dict[str, int]] = Field(default_factory=dict)


class NodeStats(BaseModel):
    """Comprehensive node statistics."""

    total_nodes: int
    count_by_category: dict[str, CategoryStats] = Field(default_factory=dict)
    count_by_id_prefixes: dict[str, int] = Field(default_factory=dict)
    node_categories: list[str] = Field(default_factory=list)
    node_id_prefixes: list[str] = Field(default_factory=list)
    provided_by: list[str] = Field(default_factory=list)


class EdgeStats(BaseModel):
    """Comprehensive edge statistics."""

    total_edges: int
    count_by_predicates: dict[str, PredicateStats] = Field(default_factory=dict)
    predicates: list[str] = Field(default_factory=list)
    provided_by: list[str] = Field(default_factory=list)


class GraphStatsReport(BaseModel):
    """Complete graph statistics report structure."""

    graph_name: str
    node_stats: NodeStats
    edge_stats: EdgeStats


class TableSchema(BaseModel):
    """Schema information for a database table."""

    columns: list[dict[str, str]] = Field(default_factory=list)  # [{"name": "id", "type": "VARCHAR"}]
    column_count: int
    record_count: int


class BiolinkCompliance(BaseModel):
    """Biolink model compliance analysis."""

    status: str
    message: str
    compliance_percentage: float | None = None
    missing_fields: list[str] = Field(default_factory=list)
    extension_fields: list[str] = Field(default_factory=list)


class SchemaAnalysisReport(BaseModel):
    """Complete schema analysis report structure."""

    tables: dict[str, TableSchema] = Field(default_factory=dict)
    analysis: dict[str, Any] = Field(default_factory=dict)
    biolink_compliance: BiolinkCompliance


class QCReportConfig(BaseModel):
    """Configuration for QC report generation."""

    database_path: Path
    output_file: Path | None = None
    group_by: str = "provided_by"
    quiet: bool = False


class QCReportResult(BaseModel):
    """Result from QC report generation."""

    qc_report: QCReport
    output_file: Path | None = None
    total_time_seconds: float = 0.0


class GraphStatsConfig(BaseModel):
    """Configuration for graph statistics report generation."""

    database_path: Path
    output_file: Path | None = None
    quiet: bool = False


class GraphStatsResult(BaseModel):
    """Result from graph statistics report generation."""

    stats_report: GraphStatsReport
    output_file: Path | None = None
    total_time_seconds: float = 0.0


class SchemaReportConfig(BaseModel):
    """Configuration for schema analysis report generation."""

    database_path: Path
    output_file: Path | None = None
    include_biolink_compliance: bool = True
    quiet: bool = False


class SchemaReportResult(BaseModel):
    """Result from schema analysis report generation."""

    schema_report: SchemaAnalysisReport
    output_file: Path | None = None
    total_time_seconds: float = 0.0


# Tabular Report Models


class TabularReportFormat(str, Enum):
    """Supported formats for tabular reports."""

    TSV = "tsv"
    PARQUET = "parquet"
    JSONL = "jsonl"
    # XLSX = "xlsx"  # stretch goal


class NodeReportConfig(BaseModel):
    """Configuration for tabular node report generation."""

    # Input: either database_path OR node_file (load into in-memory db)
    database_path: Path | None = None
    node_file: "FileSpec | None" = None

    # Output
    output_file: Path | None = None
    output_format: TabularReportFormat = TabularReportFormat.TSV

    # Categorical columns to group by (default set + extensible)
    categorical_columns: list[str] = Field(
        default_factory=lambda: ["namespace", "category", "in_taxon", "provided_by"]
    )

    quiet: bool = False

    @model_validator(mode="after")
    def validate_input_provided(self):
        """Ensure at least one input source is provided."""
        if self.database_path is None and self.node_file is None:
            raise ValueError("Must provide either database_path or node_file")
        return self


class EdgeReportConfig(BaseModel):
    """Configuration for tabular edge report generation."""

    # Input: either database_path OR node_file + edge_file
    database_path: Path | None = None
    node_file: "FileSpec | None" = None
    edge_file: "FileSpec | None" = None

    # Output
    output_file: Path | None = None
    output_format: TabularReportFormat = TabularReportFormat.TSV

    # Default categorical columns for edges
    categorical_columns: list[str] = Field(
        default_factory=lambda: [
            "subject_category",
            "subject_namespace",
            "predicate",
            "object_category",
            "object_namespace",
            "primary_knowledge_source",
            "aggregator_knowledge_source",
            "knowledge_level",
            "agent_type",
            "provided_by",
        ]
    )

    quiet: bool = False

    @model_validator(mode="after")
    def validate_input_provided(self):
        """Ensure at least one input source is provided."""
        if self.database_path is None and self.edge_file is None:
            raise ValueError("Must provide either database_path or edge_file")
        return self


class NodeExamplesConfig(BaseModel):
    """Configuration for node examples generation."""

    # Input: either database_path OR node_file
    database_path: Path | None = None
    node_file: "FileSpec | None" = None

    # Output
    output_file: Path | None = None
    output_format: TabularReportFormat = TabularReportFormat.TSV

    # How many examples per type
    sample_size: int = 5

    # Which column defines the "type" for grouping examples
    type_column: str = "category"

    quiet: bool = False

    @model_validator(mode="after")
    def validate_input_provided(self):
        """Ensure at least one input source is provided."""
        if self.database_path is None and self.node_file is None:
            raise ValueError("Must provide either database_path or node_file")
        return self


class EdgeExamplesConfig(BaseModel):
    """Configuration for edge examples generation."""

    # Input: either database_path OR node_file + edge_file
    database_path: Path | None = None
    node_file: "FileSpec | None" = None
    edge_file: "FileSpec | None" = None

    # Output
    output_file: Path | None = None
    output_format: TabularReportFormat = TabularReportFormat.TSV

    # How many examples per type
    sample_size: int = 5

    # Which columns define the "type" for grouping examples
    # Default: subject_category, predicate, object_category
    type_columns: list[str] = Field(
        default_factory=lambda: ["subject_category", "predicate", "object_category"]
    )

    quiet: bool = False

    @model_validator(mode="after")
    def validate_input_provided(self):
        """Ensure at least one input source is provided."""
        if self.database_path is None and self.edge_file is None:
            raise ValueError("Must provide either database_path or edge_file")
        return self


class NodeReportResult(BaseModel):
    """Result from node report generation."""

    output_file: Path | None = None
    total_rows: int = 0
    total_time_seconds: float = 0.0


class EdgeReportResult(BaseModel):
    """Result from edge report generation."""

    output_file: Path | None = None
    total_rows: int = 0
    total_time_seconds: float = 0.0


class NodeExamplesResult(BaseModel):
    """Result from node examples generation."""

    output_file: Path | None = None
    types_sampled: int = 0
    total_examples: int = 0
    total_time_seconds: float = 0.0


class EdgeExamplesResult(BaseModel):
    """Result from edge examples generation."""

    output_file: Path | None = None
    types_sampled: int = 0
    total_examples: int = 0
    total_time_seconds: float = 0.0
