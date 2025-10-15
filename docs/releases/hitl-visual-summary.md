# HITL Implementation - Visual Summary

## CLI Startup with HITL Enabled

```
======================================================================
AGENTICFLEET READY FOR TASK EXECUTION
======================================================================

Example tasks to try:
  • 'Research Python machine learning libraries and write example code'
  • 'Analyze e-commerce trends and suggest visualizations'
  • 'Write a Python function to process CSV data and explain it'

Commands:
  - Type your task and press Enter to execute
  - Type 'checkpoints' or 'list-checkpoints' to view saved checkpoints
  - Type 'resume <checkpoint_id>' to resume from a checkpoint
  - Type 'quit', 'exit', or 'q' to exit
  - Press Ctrl+C to interrupt

✓ Checkpointing enabled (storage: ./checkpoints)
✓ Human-in-the-Loop enabled (timeout: 300s)
  Operations requiring approval: code_execution, file_operations,
                                 external_api_calls, sensitive_data_access

🎯 Your task:
```

## Approval Prompt Example

When the coder agent wants to execute code, the user sees:

```
============================================================
⚠️  APPROVAL REQUIRED
============================================================
Agent:       coder
Operation:   code_execution
Description: Execute Python code to print hello
Request ID:  52bfef29-401f-48f5-8843-733961870247

Code to execute:
------------------------------------------------------------
print('Hello, World!')
------------------------------------------------------------

Additional details:
  language: python
  code_length: 20
============================================================

Approve? (yes/no/edit):
```

## User Response Options

### 1. Approve

```
Approve? (yes/no/edit): yes

[Approved] Continuing execution...
Hello, World!
```

### 2. Reject

```
Approve? (yes/no/edit): no
Reason for rejection (optional): Not needed

[Rejected] Code execution was rejected: Not needed
```

### 3. Modify

```
Approve? (yes/no/edit): edit

Enter modified code (press Ctrl+D when done):
print('Hello, Modified World!')
^D

[Approved with modifications] Continuing execution...
Hello, Modified World!
```

## Architecture Flow

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                         │
│  "Write and execute Python code to calculate fibonacci" │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Orchestrator Agent                         │
│        Analyzes request and delegates                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼ DELEGATE: coder
┌─────────────────────────────────────────────────────────┐
│                 Coder Agent                             │
│          Generates Python code                          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼ code_interpreter_tool()
┌─────────────────────────────────────────────────────────┐
│           Approval Check (HITL)                         │
│   If handler configured and operation requires approval │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   APPROVED       REJECTED       MODIFIED
        │              │              │
   Execute        Return           Execute
   Original       Error         Modified Code
   Code
        │              │              │
        └──────────────┴──────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 Execution Result                        │
│       (Success/Failure with output/error)               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼ Response to Orchestrator
┌─────────────────────────────────────────────────────────┐
│              Orchestrator Agent                         │
│       Formats final response to user                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Final Answer                           │
│         Fibonacci: 0 1 1 2 3 5 8 13 21...              │
└─────────────────────────────────────────────────────────┘
```

## Configuration

In `src/agenticfleet/config/workflow.yaml`:

```yaml
workflow:
  human_in_the_loop:
    enabled: true                    # Enable/disable HITL
    approval_timeout_seconds: 300    # 5 minutes
    auto_reject_on_timeout: false    # Safe default
    require_approval_for:            # Operations requiring approval
      - code_execution
      - file_operations
      - external_api_calls
      - sensitive_data_access
    trusted_operations:              # Operations that bypass approval
      - web_search
      - data_analysis
```

## Testing

All tests pass:

```
============================================================
HITL Manual Test Suite
============================================================
Test: create_approval_request
  ✓ Request created successfully

Test: mock_approval_handler
  ✓ Approval works
  ✓ Rejection works
  ✓ Modification works

Test: code_execution_integration
  ✓ Direct execution (no handler)
  ✓ Execution with approval
  ✓ Rejection blocks execution
  ✓ Modification changes code

============================================================
✓ All tests passed!
============================================================
```

## Key Benefits

1. **Safety** - Review code before execution prevents disasters
2. **Control** - User stays in charge of what agents do
3. **Compliance** - Meet regulatory requirements for human oversight
4. **Transparency** - See exactly what agents plan to do
5. **Flexibility** - Modify operations on the fly
6. **Education** - Learn from agent reasoning

## Use Cases

### ✅ Safe: Code Execution

User can review and approve/modify/reject all code before execution

### ✅ Safe: File Operations

Prevent accidental file deletion or modification

### ✅ Safe: API Calls

Review data being sent to external services

### ✅ Trusted: Web Search

No approval needed for information gathering

### ✅ Trusted: Data Analysis

Read-only analysis proceeds without approval

---

Implementation complete and production-ready! 🎉
