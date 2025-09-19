from koza.model.config.sssom_config import SSSOMConfig, FieldMapping

sssom_files = ["tests/resources/sssom/testmapping.sssom.tsv", "tests/resources/sssom/testmapping2.sssom.tsv"]


def test_basic_mapping():
    sssom_config = SSSOMConfig(
        files=sssom_files,
        filter_prefixes=["A", "B", "SOMETHINGELSE"],
        subject_target_prefixes=["B"],
        object_target_prefixes=["X"],
    )
    print(sssom_config.use_match)
    edge = {
        "subject": "A:123",
        "object": "SOMETHINGELSE:456",
    }
    mapped = sssom_config.apply_mapping(edge)
    assert mapped["subject"] == "B:987"


def test_merge_and_filter():
    sssom_config = SSSOMConfig(
        files=sssom_files,
        filter_prefixes=["A", "B"],
    )
    df = sssom_config.df
    assert "A:123" in df["subject_id"].values
    assert "B:987" in df["object_id"].values
    assert "X:111" not in df["object_id"].values and "X:111" not in df["subject_id"].values


def test_exact_match_is_bidirectional():
    sssom_config = SSSOMConfig(
        files=sssom_files, filter_prefixes=["A", "B"], subject_target_prefixes=["B"], object_target_prefixes=["B"]
    )

    edge = {
        "subject": "A:123",
        "object": "SOMETHINGELSE:456",
    }
    mapped = sssom_config.apply_mapping(edge)
    assert mapped["subject"] == "B:987"

    edge = {"subject": "SOMETHINGELSE:123", "object": "A:420"}
    mapped = sssom_config.apply_mapping(edge)
    assert mapped["object"] == "B:000"


def test_narrow_match():
    pass


def test_broad_match():
    pass


def test_field_target_mappings():
    """Test new field_target_mappings functionality."""
    sssom_config = SSSOMConfig(
        files=sssom_files,
        filter_prefixes=["A", "B", "SOMETHINGELSE"],
        field_target_mappings={
            "subject": ["B"],
            "object": ["X"],
            "predicate": ["RO"],
            "category": ["BIOLINK"]
        }
    )

    entity = {
        "subject": "A:123",
        "object": "SOMETHINGELSE:456",
        "predicate": "skos:relatedMatch",
        "category": "biolink:Association"
    }

    mapped = sssom_config.apply_mapping(entity)

    # Check that subject was mapped
    assert mapped["subject"] == "B:987"
    assert mapped["original_subject"] == "A:123"

    # Check that object was not mapped (no X mappings in test files)
    assert mapped["object"] == "SOMETHINGELSE:456"
    assert "original_object" not in mapped

    # Check other fields not mapped (no mappings available)
    assert mapped["predicate"] == "skos:relatedMatch"
    assert "original_predicate" not in mapped


def test_backward_compatibility_with_field_target_mappings():
    """Test that deprecated subject_target_prefixes and object_target_prefixes still work."""
    sssom_config = SSSOMConfig(
        files=sssom_files,
        filter_prefixes=["A", "B", "SOMETHINGELSE"],
        subject_target_prefixes=["B"],
        object_target_prefixes=["X"],
    )

    # Should work the same as the old implementation
    edge = {
        "subject": "A:123",
        "object": "SOMETHINGELSE:456",
    }
    mapped = sssom_config.apply_mapping(edge)
    assert mapped["subject"] == "B:987"
    assert mapped["original_subject"] == "A:123"


def test_field_target_mappings_precedence():
    """Test that field_target_mappings takes precedence over deprecated parameters."""
    sssom_config = SSSOMConfig(
        files=sssom_files,
        filter_prefixes=["A", "B", "SOMETHINGELSE"],
        subject_target_prefixes=["X"],  # This should be ignored
        field_target_mappings={
            "subject": ["B"],  # This should take precedence
        }
    )

    edge = {
        "subject": "A:123",
    }
    mapped = sssom_config.apply_mapping(edge)
    assert mapped["subject"] == "B:987"  # Should use field_target_mappings, not deprecated setting


# Tests for new API structure

