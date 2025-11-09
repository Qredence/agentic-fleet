"""Tests for framework health checks."""

import unittest
from unittest.mock import MagicMock, patch

from agentic_fleet.framework.health import (
    FrameworkHealthError,
    check_framework_health,
    check_package_versions,
    verify_framework_health,
)


class TestFrameworkHealth(unittest.TestCase):
    """Test framework health check functionality."""

    @patch("pkg_resources.get_distribution")
    def test_check_package_versions_healthy(self, mock_get_dist):
        """Test that check_package_versions returns healthy status when all packages are up to date."""
        # Mock package versions
        mock_dist = MagicMock()
        mock_dist.version = "1.2.0"
        mock_get_dist.return_value = mock_dist

        # Mock REQUIRED_PACKAGES to only check one package for testing
        with patch.dict(
            "agentic_fleet.framework.health.REQUIRED_PACKAGES",
            {"test-package": "1.0.0"},
            clear=True,
        ):
            results = check_package_versions()

        # Should have the test package
        self.assertEqual(len(results), 1)
        self.assertIn("test-package", results)
        self.assertEqual(results["test-package"]["status"], "ok")
        self.assertEqual(results["test-package"]["installed"], "1.2.0")
        self.assertEqual(results["test-package"]["required"], "1.0.0")

    @patch("pkg_resources.get_distribution")
    def test_check_package_versions_outdated(self, mock_get_dist):
        """Test that check_package_versions detects outdated packages."""
        # Mock package versions with some outdated
        mock_dist = MagicMock()
        mock_dist.version = "0.9.0"  # Older than required 1.0.0
        mock_get_dist.return_value = mock_dist

        # Mock REQUIRED_PACKAGES to only check one package for testing
        with patch.dict(
            "agentic_fleet.framework.health.REQUIRED_PACKAGES",
            {"test-package": "1.0.0"},
            clear=True,
        ):
            results = check_package_versions()

        # The test package should be marked as outdated
        self.assertEqual(len(results), 1)
        self.assertEqual(results["test-package"]["status"], "outdated")
        self.assertEqual(results["test-package"]["installed"], "0.9.0")

    @patch("pkg_resources.get_distribution")
    def test_check_package_versions_missing(self, mock_get_dist):
        """Test that check_package_versions handles missing packages."""
        # Simulate missing package
        mock_get_dist.side_effect = Exception("Package not found")

        # Mock REQUIRED_PACKAGES to only check one package for testing
        with patch.dict(
            "agentic_fleet.framework.health.REQUIRED_PACKAGES",
            {"missing-package": "1.0.0"},
            clear=True,
        ):
            results = check_package_versions()

        # The test package should be marked as error with the error message
        self.assertEqual(len(results), 1)
        self.assertIn("error: ", results["missing-package"]["status"])
        self.assertIsNone(results["missing-package"]["installed"])

    @patch("agentic_fleet.framework.health.check_package_versions")
    def test_check_framework_health_healthy(self, mock_check_versions):
        """Test that check_framework_health returns healthy status."""
        # Mock healthy package versions
        mock_check_versions.return_value = {
            "agent-framework": {"status": "ok", "installed": "1.2.0", "required": "1.2.0"},
            "agent-framework-core": {"status": "ok", "installed": "1.2.0", "required": "1.2.0"},
        }

        is_healthy, status = check_framework_health()

        self.assertTrue(is_healthy)
        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["packages"], mock_check_versions.return_value)

    @patch("agentic_fleet.framework.health.check_package_versions")
    def test_check_framework_health_degraded(self, mock_check_versions):
        """Test that check_framework_health detects degraded status."""
        # Mock some outdated packages
        mock_check_versions.return_value = {
            "agent-framework": {"status": "outdated", "installed": "1.1.0", "required": "1.2.0"},
            "agent-framework-core": {"status": "ok", "installed": "1.2.0", "required": "1.2.0"},
        }

        is_healthy, status = check_framework_health()

        # Should still be considered healthy but with degraded status
        self.assertTrue(is_healthy)
        self.assertEqual(status["status"], "degraded")

    @patch("agentic_fleet.framework.health.check_package_versions")
    def test_check_framework_health_error(self, mock_check_versions):
        """Test that check_framework_health detects error status."""
        # Mock missing packages
        mock_check_versions.return_value = {
            "agent-framework": {"status": "missing", "installed": None, "required": "1.2.0"},
            "agent-framework-core": {"status": "ok", "installed": "1.2.0", "required": "1.2.0"},
        }

        is_healthy, status = check_framework_health()

        self.assertFalse(is_healthy)
        self.assertEqual(status["status"], "error")

    @patch("agentic_fleet.framework.health.check_framework_health")
    def test_verify_framework_health_raises_on_error(self, mock_check_health):
        """Test that verify_framework_health raises FrameworkHealthError on error."""
        mock_check_health.return_value = (False, {"status": "error", "details": "test error"})

        with self.assertRaises(FrameworkHealthError) as ctx:
            verify_framework_health()

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.health_status["status"], "error")

    @patch("agentic_fleet.framework.health.check_framework_health")
    def test_verify_framework_health_passes_when_healthy(self, mock_check_health):
        """Test that verify_framework_health passes when healthy."""
        mock_check_health.return_value = (True, {"status": "ok"})
        # Should not raise
        verify_framework_health()

    def test_framework_health_error_initialization(self):
        """Test FrameworkHealthError initialization."""
        health_status = {"status": "error", "details": "test"}
        error = FrameworkHealthError(
            status_code=503,
            detail="Test error",
            health_status=health_status,
        )

        self.assertEqual(error.status_code, 503)
        self.assertEqual(error.detail, f"Test error: {health_status}")
        self.assertEqual(error.health_status, health_status)
