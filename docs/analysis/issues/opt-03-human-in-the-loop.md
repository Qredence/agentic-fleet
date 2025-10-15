---
title: '[OPT-03] Add Human-in-the-Loop Capabilities'
labels: ['enhancement', 'optimization', 'agent-framework', 'high-priority', 'safety']
---

## Priority Level

🔥 **High Priority** - Safety & Compliance

## Overview

Implement human-in-the-loop (HITL) capabilities to allow human approval/intervention for sensitive operations like code execution and data analysis, ensuring safety and building user trust.

## Current State

### Limitations

- Agents execute autonomously without human oversight
- No approval mechanism for sensitive operations
- Cannot pause workflow for human input
- No way to review agent decisions before execution
- Risk of harmful actions (code execution, data deletion, etc.)

## Proposed Implementation

```python
from agent_framework import FunctionApprovalRequestContent, FunctionApprovalResponseContent

# Define approval-required edges
def requires_approval(ctx):
    """Determine if human approval is needed."""
    return (
        ctx.current_agent == "coder" or  # Code execution needs approval
        ctx.shared_state.get("sensitive_operation", False)
    )

workflow = (
    WorkflowBuilder()
    .add_agent(orchestrator, "orchestrator")
    .add_agent(coder, "coder")
    .add_edge("orchestrator", "coder", approval_required=requires_approval)
    .build()
)

# CLI approval handler
async def approval_handler(request: FunctionApprovalRequestContent):
    """Handle approval requests in CLI."""
    print(f"\n{'=' * 60}")
    print(f"APPROVAL REQUIRED")
    print(f"{'=' * 60}")
    print(f"Agent: {request.agent_name}")
    print(f"Operation: {request.operation}")
    print(f"Details: {request.details}")
    print(f"{'=' * 60}")

    while True:
        response = input("Approve? (yes/no/edit): ").strip().lower()
        if response in ["yes", "y"]:
            return FunctionApprovalResponseContent(approved=True)
        elif response in ["no", "n"]:
            return FunctionApprovalResponseContent(approved=False, reason="User rejected")
        elif response == "edit":
            new_input = input("Modified input: ")
            return FunctionApprovalResponseContent(approved=True, modified_input=new_input)

workflow.set_approval_handler(approval_handler)
```

## Benefits

### Safety

- ✅ **Prevent Harmful Actions**: Human reviews code before execution
- ✅ **Data Protection**: Approve before modifying sensitive data
- ✅ **Compliance**: Meet regulatory requirements for human oversight
- ✅ **Risk Mitigation**: Catch errors before they cause damage

### User Experience

- ✅ **Transparency**: Users see what agents plan to do
- ✅ **Trust**: Users feel in control of the system
- ✅ **Learning**: Users learn from agent reasoning
- ✅ **Customization**: Users can modify agent outputs

### Quality

- ✅ **Error Detection**: Humans catch agent mistakes
- ✅ **Alignment**: Ensure outputs match user intent
- ✅ **Feedback Loop**: Improve agents based on human input

## Implementation Steps

### Phase 1: Basic Approval (Week 1)

- [ ] Implement approval_handler interface
- [ ] Add CLI approval prompt
- [ ] Wire approval to code execution tool
- [ ] Add approval configuration options
- [ ] Test basic approve/reject flows

### Phase 2: Advanced Features (Week 2)

- [ ] Add approval timeout handling
- [ ] Implement approval queuing system
- [ ] Add approval history/audit log
- [ ] Support approval modifications
- [ ] Add bypass for trusted operations

### Phase 3: UI Integration (Week 3)

- [ ] Create web UI for approvals
- [ ] Add mobile notification support
- [ ] Implement approval delegation
- [ ] Add batch approval features
- [ ] Create approval analytics dashboard

## Configuration

```yaml
# config/workflow.yaml
workflow:
  human_in_the_loop:
    enabled: true
    approval_timeout_seconds: 300  # 5 minutes
    auto_reject_on_timeout: false
    require_approval_for:
      - code_execution
      - file_operations
      - external_api_calls
      - sensitive_data_access
    trusted_operations:
      - web_search
      - data_analysis
```

## Use Cases

### 1. Code Execution Safety

