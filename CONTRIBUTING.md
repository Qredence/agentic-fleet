# Contributing to AgenticFleet

Thank you for your interest in contributing to AgenticFleet! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Development Workflow](#development-workflow)
- [Code Quality Standards](#code-quality-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)
- [Review Process](#review-process)
- [Getting Help](#getting-help)

---

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [contact@qredence.ai](mailto:contact@qredence.ai).

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.12+** - [Download here](https://www.python.org/downloads/)
- **uv** - Fast Python package manager - [Install instructions](https://docs.astral.sh/uv/)
- **Node.js 18+** and **npm** - For frontend development - [Download here](https://nodejs.org/)
- **Git** - For version control - [Download here](https://git-scm.com/)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/agentic-fleet.git
cd agentic-fleet
```

3. Add the upstream repository:

```bash
git remote add upstream https://github.com/Qredence/agentic-fleet.git
```

---

## Development Environment Setup

### 1. Install Dependencies

**Backend dependencies:**
```bash
make install
```

**Frontend dependencies:**
```bash
make frontend-install
```

**Complete development setup (includes pre-commit hooks):**
```bash
make dev-setup
```

### 2. Configure Environment

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=your-api-key-here
```

### 3. Verify Setup

Test that everything is working:

```bash
# Validate configuration
make test-config

# Run tests
make test

# Run linting and type checking
make check
```

### 4. Start Development Servers

**Full stack (backend + frontend):**
```bash
make dev
# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
```

**Backend only:**
```bash
make backend
```

**Frontend only:**
```bash
make frontend-dev
```

---

## Development Workflow

### 1. Create a Feature Branch

Always create a new branch for your work:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or updates

### 2. Make Your Changes

- Keep changes focused and atomic
- Follow the [Code Quality Standards](#code-quality-standards)
- Write or update tests for your changes
- Update documentation as needed

### 3. Test Your Changes

Run the full test suite frequently:

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/test_specific_file.py

# Run with coverage
uv run pytest --cov=agentic_fleet

# Frontend tests
cd src/frontend && npm test
```

### 4. Check Code Quality

Before committing, ensure your code passes all quality checks:

```bash
# Run all quality checks
make check

# Individual checks
make lint          # Linting with ruff
make format        # Format with black and ruff
make type-check    # Type checking with mypy
```

### 5. Validate Configuration

If you've modified YAML configuration or agent definitions:

```bash
make test-config
make validate-agents
```

---

## Code Quality Standards

### Python Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting (line length: 100)
- Use [Ruff](https://docs.astral.sh/ruff/) for linting
- Maintain [mypy](https://mypy.readthedocs.io/) type annotations for all functions

**Key conventions:**
- Use type hints for function signatures
- Write docstrings for public APIs (Google style preferred)
- Keep functions focused and single-purpose
- Avoid global state when possible

### TypeScript/React Code Style

- Follow [TypeScript best practices](https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html)
- Use functional components with hooks
- Follow React naming conventions (PascalCase for components)
- Use ESLint configuration provided in the project

### YAML Configuration

- Use 2-space indentation
- Keep configurations declarative
- Add comments for complex configurations
- Follow existing patterns in `config/workflows.yaml` and agent configs

---

## Testing Requirements

### Backend Testing

All backend changes must include appropriate tests:

**Unit Tests:**
- Test individual functions and classes in isolation
- Mock external dependencies
- Place in `tests/test_*.py`

**Integration Tests:**
- Test interactions between components
- Use test fixtures for shared setup
- Consider existing patterns in `tests/test_api_*.py`

**Configuration Tests:**
- Validate YAML configuration loading
- Test workflow factory initialization
- See `tests/test_config.py` for examples

**Running Tests:**
```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_api_responses.py

# Specific test function
uv run pytest tests/test_config.py -k test_workflow_factory

# With coverage
uv run pytest --cov=agentic_fleet --cov-report=html
```

### Frontend Testing

Frontend changes should include:

**Unit Tests:**
- Test individual components
- Test utility functions
- Use Vitest and React Testing Library

**Running Frontend Tests:**
```bash
cd src/frontend
npm test                  # Run all tests
npm run test:coverage     # With coverage
npm run test:ui          # Interactive UI
```

### Test Guidelines

- Aim for high test coverage (>80%)
- Write clear, descriptive test names
- Use fixtures for reusable test setup
- Keep tests independent and isolated
- Don't test external dependencies directly (use mocks)

---

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes

### Examples

```
feat(api): add streaming support for chat responses

fix(frontend): resolve memory leak in chat component

docs: update contributing guidelines with testing section

test(api): add integration tests for conversation endpoints

refactor(agents): simplify agent factory initialization
```

### Guidelines

- Use the imperative mood ("add feature" not "added feature")
- Keep the subject line under 50 characters
- Capitalize the subject line
- Don't end the subject line with a period
- Use the body to explain what and why, not how
- Reference issues in the footer (e.g., "Fixes #123")

---

## Pull Request Process

### Before Submitting

1. **Sync with upstream:**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all quality checks:**
   ```bash
   make check
   make test
   make test-config
   ```

3. **Update documentation:**
   - Update relevant `.md` files
   - Add docstrings to new code
   - Update CHANGELOG.md if applicable

4. **Ensure clean commit history:**
   - Squash "fix typo" or "oops" commits
   - Use meaningful commit messages
   - Each commit should be a logical unit

### Creating the Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin your-branch-name
   ```

2. Create a pull request on GitHub

3. Fill out the PR template completely:
   - Describe your changes clearly
   - Link related issues
   - Check all applicable boxes
   - Add screenshots for UI changes

### PR Checklist

Ensure your PR meets these requirements:

- [ ] Code follows the project's style guidelines
- [ ] All tests pass locally
- [ ] New tests added for new functionality
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Configuration validation passes (`make test-config`)
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] PR description is clear and complete

### Size Guidelines

- Keep PRs focused and reasonably sized
- Large PRs are harder to review and more likely to introduce issues
- If your change is large, consider breaking it into smaller PRs
- Discuss large changes in an issue before implementing

---

## Documentation

### What to Document

- **Code Documentation:**
  - Add docstrings to all public functions and classes
  - Use type hints for function signatures
  - Add inline comments for complex logic

- **User Documentation:**
  - Update `README.md` for user-facing changes
  - Update or create docs in `docs/` directory
  - Include usage examples

- **Developer Documentation:**
  - Update `AGENTS.md` files for architectural changes
  - Update `tests/TESTING_GUIDE.md` for test changes
  - Document new patterns or conventions

### Documentation Style

- Use Markdown for all documentation
- Write in clear, concise language
- Include code examples where appropriate
- Use proper formatting (headers, lists, code blocks)
- Keep line lengths reasonable (80-100 characters)

### Key Documentation Files

- `README.md` - Project overview and quick start
- `AGENTS.md` - Project instructions for AI agents (root and subdirectories)
- `docs/` - Detailed guides and API documentation
- `CHANGELOG.md` - Version history and changes
- Code comments and docstrings

---

## Review Process

### What to Expect

1. **Initial Review:**
   - A maintainer will review your PR within a few days
   - Automated checks must pass before review

2. **Feedback:**
   - Address reviewer comments promptly
   - Ask questions if feedback is unclear
   - Push additional commits to the same branch

3. **Approval:**
   - PRs require approval from at least one maintainer
   - All CI checks must pass
   - All review comments must be resolved

4. **Merge:**
   - Maintainers will merge approved PRs
   - Your branch will be deleted after merge

### Responding to Feedback

- Be respectful and professional
- Don't take feedback personally
- Ask for clarification if needed
- Update your PR based on feedback
- Mark conversations as resolved when addressed

### After Your PR is Merged

- Delete your feature branch
- Sync your fork with upstream:
  ```bash
  git checkout main
  git fetch upstream
  git merge upstream/main
  git push origin main
  ```

---

## Getting Help

### Documentation Resources

- **Main README:** [README.md](README.md)
- **Backend Guide:** [src/agentic_fleet/AGENTS.md](src/agentic_fleet/AGENTS.md)
- **Frontend Guide:** [src/frontend/AGENTS.md](src/frontend/AGENTS.md)
- **Testing Guide:** [tests/TESTING_GUIDE.md](tests/TESTING_GUIDE.md)
- **API Documentation:** [docs/api/README.md](docs/api/README.md)

### Getting Support

- **Questions:** Open a [Discussion](https://github.com/Qredence/agentic-fleet/discussions)
- **Bug Reports:** Open an [Issue](https://github.com/Qredence/agentic-fleet/issues/new?template=bug_report.md)
- **Feature Requests:** Open an [Issue](https://github.com/Qredence/agentic-fleet/issues/new?template=feature_request.md)
- **Security Issues:** See [SECURITY.md](SECURITY.md)

### Community

- Be respectful and inclusive
- Help others when you can
- Share your experiences and learnings
- Follow the Code of Conduct

---

## Additional Notes

### Security

- Never commit sensitive information (API keys, passwords, etc.)
- Use `.env` files for local configuration (never commit `.env` files)
- Report security vulnerabilities privately (see [SECURITY.md](SECURITY.md))

### Performance

- Consider performance implications of your changes
- Run load tests if appropriate (`make load-test-smoke`)
- Profile code for performance-critical paths

### Breaking Changes

- Discuss breaking changes in an issue first
- Document breaking changes clearly
- Update version numbers appropriately
- Provide migration guides when needed

### License

By contributing to AgenticFleet, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

---

## Thank You!

Your contributions help make AgenticFleet better for everyone. We appreciate your time and effort! 🎉