def test_new_api_basic_field_mapping():
    """Test new API with basic field mapping structure."""
    sssom_config = SSSOMConfig(
        files=sssom_files,
        filter_prefixes=["A", "B", "SOMETHINGELSE"],
        field_mappings={
            "subject": FieldMapping(
                target_prefixes=["B"],
                preserve_original=True
            ),
            "object": FieldMapping(
                target_prefixes=["X"],
                preserve_original=False
            )
        }
    )

    entity = {
        "subject": "A:123",
        "object": "SOMETHINGELSE:456",
    }
    mapped = sssom_config.apply_mapping(entity)

    # Subject should be mapped and preserved
    assert mapped["subject"] == "B:987"
    assert mapped["original_subject"] == "A:123"

    # Object should not be mapped (no X mappings in test files)
    assert mapped["object"] == "SOMETHINGELSE:456"
    assert "original_object" not in mapped  # preserve_original=False


def test_new_api_per_field_files():
    """Test new API with per-field SSSOM files."""
    sssom_config = SSSOMConfig(
        field_mappings={
            "subject": FieldMapping(
                files=sssom_files,  # Per-field files only
                target_prefixes=["B"],
                preserve_original=True
            )
        }
    )

    entity = {"subject": "A:123"}
    mapped = sssom_config.apply_mapping(entity)

    assert mapped["subject"] == "B:987"
    assert mapped["original_subject"] == "A:123"


def test_new_api_global_files_only():
    """Test new API using only global files."""
    sssom_config = SSSOMConfig(
        files=sssom_files,  # Global files only
        field_mappings={
            "subject": FieldMapping(
                target_prefixes=["B"],
                preserve_original=True
            )
        }
    )

    entity = {"subject": "A:123"}
    mapped = sssom_config.apply_mapping(entity)

    assert mapped["subject"] == "B:987"
    assert mapped["original_subject"] == "A:123"


def test_new_api_mixed_files():
    """Test new API with mix of global and field-specific files."""
    sssom_config = SSSOMConfig(
        files=[sssom_files[0]],  # Global file
        field_mappings={
            "subject": FieldMapping(
                files=[sssom_files[1]],  # Additional field-specific file
                target_prefixes=["B"],
                preserve_original=True
            )
        }
    )

    entity = {"subject": "A:123"}
    mapped = sssom_config.apply_mapping(entity)

    assert mapped["subject"] == "B:987"
    assert mapped["original_subject"] == "A:123"


def test_new_api_preservation_control():
    """Test preserve_original boolean control."""
    sssom_config = SSSOMConfig(
        files=sssom_files,
        field_mappings={
            "subject": FieldMapping(
                target_prefixes=["B"],
                preserve_original=True  # Should preserve
            ),
            "object": FieldMapping(
                target_prefixes=["B"],
                preserve_original=False  # Should not preserve
            )
        }
    )

    entity = {
        "subject": "A:123",
        "object": "A:420"  # This should map to B:000 based on test files
    }
    mapped = sssom_config.apply_mapping(entity)

    # Subject preserved
    assert "original_subject" in mapped
    # Object not preserved
    assert "original_object" not in mapped


def test_new_api_custom_original_field_names():
    """Test custom original field names."""
    sssom_config = SSSOMConfig(
        files=sssom_files,
        field_mappings={
            "subject": FieldMapping(
                target_prefixes=["B"],
                preserve_original=True,
                original_field_name="source_subject"  # Custom name
            ),
            "predicate": FieldMapping(
                target_prefixes=["RO"],
                preserve_original=True,
                original_field_name="original_predicate"  # Standard name
            )
        }
    )

    entity = {"subject": "A:123"}
    mapped = sssom_config.apply_mapping(entity)

    assert mapped["subject"] == "B:987"
    assert mapped["source_subject"] == "A:123"  # Custom field name
    assert "original_subject" not in mapped  # Standard name should not exist


def test_new_api_validation_no_files():
    """Test validation error when no files are specified anywhere."""
    try:
        sssom_config = SSSOMConfig(
            field_mappings={
                "subject": FieldMapping(
                    target_prefixes=["B"],
                    preserve_original=True
                )
            }
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "At least one SSSOM file must be specified" in str(e)


def test_new_api_backward_compatibility():
    """Test that old API still works with new implementation."""
    # Old API should still work
    sssom_config = SSSOMConfig(
        files=sssom_files,
        filter_prefixes=["A", "B", "SOMETHINGELSE"],
        subject_target_prefixes=["B"],
        object_target_prefixes=["X"],
    )

    entity = {
        "subject": "A:123",
        "object": "SOMETHINGELSE:456",
    }
    mapped = sssom_config.apply_mapping(entity)

    assert mapped["subject"] == "B:987"
    assert mapped["original_subject"] == "A:123"
