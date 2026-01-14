#!/usr/bin/env bash
# validate_litellm_models.sh - Test all LiteLLM proxy models
#
# Purpose: Validate that all 5 LiteLLM models are accessible and working
# Usage: ./scripts/validate_litellm_models.sh
# Requires: LITELLM_PROXY_URL and LITELLM_API_KEY environment variables
#
# Exit codes:
#   0 - All models validated successfully
#   1 - One or more models failed validation
#   2 - Configuration error (missing env vars)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load .env if it exists
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    echo -e "${BLUE}Loading environment from .env${NC}"
    # shellcheck disable=SC1091
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Validate required environment variables
if [[ -z "${LITELLM_PROXY_URL:-}" ]]; then
    echo -e "${RED}ERROR: LITELLM_PROXY_URL not set${NC}"
    echo "Please set LITELLM_PROXY_URL in your .env file or environment"
    exit 2
fi

if [[ -z "${LITELLM_API_KEY:-}" ]]; then
    echo -e "${RED}ERROR: LITELLM_API_KEY not set${NC}"
    echo "Please set LITELLM_API_KEY in your .env file or environment"
    exit 2
fi

# Test configuration
TIMEOUT=30
FAILED_MODELS=()
PASSED_MODELS=()

# Model definitions: name, test prompt (gemini/ and deepinfra/ only)
declare -a MODEL_NAMES=(
    "deepinfra/nvidia/Nemotron-3-Nano-30B-A3B"
    "deepinfra/deepseek-ai/DeepSeek-V3.2"
    "deepinfra/deepseek-ai/DeepSeek-R1-0528"
    "gemini/gemini-3-flash-preview"
    "gemini/gemini-3-pro-preview"
)

declare -a MODEL_PROMPTS=(
    "Classify this as greeting or question: Hello"
    "Write a Python function to sort a list"
    "Is 17 a prime number? Verify step by step."
    "Summarize: AI trends in 2026"
    "Rate the quality of this text on scale 1-10: This is a test."
)

# Function to test a single model
test_model() {
    local model_name="$1"
    local prompt="$2"
    local start_time
    local end_time
    local duration

    echo -e "${BLUE}Testing: ${model_name}${NC}"

    # Create JSON payload
    local json_payload
    json_payload=$(jq -n \
        --arg model "$model_name" \
        --arg prompt "$prompt" \
        '{
            model: $model,
            messages: [
                {
                    role: "user",
                    content: $prompt
                }
            ],
            max_tokens: 100,
            temperature: 0.7
        }')

    # Standard LiteLLM endpoint: /v1/chat/completions
    local endpoint="${LITELLM_PROXY_URL}/v1/chat/completions"

    # Make request with timeout
    start_time=$(date +%s)

    if response=$(curl -s -w "\n%{http_code}" \
        -m "$TIMEOUT" \
        -X POST "$endpoint" \
        -H "Authorization: Bearer ${LITELLM_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$json_payload" 2>&1); then

        end_time=$(date +%s)
        duration=$((end_time - start_time))

        # Split response and status code
        http_code=$(echo "$response" | tail -n1)
        response_body=$(echo "$response" | sed '$d')

        # Check HTTP status
        if [[ "$http_code" == "200" ]]; then
            # Validate JSON response
            if echo "$response_body" | jq -e '.choices[0].message.content' > /dev/null 2>&1; then
                local content
                content=$(echo "$response_body" | jq -r '.choices[0].message.content')
                local content_preview="${content:0:100}"
                echo -e "${GREEN}✓ PASSED${NC} (${duration}s)"
                echo -e "  Response: ${content_preview}..."
                PASSED_MODELS+=("$model_name")
                return 0
            else
                echo -e "${RED}✗ FAILED${NC} - Invalid JSON response"
                echo "  Response: $response_body"
                FAILED_MODELS+=("$model_name")
                return 1
            fi
        elif [[ "$http_code" == "401" ]]; then
            echo -e "${RED}✗ FAILED${NC} - HTTP 401 Unauthorized"
            echo "  Error: $response_body"
            if echo "$response_body" | grep -q "IAP"; then
                echo -e "${YELLOW}  Hint: LiteLLM proxy is behind Google Cloud IAP${NC}"
                echo -e "${YELLOW}  Try: gcloud auth print-identity-token${NC}"
            else
                echo -e "${YELLOW}  Hint: Check LITELLM_API_KEY is correct${NC}"
            fi
            FAILED_MODELS+=("$model_name")
            return 1
        else
            echo -e "${RED}✗ FAILED${NC} - HTTP $http_code"
            echo "  Response: $response_body"
            FAILED_MODELS+=("$model_name")
            return 1
        fi
    else
        echo -e "${RED}✗ FAILED${NC} - Request timeout or network error"
        echo "  Error: $response"
        FAILED_MODELS+=("$model_name")
        return 1
    fi
}

# Main execution
echo "=========================================="
echo "LiteLLM Model Validation"
echo "=========================================="
echo "Proxy URL: $LITELLM_PROXY_URL"
echo "Testing ${#MODEL_NAMES[@]} models with ${TIMEOUT}s timeout"
echo "=========================================="
echo ""

# Test all models
for i in "${!MODEL_NAMES[@]}"; do
    test_model "${MODEL_NAMES[$i]}" "${MODEL_PROMPTS[$i]}"
    echo ""
done

# Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed: ${#PASSED_MODELS[@]}${NC}"
echo -e "${RED}Failed: ${#FAILED_MODELS[@]}${NC}"
echo ""

if [[ ${#PASSED_MODELS[@]} -gt 0 ]]; then
    echo "Passed models:"
    for model in "${PASSED_MODELS[@]}"; do
        echo -e "  ${GREEN}✓${NC} $model"
    done
    echo ""
fi

if [[ ${#FAILED_MODELS[@]} -gt 0 ]]; then
    echo "Failed models:"
    for model in "${FAILED_MODELS[@]}"; do
        echo -e "  ${RED}✗${NC} $model"
    done
    echo ""
fi

# Exit with appropriate code
if [[ ${#FAILED_MODELS[@]} -eq 0 ]]; then
    echo -e "${GREEN}All models validated successfully!${NC}"
    exit 0
else
    echo -e "${RED}Some models failed validation. Please check configuration.${NC}"
    exit 1
fi
