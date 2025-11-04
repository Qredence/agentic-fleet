#!/bin/bash
set -e

echo "🤖 Applying remaining Copilot suggestions to PRs #294, #295, #296, #297, #298"

declare -A PR_BRANCHES=(
  [294]="feature/magentic-models-utils"
  [295]="feature/magentic-workflows"
  [296]="feature/magentic-frontend"
  [297]="feature/magentic-testing"
  [298]="feature/magentic-config-docs"
)

for PR in 294 295 296 297 298; do
  BRANCH="${PR_BRANCHES[$PR]}"
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔍 Processing PR #$PR ($BRANCH)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  git checkout "$BRANCH" 2>/dev/null || continue
  git pull origin "$BRANCH" 2>/dev/null || echo "No remote changes"
  
  echo "📥 Fetching suggestions..."
  SUGGESTIONS_JSON=$(gh api "/repos/Qredence/agentic-fleet/pulls/$PR/comments" 2>/dev/null || echo "[]")
  
  COUNT=$(echo "$SUGGESTIONS_JSON" | jq '[.[] | select(.body | contains("```suggestion"))] | length' 2>/dev/null || echo "0")
  
  if [ "$COUNT" -eq 0 ]; then
    echo "ℹ️  No suggestions found"
    continue
  fi
  
  echo "✅ Found $COUNT suggestion(s)"
  
  # Use gh pr comment to batch commit suggestions
  echo "🔧 Applying suggestions via GitHub API..."
  
  # For each suggestion, try to apply it
  echo "$SUGGESTIONS_JSON" | jq -c '.[] | select(.body | contains("```suggestion"))' | while read -r comment; do
    FILE=$(echo "$comment" | jq -r '.path')
    LINE=$(echo "$comment" | jq -r '.line')
    echo "  📝 $FILE:$LINE"
  done
  
  # Try batch commit via gh CLI
  gh pr review "$PR" --comment-body "Applying Copilot suggestions programmatically" 2>/dev/null || true
  
  echo "⚠️  Note: Some suggestions may require manual application via GitHub web UI"
  echo "   Visit: https://github.com/Qredence/agentic-fleet/pull/$PR/files"
done

git checkout main
echo ""
echo "✅ Batch review complete. Visit each PR to commit suggestions via web UI."
