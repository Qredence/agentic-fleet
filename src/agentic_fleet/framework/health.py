"""Health checks for Microsoft Agent Framework integration."""

import logging
from typing import Any

import pkg_resources  # type: ignore
from fastapi import HTTPException

logger = logging.getLogger(__name__)

try:
    from packaging.version import InvalidVersion, Version
except ImportError:  # fallback if packaging not available
    logger.warning(
        "Could not import 'packaging.version.Version'. "
        "Falling back to simple string comparison for version checks. "
        "This may not correctly detect outdated packages if version strings are not lexically ordered."
    )
    Version = None
    InvalidVersion = Exception

# Required agent-framework packages with minimum versions
REQUIRED_PACKAGES: dict[str, str] = {
    "agent-framework": "1.2.0",
    "agent-framework-core": "1.2.0",
    "agent-framework-a2a": "1.2.0",
    "agent-framework-azure-ai": "1.2.0",
    "agent-framework-mem0": "1.2.0",
    "agent-framework-redis": "1.2.0",
    "agent-framework-devui": "1.2.0",
}


def _is_outdated(installed: str, required: str) -> bool:
    """Return True if installed version is older than required."""
    if Version is None:
        # Fallback: simple lexical compare (not fully semver accurate)
        return installed < required
    try:
        return Version(installed) < Version(required)  # type: ignore
    except InvalidVersion:
        return installed < required


def check_package_versions() -> dict[str, dict[str, str | None]]:
    """Return mapping of required package versions and their status.

    Structure:
            {
                    "package_name": {
                            "required": "<required_version>",
                            "installed": "<installed_version>|None",
                            "status": "ok|missing|outdated|error: <msg>"
                    },
                    ...
            }
    """
    results: dict[str, dict[str, str | None]] = {}
    for pkg_name, required_version in REQUIRED_PACKAGES.items():
        try:
            installed_version = pkg_resources.get_distribution(pkg_name).version
            status = "outdated" if _is_outdated(installed_version, required_version) else "ok"
            results[pkg_name] = {
                "required": required_version,
                "installed": installed_version,
                "status": status,
            }
        except pkg_resources.DistributionNotFound:
            results[pkg_name] = {
                "required": required_version,
                "installed": None,
                "status": f"error: package '{pkg_name}' not found",
            }
        except Exception as e:  # catch unexpected metadata errors
            logger.error("Error checking package %s: %s", pkg_name, e)
            results[pkg_name] = {
                "required": required_version,
                "installed": None,
                "status": f"error: {e!s}",
            }
    return results


def check_framework_health() -> tuple[bool, dict[str, Any]]:
    """Perform framework health checks synchronously.

    Returns:
            (is_healthy, details) where details contains:
                    {
                            "packages": "<package_version_mapping>",
                            "status": "ok" | "degraded" | "error"
                    }
    """
    try:
        packages = check_package_versions()
        has_errors = any(
            (pkg_info["status"] in ("missing", "error"))
            or (isinstance(pkg_info["status"], str) and pkg_info["status"].startswith("error:"))
            for pkg_info in packages.values()
        )
        has_warnings = any(pkg_info["status"] == "outdated" for pkg_info in packages.values())
        if has_errors:
            return False, {"packages": packages, "status": "error"}
        if has_warnings:
            return True, {"packages": packages, "status": "degraded"}
        return True, {"packages": packages, "status": "ok"}
    except Exception as e:
        logger.error("Error in framework health check: %s", e)
        return False, {"error": str(e), "status": "error"}


class FrameworkHealthError(HTTPException):  # type: ignore
    """Raised when framework health checks fail."""

    def __init__(
        self,
        status_code: int = 503,
        detail: str | None = None,
        health_status: dict[str, Any] | None = None,
    ) -> None:
        if detail is None:
            detail = "Microsoft Agent Framework health check failed"
        if health_status:
            detail = f"{detail}: {health_status}"
        super().__init__(status_code=status_code, detail=detail)
        self.health_status = health_status or {}


def verify_framework_health() -> None:
    """Verify framework health and raise FrameworkHealthError when unhealthy."""
    is_healthy, health_status = check_framework_health()
    if not is_healthy:
        raise FrameworkHealthError(health_status=health_status)


__all__ = [
    "REQUIRED_PACKAGES",
    "FrameworkHealthError",
    "check_framework_health",
    "check_package_versions",
    "verify_framework_health",
]
