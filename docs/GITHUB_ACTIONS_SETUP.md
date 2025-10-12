# GitHub Actions Setup Complete

## ✅ Workflows Created

The following GitHub Actions workflows have been successfully created for the AgenticFleet repository:

### 1. **CI Pipeline** (`.github/workflows/ci.yml`)

Enhanced continuous integration with:

- Multi-OS testing (Ubuntu, macOS, Windows)
- Python 3.12 & 3.13 support
- Separate jobs for linting, type-checking, testing, building, and security
- Coverage reports generated during pytest
- Concurrency controls to cancel outdated runs

### 2. **Release Workflow** (`.github/workflows/release.yml`)

Automated releases with:

- PyPI trusted publishing (no API tokens needed)
- TestPyPI support for testing
- GitHub Releases creation
- Artifact uploads

### 3. **CodeQL Analysis** (`.github/workflows/codeql.yml`)

Security scanning with:

- Advanced security queries
- Weekly scheduled scans
- Automatic vulnerability detection

### 4. **Dependency Review** (`.github/workflows/dependency-review.yml`)

PR dependency scanning:

- Checks for vulnerable dependencies
- Posts summary in PRs
- Fails on moderate+ severity

### 5. **Stale Issues/PRs** (`.github/workflows/stale.yml`)

Automatic maintenance:

- Marks stale issues/PRs
- Configurable timeouts
- Exempt labels support

### 6. **Auto PR Labeling** (`.github/workflows/pr-labels.yml`)

Automatic labeling based on:

- Changed file paths
- Intelligent area detection
- Type classification

### 7. **Label Sync** (`.github/workflows/label-sync.yml`)

Maintains consistent labels from config

### 8. **Pre-commit Auto-update** (`.github/workflows/pre-commit-autoupdate.yml`)

Weekly hook updates via automated PRs

## 📋 Configuration Files Created

### Dependabot (`.github/dependabot.yml`)

- Weekly dependency updates
- Grouped updates for Azure, Agent Framework, and dev dependencies
- GitHub Actions updates

### Issue Templates

- **Bug Report** (`.github/ISSUE_TEMPLATE/bug_report.yml`)
- **Feature Request** (`.github/ISSUE_TEMPLATE/feature_request.yml`)
- **Config** (`.github/ISSUE_TEMPLATE/config.yml`)

### Labels Configuration

- **labels.yml** - Comprehensive label definitions
- **labeler.yml** - Automatic PR labeling rules

### Templates

- **Pull Request Template** (`.github/pull_request_template.md`)

## 📚 Documentation Created

- **Workflows README** (`.github/README.md`) - Complete workflow documentation
- **Security Policy** (`SECURITY.md`) - Security reporting guidelines

## 🔧 Project Updates

Updated `pyproject.toml`:

- Added `pytest-cov>=6.0.0` for code coverage

## 🚀 Next Steps

### 1. Configure Repository Settings

#### Enable Required Features

Go to **Settings → General**:

- ✅ Enable Issues
- ✅ Enable Discussions (recommended)
- ✅ Enable Sponsorships (optional)

#### Branch Protection Rules

Go to **Settings → Branches → Add rule** for `main` and `0.5.0a`:

```
Branch name pattern: main (or 0.5.0a)
☑ Require pull request before merging
  ☑ Require approvals: 1
☑ Require status checks to pass
  ☑ Require branches to be up to date
  - lint
  - type-check
  - test
☑ Require conversation resolution before merging
☑ Do not allow bypassing the above settings
```

### 2. Configure Secrets

Go to **Settings → Secrets and variables → Actions**:

#### Required for Testing (Optional for Public Repos)

```
OPENAI_API_KEY
AZURE_AI_PROJECT_ENDPOINT
AZURE_AI_SEARCH_ENDPOINT
AZURE_AI_SEARCH_KEY
AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME
AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME
```

#### Optional Services

_None currently required._

### 3. Configure PyPI Publishing

#### Option A: Trusted Publishing (Recommended)

