#!/usr/bin/env python3
"""API Health Check Script

Quick script to verify all API endpoints are working correctly.
Run this to diagnose API connectivity issues.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx


async def check_endpoint(
    client: httpx.AsyncClient, name: str, method: str, url: str, **kwargs: Any
) -> tuple[bool, str]:
    """Check a single endpoint."""
    try:
        response = await client.request(method, url, timeout=10.0, **kwargs)
        if response.status_code < 400:
            return True, f"✓ {name}: {response.status_code}"
        return False, f"✗ {name}: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return False, f"✗ {name}: {str(e)[:100]}"


@dataclass(frozen=True)
class Endpoint:
    name: str
    method: str
    path: str
    kwargs: Mapping[str, Any] | None = None


async def main() -> None:
    """Run API health checks."""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    print(f"🔍 Testing API endpoints at {base_url}\n")

    async with httpx.AsyncClient() as client:
        checks: Sequence[Endpoint] = (
            Endpoint("Root", "GET", "/"),
            Endpoint("Health", "GET", "/v1/system/health"),
            Endpoint("Create Session", "POST", "/v1/sessions"),
            Endpoint("List Conversations", "GET", "/v1/conversations"),
            Endpoint("Create Conversation", "POST", "/v1/conversations", {"json": {}}),
            Endpoint("List Approvals", "GET", "/v1/approvals"),
        )

        results: list[tuple[bool, str]] = []
        for check in checks:
            url = urljoin(base_url, check.path)
            extra_kwargs = dict(check.kwargs or {})
            success, message = await check_endpoint(
                client,
                check.name,
                check.method,
                url,
                **extra_kwargs,
            )
            results.append((success, message))
            print(message)

        # Summary
        print("\n" + "=" * 60)
        passed = sum(1 for success, _ in results if success)
        total = len(results)
        print(f"Results: {passed}/{total} passed")

        if passed == total:
            print("✅ All API endpoints are working!")
            sys.exit(0)
        else:
            print("❌ Some endpoints failed. Check the errors above.")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
