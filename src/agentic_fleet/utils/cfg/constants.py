"""Constants and magic numbers for AgenticFleet.

This module centralizes all constant values used across the codebase including:
- Task validation limits
- Cache configuration
- Timeout and retry settings
- Quality thresholds
- Workflow limits
- DSPy defaults
- File paths
- Agent and tool names
- Phase and status values
"""

from __future__ import annotations

# =============================================================================
# Task Validation
# =============================================================================
MAX_TASK_LENGTH = 10000
MIN_TASK_LENGTH = 1

# =============================================================================
# Cache Configuration
# =============================================================================
DEFAULT_CACHE_TTL = 300
ANALYSIS_CACHE_TTL = 3600
CACHE_VERSION = 2
MIN_CACHE_SIZE_BYTES = 64

# =============================================================================
# Timeouts
# =============================================================================
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_AGENT_TIMEOUT = 300
DEFAULT_WORKFLOW_TIMEOUT = 600

# =============================================================================
# Retries
# =============================================================================
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0
MAX_RETRY_ATTEMPTS = 5

# =============================================================================
# Quality Thresholds
# =============================================================================
DEFAULT_QUALITY_THRESHOLD = 8.0
DEFAULT_JUDGE_THRESHOLD = 7.0
DEFAULT_REFINEMENT_THRESHOLD = 8.0
PERFECT_SCORE = 10.0

# =============================================================================
# Workflow Limits
# =============================================================================
DEFAULT_MAX_ROUNDS = 15
DEFAULT_MAX_STALLS = 3
DEFAULT_MAX_RESETS = 2
DEFAULT_MAX_REFINEMENT_ROUNDS = 2
DEFAULT_PARALLEL_THRESHOLD = 3

# =============================================================================
# DSPy Defaults
# =============================================================================
DEFAULT_DSPY_MODEL = "gpt-5-mini"
DEFAULT_DSPY_TEMPERATURE = 0.7
DEFAULT_DSPY_MAX_TOKENS = 2000
DEFAULT_MAX_BOOTSTRAPPED_DEMOS = 4

# =============================================================================
# Agent Model and Temperature Defaults
# =============================================================================
DEFAULT_AGENT_MODEL = "gpt-4.1"
DEFAULT_RESEARCHER_TEMPERATURE = 0.5
DEFAULT_ANALYST_TEMPERATURE = 0.3
DEFAULT_WRITER_TEMPERATURE = 0.7
DEFAULT_REVIEWER_TEMPERATURE = 0.2
DEFAULT_JUDGE_TEMPERATURE = 0.4

# =============================================================================
# Reasoning Effort
# =============================================================================
REASONING_EFFORT_MINIMAL = "minimal"
REASONING_EFFORT_MEDIUM = "medium"
REASONING_EFFORT_MAXIMAL = "maximal"
DEFAULT_REASONING_EFFORT = REASONING_EFFORT_MEDIUM

# =============================================================================
# Execution Modes
# =============================================================================
EXECUTION_MODE_DELEGATED = "delegated"
EXECUTION_MODE_SEQUENTIAL = "sequential"
EXECUTION_MODE_PARALLEL = "parallel"

# =============================================================================
# File Paths
# =============================================================================
DEFAULT_CONFIG_PATH = "config/workflow_config.yaml"
DEFAULT_EXAMPLES_PATH = "src/agentic_fleet/data/supervisor_examples.json"
DEFAULT_VAR_DIR = ".var"
DEFAULT_CACHE_DIR = ".var/cache"
DEFAULT_LOGS_DIR = ".var/logs"
DEFAULT_DATA_DIR = ".var/data"
DEFAULT_CACHE_PATH = ".var/logs/compiled_supervisor.pkl"
DEFAULT_ANSWER_QUALITY_CACHE_PATH = ".var/logs/compiled_answer_quality.pkl"
DEFAULT_NLU_CACHE_PATH = ".var/logs/compiled_nlu.pkl"
DEFAULT_HISTORY_PATH = ".var/logs/execution_history.jsonl"
DEFAULT_LOG_PATH = ".var/logs/workflow.log"
DEFAULT_GEPA_LOG_DIR = ".var/logs/gepa"
DEFAULT_DSPY_CACHE_DIR = ".var/cache/dspy"
DEFAULT_DSPY_EXAMPLES_PATH = ".var/logs/dspy_examples.jsonl"
DEFAULT_EVALUATION_DIR = ".var/logs/evaluation"

# =============================================================================
# History
# =============================================================================
DEFAULT_HISTORY_FORMAT = "jsonl"
DEFAULT_MAX_HISTORY_ENTRIES = 1000

# =============================================================================
# UI
# =============================================================================
DEFAULT_REFRESH_RATE = 4

# =============================================================================
# Error Limits
# =============================================================================
MAX_TASK_PREVIEW_LENGTH = 100
MAX_ERROR_MESSAGE_LENGTH = 500

# =============================================================================
# Browser Tool
# =============================================================================
DEFAULT_BROWSER_TIMEOUT_MS = 30000
DEFAULT_BROWSER_SELECTOR_TIMEOUT_MS = 5000
DEFAULT_BROWSER_MAX_TEXT_LENGTH = 10000

# =============================================================================
# GEPA Optimizer
# =============================================================================
DEFAULT_GEPA_VAL_SPLIT = 0.2
DEFAULT_GEPA_SEED = 13
DEFAULT_GEPA_HISTORY_MIN_QUALITY = 8.0
DEFAULT_GEPA_HISTORY_LIMIT = 200
DEFAULT_GEPA_MAX_FULL_EVALS = 50
DEFAULT_GEPA_MAX_METRIC_CALLS = 150
DEFAULT_GEPA_PERFECT_SCORE = 1.0

# =============================================================================
# Agent Names
# =============================================================================
AGENT_RESEARCHER = "Researcher"
AGENT_ANALYST = "Analyst"
AGENT_WRITER = "Writer"
AGENT_REVIEWER = "Reviewer"
AGENT_JUDGE = "Judge"
AGENT_PLANNER = "Planner"
AGENT_EXECUTOR = "Executor"
AGENT_CODER = "Coder"
AGENT_VERIFIER = "Verifier"
AGENT_GENERATOR = "Generator"
AGENT_COORDINATOR = "Coordinator"

# =============================================================================
# Tool Names
# =============================================================================
TOOL_TAVILY_MCP = "TavilyMCPTool"
TOOL_TAVILY_SEARCH = "TavilySearchTool"
TOOL_BROWSER = "BrowserTool"
TOOL_HOSTED_CODE_INTERPRETER = "HostedCodeInterpreterTool"

# =============================================================================
# Phase Names
# =============================================================================
PHASE_ANALYSIS = "analysis"
PHASE_ROUTING = "routing"
PHASE_EXECUTION = "execution"
PHASE_PROGRESS = "progress"
PHASE_QUALITY = "quality"
PHASE_JUDGE = "judge"
PHASE_REFINEMENT = "refinement"

# =============================================================================
# Status Values
# =============================================================================
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_TIMEOUT = "timeout"

# =============================================================================
# Serialization
# =============================================================================
SERIALIZER_PICKLE = "pickle"
SERIALIZER_DILL = "dill"
SERIALIZER_NONE = "none"
