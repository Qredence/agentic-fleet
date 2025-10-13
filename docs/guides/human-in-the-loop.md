# Human-in-the-Loop (HITL) User Guide

## Overview

AgenticFleet's Human-in-the-Loop (HITL) feature allows you to review and approve sensitive operations before they are executed. This ensures safety, compliance, and gives you control over what your agents do.

## Benefits

- **Safety**: Prevent harmful actions by reviewing code before execution
- **Compliance**: Meet regulatory requirements for human oversight
- **Trust**: Stay in control of what agents do with your data
- **Learning**: Understand agent reasoning and decision-making

## Quick Start

### Enabling HITL

HITL is configured in `src/agenticfleet/config/workflow.yaml`:

```yaml
workflow:
  human_in_the_loop:
    enabled: true  # Set to false to disable
    approval_timeout_seconds: 300  # 5 minutes
    auto_reject_on_timeout: false  # Don't auto-reject on timeout
    require_approval_for:
      - code_execution
      - file_operations
      - external_api_calls
      - sensitive_data_access
    trusted_operations:
      - web_search
      - data_analysis
```

### Starting the CLI

When you start AgenticFleet, you'll see the HITL status:

```bash
$ python -m agenticfleet
# or
$ agentic-fleet

✓ Human-in-the-Loop enabled (timeout: 300s)
  Operations requiring approval: code_execution, file_operations, external_api_calls, sensitive_data_access
```

## Using HITL

### Approval Workflow

When an agent wants to perform a sensitive operation, you'll see an approval prompt:

```
============================================================
⚠️  APPROVAL REQUIRED
============================================================
Agent:       coder
Operation:   code_execution
Description: Execute Python code
Request ID:  abc123...

Code to execute:
------------------------------------------------------------
import pandas as pd
data = pd.read_csv('data.csv')
print(data.describe())
------------------------------------------------------------

Additional details:
  language: python
  code_length: 89
============================================================

Approve? (yes/no/edit):
```

### Approval Options

You have three choices:

#### 1. Approve (yes/y/approve)
Allow the operation to proceed as proposed:
```
Approve? (yes/no/edit): yes
```

#### 2. Reject (no/n/reject/deny)
Block the operation from executing:
```
Approve? (yes/no/edit): no
Reason for rejection (optional): Too risky
```

#### 3. Edit (edit/e/modify/m)
Modify the code before execution (only for code operations):
```
Approve? (yes/no/edit): edit

Enter modified code (press Ctrl+D or Ctrl+Z when done):
import pandas as pd
data = pd.read_csv('data.csv')
# Only show first 5 rows for safety
print(data.head())
^D
```

## Configuration Options

### Timeout Behavior

```yaml
approval_timeout_seconds: 300  # Wait up to 5 minutes for approval
auto_reject_on_timeout: false  # What to do if timeout occurs
```

- If `auto_reject_on_timeout: true`, operations are automatically rejected after timeout
- If `auto_reject_on_timeout: false`, operations remain in timeout state (safer default)

### Operation Types

Configure which operations require approval:

```yaml
require_approval_for:
  - code_execution        # Python code execution
  - file_operations       # File read/write/delete
  - external_api_calls    # API calls to external services
  - sensitive_data_access # Access to sensitive data sources
```

Trusted operations that don't require approval:

```yaml
trusted_operations:
  - web_search      # Web searches are considered safe
  - data_analysis   # Data analysis (read-only)
```

## Use Cases

### Example 1: Code Execution Safety

**Scenario**: User asks to "clean up old files"

```
User: "Write a script to clean up my old files"

[Agent: Coder] Preparing to execute code...
⚠️  APPROVAL REQUIRED
Code: import os; os.system("rm -rf /home/user/*")

Approve? (yes/no/edit): no
Reason for rejection (optional): Too dangerous - would delete everything

[Rejected] Code execution was rejected: Too dangerous
```

✅ **Result**: No files deleted, disaster avoided!

### Example 2: Code Modification

