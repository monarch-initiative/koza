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
class SSSOMConfig:
    """SSSOM config options

    :param files: SSSOM files to use
    :param filter_prefixes: Prefixes to filter by
    :param subject_target_prefixes: Prefixes to use for subject mapping
    :param object_target_prefixes: Prefixes to use for object mapping
    :param use_match: Match types to use
    """

    files: Sequence[str | Path] = field(default_factory=list)
    filter_prefixes: list[str] = field(default_factory=list)
    subject_target_prefixes: list[str] = field(default_factory=list)
    object_target_prefixes: list[str] = field(default_factory=list)
    use_match: list[Match] = field(default_factory=list)

    predicates = {
        "exact": ["skos:exactMatch"],
        "narrow": ["skos:narrowMatch"],
        "broad": ["skos:broadMatch"],
    }

    def __post_init__(self):
        if not self.use_match:
            self.use_match = [Match.exact]
        logger.debug("Building SSSOM Dataframe...")
        self.df = self._merge_and_filter_sssom()
        logger.debug("Building SSSOM Lookup Table...")
        self.lookup_table = self._build_sssom_lookup_table()  # use_match=self.use_match)

    def apply_mapping(self, entity: dict) -> dict:
        """Apply SSSOM mappings to an edge record."""

        if self._has_mapping(entity["subject"], self.subject_target_prefixes):
            entity["original_subject"] = entity["subject"]
            entity["subject"] = self._get_mapping(entity["subject"], self.subject_target_prefixes)

        if self._has_mapping(entity["object"], self.object_target_prefixes):
            entity["original_object"] = entity["object"]
            entity["object"] = self._get_mapping(entity["object"], self.object_target_prefixes)

        return entity

    def _merge_and_filter_sssom(self):
        mapping_sets: list[MappingSetDataFrame] = []
        for file in self.files:
            msdf = parse_sssom_table(file)
            mapping_sets.append(msdf)
        merged_msdf = merge_msdf(*mapping_sets)
        filters = [
            *self.subject_target_prefixes,
            *self.object_target_prefixes,
            *(set(self.filter_prefixes) - set(self.subject_target_prefixes) - set(self.object_target_prefixes)),
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
        target_prefixes = self.subject_target_prefixes + self.object_target_prefixes
        if (
            original_prefix in self.filter_prefixes or len(self.filter_prefixes) == 0
        ) and mapped_prefix in target_prefixes:
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
