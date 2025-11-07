#!/bin/bash
# Setup PyPI Environment for GitHub Actions
# This script provides instructions and checks for setting up PyPI publishing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

# Extract project name from pyproject.toml
PYPROJECT_TOML="pyproject.toml"
PYPI_PROJECT_NAME=""
if [ -f "$PYPROJECT_TOML" ]; then
    # Extract project name under [project] section. Works for PEP 621-compliant files.
    PYPI_PROJECT_NAME=$(awk '
        $0 ~ /^\[project\]/ { in_project=1; next }
        in_project && $0 ~ /^name[[:space:]]*=/ {
            sub(/name[[:space:]]*=[[:space:]]*["'\'']/, "", $0)
            sub(/["'\''].*$/, "", $0)
            print $0; exit
        }
    ' "$PYPROJECT_TOML")
fi
if [ -z "$PYPI_PROJECT_NAME" ]; then
    echo -e "${RED}Error: Could not determine project name from pyproject.toml${NC}"
    exit 1
fi

# Set repository name from argument, env variable, or default value
REPO="${1:-${REPO:-Qredence/AgenticFleet}}"
REPO_OWNER="${REPO%%/*}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}PyPI Environment Setup for ${REPO}${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not logged in to GitHub CLI${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✓${NC} GitHub CLI is installed and authenticated"
echo ""

echo -e "${YELLOW}Step 1: PyPI Environment Setup${NC}"
echo "GitHub environments must be created through the web UI."
echo ""
echo -e "${BLUE}To create the 'pypi' environment for '${REPO}':${NC}"
echo ""
echo "1. Go to: https://github.com/${REPO}/settings/environments"
echo "2. Click 'New environment'"
echo "3. Name: ${GREEN}pypi${NC}"
echo "4. Click 'Configure environment'"
echo ""
echo -e "${YELLOW}Step 2: Configure Deployment Protection${NC}"
echo ""
echo "5. Under 'Deployment branches and tags', select: ${GREEN}Selected tags${NC}"
echo "6. Click 'Add deployment branch or tag rule'"
echo "7. Enter pattern: ${GREEN}v[0-9]+.[0-9]+.[0-9]+*${NC}"
echo "   ${YELLOW}Note: Use this exact pattern, not 'v*.*.*' (causes 'Name is invalid' error)${NC}"
echo "8. Click 'Add rule'"
echo ""
echo -e "${YELLOW}Step 3: Set Up PyPI Trusted Publishing (Recommended)${NC}"
echo ""
echo "Instead of using API tokens, set up trusted publishing:"
echo ""
echo "1. Go to: ${BLUE}https://pypi.org/manage/account/publishing/${NC}"
echo "2. Scroll to 'Add a new pending publisher'"
echo "3. Fill in:"
echo "   - PyPI Project Name: ${GREEN}${PYPI_PROJECT_NAME}${NC}"
echo "   - Owner: ${GREEN}${REPO_OWNER}${NC}"
echo "   - Repository name: ${GREEN}${REPO##*/}${NC}"
echo "   - Workflow name: ${GREEN}release.yml${NC}"
echo "   - Environment name: ${GREEN}pypi${NC}"
echo "4. Click 'Add'"
echo ""
echo -e "${YELLOW}Alternative: Using API Token${NC}"
echo ""
echo "If you prefer using an API token instead:"
echo ""
echo "1. Generate token at: ${BLUE}https://pypi.org/manage/account/token/${NC}"
echo "2. In GitHub, go to: https://github.com/${REPO}/settings/environments"
echo "3. Click on 'pypi' environment"
echo "4. Under 'Environment secrets', click 'Add secret'"
echo "5. Name: ${GREEN}PYPI_API_TOKEN${NC}"
echo "6. Paste your PyPI token"
echo "7. Update .github/workflows/release.yml to use the token"
echo ""

echo -e "${YELLOW}Step 4: Optional - TestPyPI Environment${NC}"
echo ""
echo "To test releases before publishing to production:"
echo ""
echo "1. Create another environment named: ${GREEN}testpypi${NC}"
echo "2. Set up trusted publishing at: ${BLUE}https://test.pypi.org/manage/account/publishing/${NC}"
echo "3. Use the same details but for TestPyPI"
echo ""

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Verification${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Check if release workflow exists
if [ -f ".github/workflows/release.yml" ]; then
    echo -e "${GREEN}✓${NC} Release workflow exists"
else
    echo -e "${RED}✗${NC} Release workflow not found"
fi

# Check pyproject.toml
if [ -f "pyproject.toml" ]; then
    echo -e "${GREEN}✓${NC} pyproject.toml exists"

    # Extract package name from pyproject.toml
    PKG_NAME=$(awk -F' *= *' '/^name[[:space:]]*=/ {gsub(/"/, "", $2); print $2; exit}' pyproject.toml)
    if [ "$PKG_NAME" = "$PYPI_PROJECT_NAME" ]; then
        echo -e "${GREEN}✓${NC} Package name: $PKG_NAME"
    else
        echo -e "${YELLOW}!${NC} Package name in pyproject.toml ('$PKG_NAME') does not match expected ('$PYPI_PROJECT_NAME')"
    fi

    # Check version
    version=$(grep -E '^version = ' pyproject.toml | head -1 | cut -d'"' -f2)
    if [ -n "$version" ]; then
        echo -e "${GREEN}✓${NC} Current version: $version"
    fi
else
    echo -e "${RED}✗${NC} pyproject.toml not found"
fi

echo ""
echo -e "${YELLOW}================================${NC}"
echo -e "${YELLOW}Testing Your Setup${NC}"
echo -e "${YELLOW}================================${NC}"
echo ""
echo "Once environment is configured, test the release workflow:"
echo ""
echo "1. Manual trigger (without publishing):"
echo "   ${BLUE}gh workflow run release.yml${NC}"
echo ""
echo "2. Create a test tag:"
echo "   ${BLUE}git tag v0.5.5-test${NC}"
echo "   ${BLUE}git push origin v0.5.5-test${NC}"
echo ""
echo "3. For production release:"
echo "   ${BLUE}git tag v0.5.5${NC}"
echo "   ${BLUE}git push origin v0.5.5${NC}"
echo ""

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Quick Links${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Repository Settings: https://github.com/${REPO}/settings"
echo "Environments: https://github.com/${REPO}/settings/environments"
echo "PyPI Publishing: https://pypi.org/manage/account/publishing/"
echo "TestPyPI Publishing: https://test.pypi.org/manage/account/publishing/"
echo "Workflow Runs: https://github.com/${REPO}/actions/workflows/release.yml"
echo ""

echo -e "${BLUE}For more details, see: docs/GITHUB_ACTIONS_SETUP.md${NC}"
echo ""