**Scenario**: User asks to "analyze data and send report"

```
User: "Analyze sales data and send results to external API"

[Agent: Coder] Preparing to execute code...
⚠️  APPROVAL REQUIRED
Code: 
import requests
data = analyze_sales()
requests.post("https://external-api.com/report", json=data)

Approve? (yes/no/edit): edit

Enter modified code:
# Modified to save locally instead
data = analyze_sales()
with open('report.json', 'w') as f:
    json.dump(data, f)
print("Report saved locally")
^D

[Approved with modifications] Continuing execution...
```

✅ **Result**: Data stays local, privacy maintained!

### Example 3: Quick Approval for Safe Operations

**Scenario**: User trusts the operation

```
User: "Calculate fibonacci numbers up to 100"

[Agent: Coder] Preparing to execute code...
⚠️  APPROVAL REQUIRED
Code: 
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        print(a, end=' ')
        a, b = b, a + b

fib(100)

Approve? (yes/no/edit): yes

[Approved] Continuing execution...
0 1 1 2 3 5 8 13 21...
```

✅ **Result**: Safe code executes immediately after approval!

## Disabling HITL

To disable HITL and allow autonomous execution:

1. Edit `src/agenticfleet/config/workflow.yaml`:
   ```yaml
   workflow:
     human_in_the_loop:
       enabled: false
   ```

2. Restart AgenticFleet

You'll see:
```
⚠ Human-in-the-Loop disabled
```

## Best Practices

### When to Enable HITL

✅ **Enable for**:
- Production environments
- Sensitive data operations
- Critical infrastructure changes
- Compliance-required workflows
- Learning and development

❌ **Consider Disabling for**:
- Development/testing environments
- Trusted, well-tested workflows
- Automated CI/CD pipelines
- Non-sensitive operations only

### Security Considerations

- Always review code carefully before approving
- Look for file system operations (`os`, `shutil`, `pathlib`)
- Check for network operations (`requests`, `urllib`, `socket`)
- Verify data destinations (APIs, databases, files)
- Use edit mode to restrict operations
- Set appropriate timeout values

## Troubleshooting

### "Approval request timed out"

**Cause**: No response within `approval_timeout_seconds`

**Solutions**:
- Increase timeout in configuration
- Set `auto_reject_on_timeout: true` for automatic handling
- Respond more quickly to prompts

### "This operation cannot be modified"

**Cause**: Trying to edit a non-code operation

**Solutions**:
- Only code operations can be edited
- Use approve or reject for other operation types

### HITL not prompting for approval

**Cause**: HITL may be disabled or misconfigured

**Solutions**:
1. Check `workflow.yaml`: `human_in_the_loop.enabled: true`
2. Verify operation type in `require_approval_for` list
3. Restart AgenticFleet after configuration changes
4. Check logs for errors

## API Reference

### Creating Custom Approval Handlers

```python
from agenticfleet.core.approval import (
    ApprovalHandler,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalDecision
)

class MyApprovalHandler(ApprovalHandler):
    async def request_approval(
        self, 
        request: ApprovalRequest
    ) -> ApprovalResponse:
        # Your approval logic here
        return ApprovalResponse(
            request_id=request.request_id,
            decision=ApprovalDecision.APPROVED,
            reason="Custom approval logic"
        )
```

### Integrating with Workflows

```python
from agenticfleet.workflows import MultiAgentWorkflow
from my_module import MyApprovalHandler

# Create workflow with custom handler
handler = MyApprovalHandler()
workflow = MultiAgentWorkflow(approval_handler=handler)

# Run workflow
result = await workflow.run("Your task here")
```

## Related Documentation

- [Architecture Overview](../overview/implementation-summary.md)
- [Configuration Guide](../operations/repository-guidelines.md)
- [Security Best Practices](../../SECURITY.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/Qredence/AgenticFleet/issues
- Documentation: https://github.com/Qredence/AgenticFleet/docs

---

*Last Updated: October 13, 2025*
*Version: 0.5.0*
