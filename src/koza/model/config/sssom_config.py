from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union, Literal

from loguru import logger
from pydantic.dataclasses import dataclass
from sssom.parsers import parse_sssom_table
from sssom.util import filter_prefixes, merge_msdf


class Match(str, Enum):
    """SSSOM match types."""

    exact = "exact"
    narrow = "narrow"
    broad = "broad"


@dataclass()
class SSSOMConfig:
    """SSSOM config options

    Attributes:
        files: List of SSSOM files to use
        filter_prefixes: Optional list of prefixes to filter by
        subject_target_prefixes: Optional list of prefixes to use for subject mapping
        object_target_prefixes: Optional list of prefixes to use for object mapping
        use_match: Optional list of match types to use
    """

    files: List[Union[str, Path]] = field(default_factory=list)
    filter_prefixes: List[str] = field(default_factory=list)
    subject_target_prefixes: List[str] = field(default_factory=list)
    object_target_prefixes: List[str] = field(default_factory=list)
    use_match: List[Match] = field(default_factory=list)

    predicates = {"exact": ["skos:exactMatch"], "narrow": ["skos:narrowMatch"], "broad": ["skos:broadMatch"]}

    def __post_init__(self):
        if not self.use_match:
            self.use_match = [Match.exact]
        logger.debug("Building SSSOM Dataframe...")
        self.df = self._merge_and_filter_sssom()
        logger.debug("Building SSSOM Lookup Table...")
        self.lut = self._build_sssom_lut()  # use_match=self.use_match)

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
        mapping_sets = []
        for file in self.files:
            msdf = parse_sssom_table(file)
            mapping_sets.append(msdf)
        new_msdf = merge_msdf(*mapping_sets)
        filters = (self.subject_target_prefixes + self.object_target_prefixes) + list(
            set(self.filter_prefixes) - set(self.subject_target_prefixes) - set(self.object_target_prefixes)
        )
        logger.debug(f"Filtering SSSOM by {filters}")
        new_msdf = filter_prefixes(
            df=new_msdf.df, filter_prefixes=filters, require_all_prefixes=False, features=new_msdf.df.columns  # type: ignore
        )

        return new_msdf

    def _build_sssom_lut(self) -> Dict:
        """Build a lookup table from SSSOM mapping dataframe."""
        # TODO add narrow and broad match mappings
        sssom_lut = {}
        for _, row in self.df.iterrows():
            subject_id = row["subject_id"]
            object_id = row["object_id"]
            predicate = row["predicate_id"]
            if Match.exact in self.use_match:
                # Add exact match mappings in both directions
                sssom_lut = self._set_mapping(subject_id, object_id, predicate, match="exact", lut=sssom_lut)
                sssom_lut = self._set_mapping(object_id, subject_id, predicate, match="exact", lut=sssom_lut)
            if Match.narrow in self.use_match:
                logger.warning("Narrow match not yet implemented")
            if Match.broad in self.use_match:
                logger.warning("Broad match not yet implemented")
        return sssom_lut

    def _has_match(self, predicate, match: Literal[Match.exact, Match.narrow, Match.broad]):
        """Check if a predicate has a match."""
        if match == Match.exact:
            return predicate in self.predicates[Match.exact]
        if match == Match.narrow:
            # return predicate in self.predicates["narrow"] or predicate in self.predicates[Match.exact]
            return False
        if match == Match.broad:
            # return predicate in self.predicates["broad"] or predicate in self.predicates[Match.exact]
            return False

    def _has_mapping(self, id, target_prefixes=None):
        """Check if an ID has a mapping."""
        if target_prefixes is None:
            return id in self.lut
        else:
            if id not in self.lut:
                return False
            for target_prefix in target_prefixes:
                if target_prefix in self.lut[id]:
                    return True
            return False  # No mapping found

    def _get_mapping(self, id, target_prefixes):
        """Get the mapping for an ID."""
        for target_prefix in target_prefixes:
            if target_prefix in self.lut[id]:
                return self.lut[id][target_prefix]
        raise KeyError(f"Could not find mapping for {id} in {target_prefixes}: {self.lut[id]}")

    def _set_mapping(
        self,
        original_id,
        mapped_id,
        predicate,
        match: Literal[Match.exact, Match.narrow, Match.broad],
        lut: Dict[str, dict],
    ):
        """Set a mapping for an ID."""
        original_prefix = original_id.split(":")[0]
        mapped_prefix = mapped_id.split(":")[0]
        target_prefixes = self.subject_target_prefixes + self.object_target_prefixes
        if (
            original_prefix in self.filter_prefixes or len(self.filter_prefixes) == 0
        ) and mapped_prefix in target_prefixes:
            if original_id not in lut:
                lut[original_id] = {}
            if mapped_prefix in lut[original_id]:
                logger.warning(f"Duplicate mapping for {original_id} to {mapped_prefix}")
            elif self._has_match(predicate, match):
                lut[original_id][mapped_prefix] = mapped_id
            else:
                logger.warning(
                    f"{match} match not found for {original_id} to {mapped_prefix} with predicate {predicate}"
                )
        return lut
