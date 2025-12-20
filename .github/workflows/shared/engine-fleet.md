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
        # Read the prompt from the file provided by gh-aw
        PROMPT_CONTENT=$(cat "$GH_AW_PROMPT")

        # Run the fleet with JSON output
        uv run agentic-fleet run --json --no-stream "$PROMPT_CONTENT" > "$GH_AW_SAFE_OUTPUTS"
---

# AgenticFleet Custom Engine

This shared component configures the `agentic-fleet` CLI as a custom engine for GitHub Agentic Workflows.
It handles environment setup, dependency installation, and execution of the fleet with structured JSON output.
