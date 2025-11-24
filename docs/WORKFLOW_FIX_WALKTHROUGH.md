# Walkthrough: Backend Workflow Fix

## Problem Summary

The frontend successfully connects to the backend and receives SSE events, but the response content echoes the user's input ("who is trump?") instead of generating real AI-powered answers.

## Investigation Results

### ✅ What Works

1. **OpenAI API Configuration**: API key is properly configured
2. **Agent Functionality**: Direct testing shows the `writer` agent generates proper responses using OpenAI
3. **Chat API Route**: Correctly streams events from workflow
4. **Network Communication**: Frontend successfully makes requests and receives SSE events

### ❌ Root Cause Identified

The workflow is executing correctly and agents are generating responses, BUT the streaming event pipeline is not properly yielding the agent's output.

**Evidence**:

- Response shows `"agent_id": "judge_refine"` - this is from the quality/judge phase, not the execution phase
- Direct agent test (`test_agent_direct.py`) shows writer agent generates full, detailed answers
- The workflow completes but only sends the original task as `response.delta`

### Technical Analysis

The problem is in how workflow events are being converted to SSE responses. Looking at `src/agentic_fleet/api/routes/chat.py` lines 128-144:

```python
async for event in workflow.run_stream(message):
    if isinstance(event, MagenticAgentMessageEvent):
        content = event.message.text
        if content:
            full_response += content
            delta_msg = {
                "type": "response.delta",
                "delta": content,
                "agent_id": event.agent_id
            }
            yield f"data: {json.dumps(delta_msg)}\\n\\n"
```

The workflow should yield `MagenticAgentMessageEvent` instances with the agent's response text, but it appears only the judge phase is yielding events, not the execution phase.

## Fix Needed

The workflow execution phase needs to properly yield `MagenticAgentMessageEvent` with the agent's response. The issue is likely in:

1. **Workflow Builder** (`src/agentic_fleet/workflows/builder.py`): Check how ExecutorWorkflow yields events
2. **Executors** (`src/agentic_fleet/workflows/executors.py`): Ensure execution results are properly yielded as streaming events
3. **Supervisor Workflow** (`src/agentic_fleet/workflows/supervisor.py`): Verify event forwarding in `run_stream` method

## Next Steps

1. Add logging to track which events are being yielded during workflow `run_stream`
2. Check if execution phase is yielding `MagenticAgentMessageEvent`
3. Verify event forwarding in supervisor's `run_stream` method (lines 378-399)
4. Fix event generation/forwarding to include agent execution results

## Test Verification

After fix, test with:

```bash
curl -X POST http://localhost:8000/api/chat \\
  -H "Content-Type: application/json" \\
  -d '{"conversation_id": "71", "message": "who is trump?", "stream": true}'
```

Expected response should include:

```
data: {"type": "response.delta", "delta": "Do you mean Donald J. Trump? If so...", ...}
```

Instead of:

```
data: {"type": "response.delta", "delta": "who is trump?", "agent_id": "judge_refine"}
```
