# Automated Feedback Implementation Guide

This document explains how to use the automated code quality feedback system implemented in this repository.

## Overview

The automated feedback system provides comprehensive code review capabilities across multiple dimensions:

1. **Code Quality** - Style, formatting, naming conventions
2. **Security** - Secrets detection, SQL injection risks, shell injection
3. **Performance** - Async patterns, database optimization, caching
4. **Documentation** - Docstrings, type hints, comments
5. **Testing** - Coverage, test quality, edge cases

## Components

### 1. Code Review Guidelines

**Location:** `docs/CODE_REVIEW_GUIDELINES.md`

Comprehensive documentation that defines:
- Code style standards
- Security best practices  
- Performance considerations
- Documentation requirements
- Testing standards
- Automated feedback checklist

**Usage:**
- Reference when writing new code
- Review before submitting PRs
- Use as training material for new contributors

### 2. Automated Feedback Tool

**Location:** `tools/scripts/automated_feedback.py`

Python script that performs static analysis on code to identify:
- Missing docstrings
- Missing type hints
- Poor error handling
- Security vulnerabilities
- Performance anti-patterns

**Usage Examples:**

```bash
# Analyze a single file
python tools/scripts/automated_feedback.py --file src/agentic_fleet/api/chat/service.py

# Analyze a directory
python tools/scripts/automated_feedback.py --dir src/agentic_fleet

# Get JSON output for programmatic use
python tools/scripts/automated_feedback.py --dir src --format json > analysis.json

# Analyze without recursion
python tools/scripts/automated_feedback.py --dir src --no-recursive
```

**Output Format:**

```
================================================================================
AUTOMATED CODE QUALITY FEEDBACK
================================================================================

Files analyzed: 32
Total issues: 30
  - Errors: 0
  - Warnings: 27
  - Info: 3

WARNINGS
--------------------------------------------------------------------------------
[DOCUMENTATION] src/agentic_fleet/api/app.py:13
  Missing docstring for FunctionDef 'create_app'
  Suggestion: Add a docstring describing the purpose, parameters, and return value

...

CODE METRICS
--------------------------------------------------------------------------------
Total lines of code: 5432
Total functions: 156
Total classes: 42
```

### 3. GitHub Actions Workflow

**Location:** `.github/workflows/copilot-feedback.yml`

Automated CI/CD workflow that runs on every PR to:
- Execute automated feedback analysis
- Run ruff linting
- Perform mypy type checking
- Check test coverage
- Post comprehensive feedback as PR comment
- Upload analysis artifacts

**Trigger:** Automatically runs when:
- A PR is opened
- New commits are pushed to a PR
- A PR is reopened

**What it checks:**
- Custom code analysis (docstrings, type hints, error handling)
- Ruff linting (style, imports, complexity)
- Type safety (mypy)
- Test coverage (pytest)

**PR Comment Example:**

```markdown
## 🤖 Copilot Automated Feedback

This automated analysis provides feedback on code quality, security, performance, and documentation.

### 📊 Analysis Results

**Custom Analysis:**
- Files analyzed: 32
- Total issues: 30
- Errors: ❌ 0
- Warnings: ⚠️ 27  
- Info: ℹ️ 3

**Ruff Linting:**
- Issues found: 0
- ✅ No linting issues found

**Type Checking (mypy):**
- ✅ No type errors found

**Test Coverage:**
- Coverage: 96.0%
- ✅ Coverage meets target (≥90%)

### 📋 Code Quality Checklist

Please ensure your PR addresses the following:

- [ ] All functions and classes have docstrings
- [ ] Type hints are present for all parameters and return values
- [ ] No hardcoded secrets or credentials
- [ ] Error handling uses specific exception types
- [ ] Tests cover new functionality
- [ ] Documentation is updated

### 📚 Resources

- [Code Review Guidelines](../docs/CODE_REVIEW_GUIDELINES.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Testing Guide](../tests/TESTING_GUIDE.md)
```

## Applying to PRs #291-#298

The automated feedback system can be used to review the 8 PRs split from #290:

### PR #291 - Core Framework (15 files)
```bash
# Analyze core files
python tools/scripts/automated_feedback.py --dir src/agentic_fleet/core
```

**Focus Areas:**
- Ensure all public APIs have docstrings
- Verify type hints on all function parameters
- Check error handling patterns
- Validate async/await usage

### PR #292 - Specialist Agents (15 files)
```bash
# Analyze agent files  
python tools/scripts/automated_feedback.py --dir src/agentic_fleet/agents
```

**Focus Areas:**
- Document agent capabilities and configurations
- Ensure tool integrations are properly typed
- Validate prompt templates are secure
- Check for proper error handling in agent execution

### PR #293 - API & Streaming (20 files)
```bash
# Analyze API files
python tools/scripts/automated_feedback.py --dir src/agentic_fleet/api
```

**Focus Areas:**
- Validate all API endpoints have proper error handling
- Ensure input validation on all routes
- Check for security vulnerabilities (SQL injection, XSS)
- Verify async streaming patterns
- Document response schemas