```
User: "Write a script to clean up my files"
Agent: Plans to run: rm -rf /home/user/*
System: [APPROVAL REQUIRED]
User: Rejects → No files deleted ✅
```

### 2. Data Analysis Review

```
User: "Analyze sales data and share insights"
Agent: Plans to send data to external API
System: [APPROVAL REQUIRED]
User: Modifies to use local analysis only ✅
```

### 3. Multi-Step Workflows

```
User: "Research, write code, and deploy"
System: Pauses at each critical step
User: Reviews and approves each phase ✅
```

## Testing Requirements

### Unit Tests

```python
def test_approval_required():
    """Test approval is requested for sensitive ops."""
    workflow = create_workflow_with_hitl()
    result = workflow.plan_execution("Run code")
    assert result.requires_approval

def test_approval_granted():
    """Test workflow continues after approval."""
    workflow = create_workflow_with_hitl()
    approval_handler = MockApprovalHandler(approve=True)
    result = await workflow.run("Run code", approval_handler=approval_handler)
    assert result.success

def test_approval_denied():
    """Test workflow stops after rejection."""
    workflow = create_workflow_with_hitl()
    approval_handler = MockApprovalHandler(approve=False)
    result = await workflow.run("Run code", approval_handler=approval_handler)
    assert not result.success
    assert "User rejected" in result.message
```

### Integration Tests

- Test approval timeout handling
- Test approval modification flow
- Test multiple approvals in one workflow
- Test approval history recording

### Manual Verification

1. Start workflow that requires approval
2. Verify approval prompt appears
3. Test approve → workflow continues
4. Test reject → workflow stops
5. Test edit → modified input used
6. Test timeout → workflow handles gracefully

## UI/UX Considerations

### CLI Approval Prompt

```
════════════════════════════════════════════════════════
⚠️  HUMAN APPROVAL REQUIRED ⚠️
════════════════════════════════════════════════════════

Agent: coder
Operation: Execute Python Code

Proposed Action:
────────────────────────────────────────────────────────
import os
os.system('rm -rf *.tmp')
────────────────────────────────────────────────────────

Rationale:
The code will delete all temporary files to clean up disk space.

Options:
  [Y] Approve and continue
  [N] Reject and stop
  [E] Edit the code before approval
  [V] View full context
  [?] Help

Your choice:
```

### Web UI Approval (Future)

- Real-time notifications
- Code diff viewer
- Approval history
- Batch approval interface
- Mobile-responsive design

## Documentation Updates

### User Guide

```markdown
# Human-in-the-Loop

AgenticFleet can pause for human approval before executing sensitive operations:

## Enabling HITL

Add to your `.env`:
\`\`\`
HITL_ENABLED=true
HITL_APPROVAL_TIMEOUT=300
\`\`\`

## Operations Requiring Approval

By default, approval is required for:
- Code execution
- File system operations
- External API calls
- Sensitive data access

## Approval Workflow

1. Agent proposes action
2. System pauses and shows details
3. You approve, reject, or modify
4. Workflow continues or stops

## Examples

\`\`\`bash
$ agentic-fleet

> Write and execute Python code to analyze data.csv

[Agent: Coder] Preparing to execute code...
[APPROVAL REQUIRED]
Code: print(pd.read_csv('data.csv').describe())

Approve? (yes/no/edit): yes
[Approved] Continuing execution...
\`\`\`
```

## Estimated Effort

🔨 **Medium** (2-3 weeks)

### Breakdown

- Basic CLI approval: 3-5 days
- Advanced features: 3-5 days
- Web UI (optional): 5-7 days
- Testing & docs: 2-3 days

## Dependencies

- Works best with WorkflowBuilder (#OPT-01)
- May integrate with DevUI (#OPT-04)

## Related Resources

- [HITL Examples](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started/workflows/human-in-the-loop)
- [Function Approval API](https://learn.microsoft.com/agent-framework/user-guide/workflows/human-in-the-loop)

## Success Criteria

- ✅ Approval prompts appear for sensitive operations
- ✅ Users can approve/reject/modify actions
- ✅ Workflow continues after approval
- ✅ Workflow stops after rejection
- ✅ Timeout handling works correctly
- ✅ Approval history is recorded
- ✅ User experience is smooth and intuitive

---
Status: Ready for Implementation
Priority: High (Safety-critical)
Related: #OPT-01, #OPT-04
