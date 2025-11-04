#!/bin/bash
echo "=== Copilot Suggestions Summary ==="
for PR in 291 292 293 294 295 296 297 298; do
  COUNT=$(gh api "/repos/Qredence/agentic-fleet/pulls/$PR/comments" 2>/dev/null | jq '[.[] | select(.body | contains("```suggestion"))] | length' 2>/dev/null || echo "0")
  printf "PR #%d: %d suggestions\n" "$PR" "$COUNT"
done