### PR #294 - Models & Utilities (17 files)
```bash
# Analyze models and utilities
python tools/scripts/automated_feedback.py --dir src/agentic_fleet/models
python tools/scripts/automated_feedback.py --dir src/agentic_fleet/utils
```

**Focus Areas:**
- Ensure all Pydantic models have field descriptions
- Validate utility functions have docstrings
- Check for proper type hints
- Verify configuration handling is secure

### PR #295 - Workflow Orchestration (7 files)
```bash
# Analyze workflow files
python tools/scripts/automated_feedback.py --dir src/agentic_fleet/workflow
```

**Focus Areas:**
- Document workflow builder patterns
- Ensure proper error handling in workflow execution
- Validate event handling is type-safe
- Check for resource cleanup in workflow teardown

### PR #296 - Frontend Enhancements (63 files)
```bash
# Note: Python tool doesn't analyze TypeScript/JavaScript
# Use frontend-specific linters: ESLint, TypeScript compiler
cd src/frontend
npm run lint
npm run type-check
```

**Focus Areas:**
- Ensure components have proper TypeScript types
- Validate state management patterns
- Check for proper error handling in API calls
- Verify accessibility standards

### PR #297 - Comprehensive Testing (30 files)
```bash
# Analyze test files
python tools/scripts/automated_feedback.py --dir tests
```

**Focus Areas:**
- Ensure test functions have descriptive docstrings
- Validate test coverage is comprehensive
- Check for proper use of fixtures and mocks
- Verify edge cases are tested

### PR #298 - Configuration & Docs (14 files)
```bash
# Analyze configuration
python tools/scripts/automated_feedback.py --dir config
python tools/scripts/automated_feedback.py --dir docs
```

**Focus Areas:**
- Ensure configuration files are well-documented
- Validate CI/CD workflows are secure
- Check documentation is up-to-date
- Verify agent specifications are complete

## Integration with Development Workflow

### Pre-commit

Add automated feedback to your pre-commit workflow:

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: automated-feedback
        name: Run automated feedback
        entry: python tools/scripts/automated_feedback.py --dir src
        language: system
        pass_filenames: false
```

### Local Development

Before submitting a PR:

```bash
# Run all quality checks
make check

# Run automated feedback
python tools/scripts/automated_feedback.py --dir src

# Run tests with coverage
make test
```

### CI/CD

The GitHub Actions workflow automatically runs on all PRs. Review the feedback comment and address issues before requesting review.

## Customization

### Adding New Checks

Edit `tools/scripts/automated_feedback.py` to add custom checks:

```python
def _check_custom_pattern(self, tree: ast.AST, result: AnalysisResult) -> None:
    """Check for custom pattern."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Your custom check logic
            if some_condition:
                result.feedback.append(
                    FeedbackItem(
                        category="quality",
                        severity="warning",
                        message="Custom check failed",
                        file=result.file,
                        line=node.lineno,
                        suggestion="How to fix it",
                    )
                )
```

### Adjusting Severity Levels

Modify severity thresholds in the tool or workflow:

```python
# In automated_feedback.py
if issue_count > 0:
    severity = "error" if issue_count > 10 else "warning"
```

### Excluding Files

Add exclusions to `.gitignore` or modify the tool:

```python
# Skip certain directories
if "__pycache__" in str(file_path) or ".venv" in str(file_path):
    continue
```

## Best Practices

1. **Run Locally First** - Don't wait for CI to catch issues
2. **Address Critical Issues** - Fix errors before warnings
3. **Document Exceptions** - If you must ignore a rule, document why
4. **Keep It Updated** - Regularly review and update guidelines
5. **Educate Team** - Use guidelines for onboarding and training

## Metrics and Reporting

Track code quality metrics over time:

```bash
# Generate baseline report
python tools/scripts/automated_feedback.py --dir src --format json > baseline.json

# Compare after changes
python tools/scripts/automated_feedback.py --dir src --format json > current.json
diff baseline.json current.json
```

## Troubleshooting

### Tool Fails to Run

```bash
# Ensure dependencies are installed
uv sync --all-extras

# Check Python version
python --version  # Should be 3.12+

# Run with verbose output
python -v tools/scripts/automated_feedback.py --dir src
```

### Workflow Fails in CI

1. Check the workflow logs in GitHub Actions
2. Review uploaded artifacts for detailed reports
3. Run the same commands locally to reproduce
4. Check that secrets are properly configured

### False Positives

If the tool reports false positives:

1. Add specific exclusions to the tool
2. Document why the pattern is acceptable
3. Update the CODE_REVIEW_GUIDELINES.md
4. Consider contributing improvements to the tool

## Contributing

To improve the automated feedback system:

1. Identify gaps in current checks
2. Implement new checks in `automated_feedback.py`
3. Update `CODE_REVIEW_GUIDELINES.md` with new standards
4. Add tests for new checks
5. Update this guide with usage examples
6. Submit a PR with your improvements

## Support

For questions or issues:
- Review `docs/CODE_REVIEW_GUIDELINES.md`
- Check GitHub Actions logs
- Open an issue with the `quality` label
- Ask in PR comments or discussions

---

**Last Updated:** 2025-11-04
**Version:** 1.0.0
**Maintainer:** AgenticFleet Team
