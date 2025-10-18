# Tooling Overview

This directory consolidates auxiliary tooling that used to live at the repository root.

- `scripts/` — one-off maintenance and operational scripts. Run them from the repository root, e.g. `./tools/scripts/setup-pypi-environment.sh`.
- `static-analysis/` — service-specific configuration such as Datadog rule sets.
- `observability/` — OpenTelemetry collector configuration and related assets.

Keeping these assets together keeps the root tidy while still making the utilities easy to discover.
