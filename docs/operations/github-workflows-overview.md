# GitHub Actions Workflows

This directory contains the CI/CD workflows for AgenticFleet.

## Workflows

### Core CI/CD

#### 🔄 [ci.yml](.github/workflows/ci.yml)

Main continuous integration pipeline that runs on every push and pull request.

**Jobs:**

- **Lint**: Runs Ruff linter and Black formatter checks
- **Type Check**: Runs mypy for type checking
- **Test**: Runs tests across multiple Python versions (3.12, 3.13) and operating systems (Ubuntu, macOS, Windows)
- **Build**: Builds the Python package and validates metadata
- **Security**: Runs Bandit security scanner

**Triggers:**

- Push to `main`, `0.5.0a`, `develop` branches
- Pull requests to these branches
- Manual workflow dispatch

#### 🚀 [release.yml](.github/workflows/release.yml)

Handles package releases to PyPI and GitHub Releases.

**Jobs:**

- **Build**: Creates distribution packages
- **Publish to PyPI**: Publishes to PyPI using trusted publishing
- **Publish to TestPyPI**: Optional test publishing
- **GitHub Release**: Creates GitHub release with artifacts

**Triggers:**

- Tags matching `v*.*.*` pattern
- Manual workflow dispatch

### Security & Quality

#### 🔒 [codeql.yml](.github/workflows/codeql.yml)

GitHub's CodeQL security analysis for identifying vulnerabilities.

**Triggers:**

- Push to main branches
- Pull requests
- Weekly schedule (Monday 06:00 UTC)

#### 🔍 [dependency-review.yml](.github/workflows/dependency-review.yml)

Reviews dependencies in pull requests for security issues.

**Triggers:**

- Pull requests only

### Maintenance

#### 🤖 [stale.yml](.github/workflows/stale.yml)

Automatically marks and closes stale issues and pull requests.

**Configuration:**

- Issues: Stale after 60 days, close after 14 days
- PRs: Stale after 30 days, close after 7 days
- Exempt labels: `pinned`, `security`, `roadmap`, `in-progress`

**Triggers:**

- Daily at 01:00 UTC
- Manual workflow dispatch

#### 🏷️ [pr-labels.yml](.github/workflows/pr-labels.yml)

Automatically labels pull requests based on changed files.

**Triggers:**

- Pull request events (opened, edited, synchronize, reopened)

#### 🏷️ [label-sync.yml](.github/workflows/label-sync.yml)

Syncs repository labels from [labels.yml](labels.yml) configuration.

**Triggers:**

- Push to `main` when `labels.yml` changes
- Manual workflow dispatch

#### 🔄 [pre-commit-autoupdate.yml](.github/workflows/pre-commit-autoupdate.yml)

Automatically updates pre-commit hooks weekly.

**Triggers:**

- Weekly on Monday at 00:00 UTC
- Manual workflow dispatch

## Dependabot

[dependabot.yml](dependabot.yml) configures automatic dependency updates:

- **GitHub Actions**: Weekly updates on Monday
- **Python packages**: Weekly updates with grouped updates for:
  - Azure packages
  - Agent Framework packages
  - Development dependencies

## Issue Templates

Located in [ISSUE_TEMPLATE/](ISSUE_TEMPLATE/):

- **bug_report.yml**: Structured bug report form
- **feature_request.yml**: Feature request form
- **config.yml**: Issue template configuration with links to docs and discussions

## Pull Request Template

[pull_request_template.md](pull_request_template.md) provides a structured template for PRs including:

- Description
- Type of change
- Related issues
- Testing checklist
- Documentation updates

## Labels Configuration

[labels.yml](labels.yml) defines repository labels organized by:

- **Type**: bug, feature, enhancement, documentation, etc.
- **Priority**: critical, high, medium, low
- **Status**: in-progress, blocked, needs-review, needs-info
- **Area**: agents, workflow, tools, config, memory, cli
- **Special**: dependencies, security, good first issue, etc.

[labeler.yml](labeler.yml) maps file patterns to labels for automatic PR labeling.

## Required Secrets

Configure these secrets in repository settings for full functionality:

### PyPI Publishing

- `PYPI_API_TOKEN` (optional if using trusted publishing)

### Testing (Optional)

- `OPENAI_API_KEY`
- `AZURE_AI_PROJECT_ENDPOINT`
- `AZURE_AI_SEARCH_ENDPOINT`
- `AZURE_AI_SEARCH_KEY`
- `AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME`
- `AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME`

## Environments

Configure these environments in repository settings:

- **pypi**: For production PyPI releases
- **testpypi**: For test PyPI releases (optional)

Both should use trusted publishing (no API tokens needed) via OpenID Connect.

## Local Testing

Test workflows locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# List available workflows
act -l

# Run CI workflow
act push

# Run specific job
act -j lint
```

## Workflow Status Badges

Add these badges to your README.md:

```markdown
[![CI](https://github.com/Qredence/AgenticFleet/actions/workflows/ci.yml/badge.svg)](https://github.com/Qredence/AgenticFleet/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Qredence/AgenticFleet/actions/workflows/codeql.yml/badge.svg)](https://github.com/Qredence/AgenticFleet/actions/workflows/codeql.yml)
[![Release](https://github.com/Qredence/AgenticFleet/actions/workflows/release.yml/badge.svg)](https://github.com/Qredence/AgenticFleet/actions/workflows/release.yml)
```

## Best Practices

1. **Testing**: Always ensure tests pass locally before pushing
2. **Secrets**: Never commit secrets; use GitHub Secrets
3. **Dependencies**: Let Dependabot handle routine updates
4. **Labels**: Use automatic labeling; manually adjust if needed
5. **Releases**: Use semantic versioning (v0.5.0, v1.0.0, etc.)
6. **Security**: Monitor CodeQL and Dependabot alerts regularly

## Troubleshooting

### Workflow Fails on Secrets

If CI fails due to missing secrets (API keys), the workflow is configured with `continue-on-error: true` for tests requiring external services. This is expected for public repositories.

### Release Workflow Issues

Ensure:

1. Tag format is `v*.*.*` (e.g., `v0.5.0`)
2. PyPI environment is configured in repository settings
3. Trusted publishing is set up on PyPI

### Dependabot PRs Not Created

Check:

1. Dependabot is enabled in repository settings
2. Security alerts are enabled
3. No conflicting branch protection rules

## Contributing

When adding new workflows:

1. Add comprehensive comments
2. Update this README
3. Test locally with `act` if possible
4. Document any required secrets
5. Add appropriate error handling
