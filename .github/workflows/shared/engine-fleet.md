---
engine:
  id: custom
  steps:
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh

    - name: Install dependencies
      run: uv sync

    - name: Run AgenticFleet
      env:
        GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
      run: |
        set -e  # Exit on error

        # Validate required environment variables
        if [ -z "$GH_AW_PROMPT" ]; then
          echo "Error: GH_AW_PROMPT environment variable is not set" >&2
          exit 1
        fi

        if [ -z "$GH_AW_SAFE_OUTPUTS" ]; then
          echo "Error: GH_AW_SAFE_OUTPUTS environment variable is not set" >&2
          exit 1
        fi

        # Verify prompt file exists and is readable
        if [ ! -f "$GH_AW_PROMPT" ]; then
          echo "Error: Prompt file does not exist: $GH_AW_PROMPT" >&2
          exit 1
        fi

        if [ ! -r "$GH_AW_PROMPT" ]; then
          echo "Error: Prompt file is not readable: $GH_AW_PROMPT" >&2
          exit 1
        fi

        # Ensure output directory exists and is writable
        OUTPUT_DIR=$(dirname "$GH_AW_SAFE_OUTPUTS")
        if [ ! -d "$OUTPUT_DIR" ]; then
          mkdir -p "$OUTPUT_DIR" || {
            echo "Error: Failed to create output directory: $OUTPUT_DIR" >&2
            exit 1
          }
        fi

        if [ ! -w "$OUTPUT_DIR" ]; then
          echo "Error: Output directory is not writable: $OUTPUT_DIR" >&2
          exit 1
        fi

        # Read the prompt from the file provided by gh-aw
        PROMPT_CONTENT=$(cat "$GH_AW_PROMPT")

        # Run the fleet with JSON output (exit code propagates)
        uv run agentic-fleet run --json --no-stream "$PROMPT_CONTENT" > "$GH_AW_SAFE_OUTPUTS"
---

# AgenticFleet Custom Engine

This shared component configures the `agentic-fleet` CLI as a custom engine for GitHub Agentic Workflows.
It handles environment setup, dependency installation, and execution of the fleet with structured JSON output.