1. Go to [PyPI](https://pypi.org) → Account Settings → Publishing
2. Add a new pending publisher:
   - **PyPI Project Name**: `agentic-fleet`
   - **Owner**: `Qredence`
   - **Repository**: `AgenticFleet`
   - **Workflow**: `release.yml`
   - **Environment**: `pypi`

#### Option B: API Token (Alternative)

1. Generate API token on PyPI
2. Add as secret: `PYPI_API_TOKEN`

### 4. Configure Environments

Go to **Settings → Environments**:

#### Create `pypi` Environment

- **Deployment branches**: Selected tags matching `v[0-9]+.[0-9]+.[0-9]+*`
  - Note: Use this exact pattern (not `v*.*.*` which causes "Name is invalid" error)
- **Environment secrets**: (if not using trusted publishing)
  - `PYPI_API_TOKEN`

#### Create `testpypi` Environment (Optional)

- **Deployment branches**: Any branch
- **Environment secrets**:
  - `TEST_PYPI_API_TOKEN`

### 5. Enable Dependabot

Go to **Settings → Security → Code security and analysis**:

- ✅ Dependency graph
- ✅ Dependabot alerts
- ✅ Dependabot security updates

### 6. Sync Labels

Run the label sync workflow manually:

```bash
gh workflow run label-sync.yml
```

Or push the `.github/labels.yml` file to main.

### 7. Add Status Badges

Add to your `README.md`:

```markdown
[![CI](https://github.com/Qredence/AgenticFleet/actions/workflows/ci.yml/badge.svg)](https://github.com/Qredence/AgenticFleet/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Qredence/AgenticFleet/actions/workflows/codeql.yml/badge.svg)](https://github.com/Qredence/AgenticFleet/actions/workflows/codeql.yml)
[![Release](https://github.com/Qredence/AgenticFleet/actions/workflows/release.yml/badge.svg)](https://github.com/Qredence/AgenticFleet/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
```

### 8. Update Dependencies

Install the new dependency:

```bash
uv sync
```

### 9. Create First Release

When ready to release:

```bash
# Create and push a tag
git tag v0.5.0
git push origin v0.5.0

# Or use GitHub CLI
gh release create v0.5.0 --title "AgenticFleet v0.5.0" --notes "Initial release"
```

## 📊 Workflow Features

### CI Pipeline Improvements

- **Parallel Execution**: Lint, type-check, and tests run in parallel
- **Matrix Testing**: Multiple Python versions and OSes
- **Smart Caching**: UV caching for faster builds
- **Coverage Reports**: Integrated code coverage
- **Artifact Upload**: Build artifacts saved for 7 days

### Security Features

- **CodeQL**: Weekly security scans
- **Dependabot**: Automatic dependency updates
- **Bandit**: Python security linting
- **Dependency Review**: PR vulnerability checks

### Automation Features

- **Auto-labeling**: PRs labeled by file changes
- **Stale Management**: Auto-close inactive issues/PRs
- **Pre-commit Updates**: Weekly hook updates
- **Release Automation**: One-command releases

## 🧪 Testing Workflows Locally

Install [act](https://github.com/nektos/act):

```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

Run workflows:

```bash
# List all workflows
act -l

# Run CI workflow
act push

# Run specific job
act -j lint

# With secrets
act -j test --secret-file .env.secrets
```

## 📝 Workflow Triggers Summary

| Workflow | Push | PR | Schedule | Manual |
|----------|------|-----|----------|--------|
| CI | ✅ | ✅ | ❌ | ✅ |
| Release | ❌ (tags) | ❌ | ❌ | ✅ |
| CodeQL | ✅ | ✅ | ✅ Weekly | ❌ |
| Dependency Review | ❌ | ✅ | ❌ | ❌ |
| Stale | ❌ | ❌ | ✅ Daily | ✅ |
| PR Labels | ❌ | ✅ | ❌ | ❌ |
| Label Sync | ✅ | ❌ | ❌ | ✅ |
| Pre-commit Update | ❌ | ❌ | ✅ Weekly | ✅ |

## 🔍 Monitoring

### View Workflow Runs

```bash
gh run list
gh run view <run-id>
gh run watch
```

### Check Workflow Status

```bash
gh workflow list
gh workflow view ci.yml
```

### View Logs

```bash
gh run view --log
gh run view <run-id> --job=<job-id> --log
```

## 🐛 Troubleshooting

### Common Issues

#### Workflow Not Triggering

- Check branch names in workflow `on:` section
- Verify file paths for path filters
- Check branch protection rules

#### Test Failures

- Secrets not configured: Expected for public repos
- Tests have `continue-on-error: true` for external services
- Check logs: `gh run view --log`

#### Release Failures

- Verify tag format: `v[0-9]+.[0-9]+.[0-9]+*` (not `v*.*.*`)
- Check PyPI trusted publishing setup
- Ensure environment configured

#### Permission Errors

- Check workflow permissions section
- Verify repository settings
- Check personal access token scopes

## 📖 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [UV Documentation](https://docs.astral.sh/uv/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [CodeQL Documentation](https://codeql.github.com/docs/)

## ✨ What's Different from Before

### Improvements Over Original Workflow

1. **Separated Jobs**: Lint, type-check, test, build, security run independently
2. **Matrix Testing**: Multiple Python versions (3.12, 3.13) and OSes
3. **Better Caching**: UV cache for faster builds
4. **Coverage**: Integrated code coverage reporting via pytest-cov
5. **Security**: Added Bandit, CodeQL, dependency review
6. **Automation**: Auto-labeling, stale management, dependency updates
7. **Documentation**: Comprehensive READMEs and templates

### New Capabilities

- ✅ Automated releases to PyPI
- ✅ Security scanning (CodeQL + Bandit)
- ✅ Dependency vulnerability checks
- ✅ Auto PR labeling
- ✅ Issue/PR templates
- ✅ Stale issue management
- ✅ Label synchronization
- ✅ Pre-commit auto-updates

---

**Status**: ✅ All workflows created and ready to use!

**Next**: Configure repository settings and secrets as described above.
