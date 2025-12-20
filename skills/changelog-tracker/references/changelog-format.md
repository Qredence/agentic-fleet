# Changelog format (AgenticFleet)

## Structure

- Keep a top-level **Unreleased** section if present.
- Use clear, concise bullets.
- Prefer these subsections when applicable:
  - Highlights
  - Backend
  - Frontend
  - Docs
  - Tests
  - CI/Infra
  - Security
  - Migration Notes

## Categorization hints

- **Backend**: `src/agentic_fleet/`
- **Frontend**: `src/frontend/`
- **Docs**: `docs/`, root `.md` files
- **Tests**: `tests/`
- **CI/Infra**: `.github/`, `docker/`, `infrastructure/`
- **Scripts/Tools**: `scripts/`

## Tone

- Lead with user-facing impact.
- Keep each bullet under ~2 lines.
- If a change is internal only, say so explicitly.
- Add small migration notes if behavior/config changes.
