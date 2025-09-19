from collections.abc import Sequence
from dataclasses import field
from enum import Enum
from pathlib import Path

from loguru import logger
from pydantic.dataclasses import dataclass
from sssom.parsers import MappingSetDataFrame, parse_sssom_table
from sssom.util import filter_prefixes, merge_msdf, pandas_set_no_silent_downcasting

pandas_set_no_silent_downcasting()


class Match(str, Enum):
    """SSSOM match types."""

    exact = "exact"
    narrow = "narrow"
    broad = "broad"


@dataclass()
class FieldMapping:
    """Configuration for mapping a specific field.

    :param files: Field-specific SSSOM files (merged with global files)
    :param target_prefixes: List of prefixes to map TO for this field
    :param preserve_original: Whether to preserve the original value
    :param original_field_name: Custom name for the preservation field (defaults to original_{field_name})
    """

    target_prefixes: list[str] = field(default_factory=list)
    files: list[str | Path] = field(default_factory=list)
    preserve_original: bool = True
    original_field_name: str | None = None


@dataclass()
class SSSOMConfig:
    """SSSOM config options

    :param files: Global SSSOM files applied to all field mappings
    :param filter_prefixes: Prefixes to filter by
    :param field_mappings: Dictionary mapping field names to FieldMapping configurations
    :param field_target_mappings: (DEPRECATED) Dictionary mapping field names to their target prefixes - use field_mappings instead
    :param subject_target_prefixes: (DEPRECATED) Prefixes to use for subject mapping - use field_mappings instead
    :param object_target_prefixes: (DEPRECATED) Prefixes to use for object mapping - use field_mappings instead
    :param use_match: Match types to use
    """

    files: Sequence[str | Path] = field(default_factory=list)
    filter_prefixes: list[str] = field(default_factory=list)
    field_mappings: dict[str, FieldMapping] = field(default_factory=dict)
    field_target_mappings: dict[str, list[str]] = field(default_factory=dict)  # DEPRECATED
    subject_target_prefixes: list[str] = field(default_factory=list)  # DEPRECATED
    object_target_prefixes: list[str] = field(default_factory=list)   # DEPRECATED
    use_match: list[Match] = field(default_factory=list)

    predicates = {
        "exact": ["skos:exactMatch"],
        "narrow": ["skos:narrowMatch"],
        "broad": ["skos:broadMatch"],
    }

    def __post_init__(self):
        if not self.use_match:
            self.use_match = [Match.exact]

        # Handle backward compatibility - migrate deprecated configurations to new structure
        self._migrate_deprecated_config()

        # Validate that we have at least one SSSOM file somewhere
        self._validate_file_configuration()

        # Build unified field mappings with file merging
        self._build_unified_field_mappings()

        logger.debug("Building SSSOM Dataframe...")
        self.df = self._merge_and_filter_sssom()
        logger.debug("Building SSSOM Lookup Table...")
        self.lookup_table = self._build_sssom_lookup_table()  # use_match=self.use_match)

    def _migrate_deprecated_config(self):
        """Migrate deprecated configuration options to new structure."""
        # Migrate old field_target_mappings to new field_mappings structure
        if self.field_target_mappings:
            logger.warning("field_target_mappings is deprecated. Use field_mappings instead.")
            for field_name, target_prefixes in self.field_target_mappings.items():
                if field_name not in self.field_mappings:
                    self.field_mappings[field_name] = FieldMapping(
                        target_prefixes=target_prefixes,
                        preserve_original=True  # Default for backward compatibility
                    )

        # Migrate old subject_target_prefixes and object_target_prefixes
        if self.subject_target_prefixes and "subject" not in self.field_mappings:
            logger.warning("subject_target_prefixes is deprecated. Use field_mappings['subject'] instead.")
            self.field_mappings["subject"] = FieldMapping(
                target_prefixes=self.subject_target_prefixes,
                preserve_original=True
            )

        if self.object_target_prefixes and "object" not in self.field_mappings:
            logger.warning("object_target_prefixes is deprecated. Use field_mappings['object'] instead.")
            self.field_mappings["object"] = FieldMapping(
                target_prefixes=self.object_target_prefixes,
                preserve_original=True
            )

    def _validate_file_configuration(self):
        """Validate that at least one SSSOM file is specified somewhere."""
        has_global_files = bool(self.files)
        has_field_files = any(field_mapping.files for field_mapping in self.field_mappings.values())

        if not has_global_files and not has_field_files:
            raise ValueError("At least one SSSOM file must be specified either globally or in field_mappings")

    def _build_unified_field_mappings(self):
        """Build unified field mappings that merge global and field-specific files."""
        self._unified_field_mappings = {}

        for field_name, field_mapping in self.field_mappings.items():
            # Merge global files with field-specific files
            all_files = list(self.files) + list(field_mapping.files)

            if not all_files:
                logger.warning(f"No SSSOM files available for field '{field_name}' - skipping")
                continue

            # Set default original field name if not specified
            original_field_name = field_mapping.original_field_name
            if original_field_name is None:
                original_field_name = f"original_{field_name}"

            self._unified_field_mappings[field_name] = {
                'files': all_files,
                'target_prefixes': field_mapping.target_prefixes,
                'preserve_original': field_mapping.preserve_original,
                'original_field_name': original_field_name
            }

    def apply_mapping(self, entity: dict) -> dict:
        """Apply SSSOM mappings to any field in an entity record."""

        for field_name, field_config in self._unified_field_mappings.items():
            if field_name in entity:
                target_prefixes = field_config['target_prefixes']
                if self._has_mapping(entity[field_name], target_prefixes):
                    # Store original value if preservation is enabled
                    if field_config['preserve_original']:
                        original_field_name = field_config['original_field_name']
                        entity[original_field_name] = entity[field_name]

                    # Apply mapping
                    entity[field_name] = self._get_mapping(entity[field_name], target_prefixes)

        return entity

    def _merge_and_filter_sssom(self):
        mapping_sets: list[MappingSetDataFrame] = []

        # Collect all unique files from global and field-specific configurations
        all_files = set(self.files)
        for field_config in self._unified_field_mappings.values():
            all_files.update(field_config['files'])

        # Parse all SSSOM files
        for file in all_files:
            msdf = parse_sssom_table(file)
            mapping_sets.append(msdf)

        if not mapping_sets:
            raise ValueError("No valid SSSOM files found")

        merged_msdf = merge_msdf(*mapping_sets)

        # Collect all target prefixes from unified field mappings
        all_target_prefixes = []
        for field_config in self._unified_field_mappings.values():
            all_target_prefixes.extend(field_config['target_prefixes'])

        filters = [
            *all_target_prefixes,
            *(set(self.filter_prefixes) - set(all_target_prefixes)),
        ]
        logger.debug(f"Filtering SSSOM by {filters}")
        merged_msdf = filter_prefixes(
            df=merged_msdf.df,
            filter_prefixes=filters,
            require_all_prefixes=False,
            features=merged_msdf.df.columns,  # type: ignore
        )

        return merged_msdf

    def _build_sssom_lookup_table(self):
        """Build a lookup table from SSSOM mapping dataframe."""
        sssom_lookup_table: dict[str, dict[str, str]] = {}
        for row in self.df.itertuples():
            subject_id: str = row.subject_id  # type: ignore
            object_id: str = row.object_id  # type: ignore
            predicate: str = row.predicate_id  # type: ignore
            if Match.exact in self.use_match:
                # Add exact match mappings in both directions
                sssom_lookup_table = self._set_mapping(
                    subject_id,
                    object_id,
                    predicate,
                    match=Match.exact,
                    lookup_table=sssom_lookup_table,
                )
                sssom_lookup_table = self._set_mapping(
                    object_id,
                    subject_id,
                    predicate,
                    match=Match.exact,
                    lookup_table=sssom_lookup_table,
                )
            if Match.narrow in self.use_match:
                logger.warning("Narrow match not yet implemented")
            if Match.broad in self.use_match:
                logger.warning("Broad match not yet implemented")
        return sssom_lookup_table

    def _has_match(self, predicate: str, match: Match):
        """Check if a predicate has a match."""
        if match == Match.exact:
            return predicate in self.predicates[Match.exact]
        if match == Match.narrow:
            # return predicate in self.predicates["narrow"] or predicate in self.predicates[Match.exact]
            return False
        if match == Match.broad:
            # return predicate in self.predicates["broad"] or predicate in self.predicates[Match.exact]
            return False

    def _has_mapping(self, _id: str, target_prefixes: list[str] | None = None):
        """Check if an ID has a mapping."""
        if target_prefixes is None:
            return _id in self.lookup_table
        else:
            if _id not in self.lookup_table:
                return False
            for target_prefix in target_prefixes:
                if target_prefix in self.lookup_table[_id]:
                    return True
            return False  # No mapping found

    def _get_mapping(self, _id: str, target_prefixes: list[str]):
        """Get the mapping for an ID."""
        for target_prefix in target_prefixes:
            if target_prefix in self.lookup_table[_id]:
                return self.lookup_table[_id][target_prefix]
        raise KeyError(f"Could not find mapping for {_id} in {target_prefixes}: {self.lookup_table[_id]}")

    def _set_mapping(
        self,
        original_id: str,
        mapped_id: str,
        predicate: str,
        match: Match,
        lookup_table: dict[str, dict[str, str]],
    ):
        """Set a mapping for an ID."""
        original_prefix = original_id.split(":")[0]
        mapped_prefix = mapped_id.split(":")[0]

        # Collect all target prefixes from unified field mappings
        all_target_prefixes = []
        for field_config in self._unified_field_mappings.values():
            all_target_prefixes.extend(field_config['target_prefixes'])
        if (
            original_prefix in self.filter_prefixes or len(self.filter_prefixes) == 0
        ) and mapped_prefix in all_target_prefixes:
            if original_id not in lookup_table:
                lookup_table[original_id] = {}
            if mapped_prefix in lookup_table[original_id]:
                logger.warning(f"Duplicate mapping for {original_id} to {mapped_prefix}")
            elif self._has_match(predicate, match):
                lookup_table[original_id][mapped_prefix] = mapped_id
            else:
                logger.warning(
                    f"{match} match not found for {original_id} to {mapped_prefix} with predicate {predicate}"
                )
        return lookup_table
