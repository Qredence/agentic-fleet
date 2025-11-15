"""
Tests for enhanced cache invalidation with signature and config hashes.
"""

import os
import tempfile
from pathlib import Path

from agentic_fleet.utils.compiler import (
    _compute_config_hash,
    _compute_signature_hash,
    _get_cache_metadata,
    _is_cache_valid,
    _save_cache_metadata,
)


class TestCacheHashing:
    """Test signature and config hash computation."""

    def test_compute_signature_hash(self):
        """Test that signature hash is computed correctly."""
        hash_value = _compute_signature_hash()

        # Hash should be a 16-character hex string
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_compute_signature_hash_consistent(self):
        """Test that signature hash is consistent across calls."""
        hash1 = _compute_signature_hash()
        hash2 = _compute_signature_hash()

        assert hash1 == hash2

    def test_compute_config_hash(self):
        """Test that config hash is computed correctly."""
        hash_value = _compute_config_hash(
            dspy_model="gpt-4",
            optimizer="bootstrap",
            gepa_options={"max_metric_calls": 100},
            agent_config={"Researcher": {"tools": ["TavilySearchTool"]}},
        )

        assert isinstance(hash_value, str)
        assert len(hash_value) == 16

    def test_compute_config_hash_different_for_different_configs(self):
        """Test that different configs produce different hashes."""
        hash1 = _compute_config_hash(
            dspy_model="gpt-4",
            optimizer="bootstrap",
        )
        hash2 = _compute_config_hash(
            dspy_model="gpt-5-mini",
            optimizer="bootstrap",
        )

        assert hash1 != hash2

    def test_compute_config_hash_same_for_same_configs(self):
        """Test that same configs produce same hashes."""
        config = {
            "dspy_model": "gpt-4",
            "optimizer": "bootstrap",
            "gepa_options": {"max_metric_calls": 100},
        }

        hash1 = _compute_config_hash(**config)
        hash2 = _compute_config_hash(**config)

        assert hash1 == hash2


class TestCacheMetadata:
    """Test cache metadata with hashes."""

    def test_save_cache_metadata_with_hashes(self):
        """Test that cache metadata includes signature and config hashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test.pkl")
            examples_path = os.path.join(tmpdir, "examples.json")

            # Create dummy examples file
            Path(examples_path).touch()

            _save_cache_metadata(
                cache_path,
                examples_path,
                signature_hash="abc123",
                config_hash="def456",
            )

            metadata = _get_cache_metadata(cache_path)

            assert metadata is not None
            assert metadata["signature_hash"] == "abc123"
            assert metadata["config_hash"] == "def456"

    def test_is_cache_valid_with_hash_mismatch(self):
        """Test that cache is invalid when hashes don't match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test.pkl")
            examples_path = os.path.join(tmpdir, "examples.json")

            # Create dummy files
            Path(cache_path).touch()
            Path(examples_path).touch()

            # Save metadata with one hash
            _save_cache_metadata(
                cache_path,
                examples_path,
                signature_hash="abc123",
                config_hash="def456",
            )

            # Check with different hash - should be invalid
            is_valid = _is_cache_valid(
                cache_path,
                examples_path,
                optimizer="bootstrap",
                signature_hash="xyz789",  # Different hash
                config_hash="def456",
            )

            assert is_valid is False

    def test_is_cache_valid_with_matching_hashes(self):
        """Test that cache is valid when hashes match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test.pkl")
            examples_path = os.path.join(tmpdir, "examples.json")

            # Create dummy files
            Path(cache_path).touch()
            Path(examples_path).touch()

            # Save metadata with hashes
            signature_hash = "abc123"
            config_hash = "def456"
            _save_cache_metadata(
                cache_path,
                examples_path,
                signature_hash=signature_hash,
                config_hash=config_hash,
            )

            # Check with matching hashes - should be valid
            is_valid = _is_cache_valid(
                cache_path,
                examples_path,
                optimizer="bootstrap",
                signature_hash=signature_hash,
                config_hash=config_hash,
            )

            assert is_valid is True
