#!/bin/bash
set -e

# Apply Copilot suggestions across all 8 PRs
# Usage: ./apply_copilot_suggestions.sh

echo "🤖 Fetching and applying Copilot suggestions across PRs #291-298"
echo ""

PRS=(291 292 293 294 295 296 297 298)
BRANCHES=(
  "feature/magentic-core"
  "feature/magentic-agents"
  "feature/magentic-api-responses"
  "feature/magentic-models-utils"
  "feature/magentic-workflows"
  "feature/magentic-frontend"
  "feature/magentic-testing"
  "feature/magentic-config-docs"
)

# Store current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Current branch: $CURRENT_BRANCH"
echo ""

for i in "${!PRS[@]}"; do
  PR="${PRS[$i]}"
  BRANCH="${BRANCHES[$i]}"
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔍 Processing PR #$PR ($BRANCH)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  # Checkout the branch
  echo "📥 Checking out $BRANCH..."
  git checkout "$BRANCH" 2>/dev/null || {
    echo "❌ Failed to checkout $BRANCH"
    continue
  }
  
  # Pull latest changes
  echo "🔄 Pulling latest changes..."
  git pull origin "$BRANCH" 2>/dev/null || echo "⚠️  No remote changes"
  
  # Get PR review comments with suggestions
  echo "🔍 Fetching Copilot review comments..."
  
  # Fetch review comments as JSON
  COMMENTS=$(gh api \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/Qredence/agentic-fleet/pulls/$PR/comments" 2>/dev/null || echo "[]")
  
  # Count suggestions
  SUGGESTION_COUNT=$(echo "$COMMENTS" | jq '[.[] | select(.body | contains("```suggestion"))] | length' 2>/dev/null || echo "0")
  
  if [ "$SUGGESTION_COUNT" -eq 0 ]; then
    echo "ℹ️  No Copilot suggestions found for PR #$PR"
    echo ""
    continue
  fi
  
  echo "✅ Found $SUGGESTION_COUNT suggestion(s)"
  
  # Process each suggestion
  echo "$COMMENTS" | jq -c '.[] | select(.body | contains("```suggestion"))' | while read -r comment; do
    # Extract file path, line info, and suggestion
    FILE_PATH=$(echo "$comment" | jq -r '.path')
    START_LINE=$(echo "$comment" | jq -r '.start_line // .line')
    END_LINE=$(echo "$comment" | jq -r '.line')
    BODY=$(echo "$comment" | jq -r '.body')
    COMMENT_ID=$(echo "$comment" | jq -r '.id')
    
    # Extract suggestion code block
    SUGGESTION=$(echo "$BODY" | sed -n '/```suggestion/,/```/p' | sed '1d;$d')
    
    if [ -z "$SUGGESTION" ]; then
      echo "⚠️  Could not extract suggestion from comment $COMMENT_ID"
      continue
    fi
    
    echo "  📝 Applying suggestion to $FILE_PATH (lines $START_LINE-$END_LINE)"
    
    # Create temp file with suggestion
    TEMP_FILE=$(mktemp)
    echo "$SUGGESTION" > "$TEMP_FILE"
    
    # Apply the suggestion (this is a simplified approach)
    # For production, you'd want more sophisticated patch application
    if [ -f "$FILE_PATH" ]; then
      # Read original file
      if [ "$START_LINE" = "$END_LINE" ]; then
        # Single line replacement
        sed -i.bak "${START_LINE}s|.*|$(cat $TEMP_FILE)|" "$FILE_PATH"
      else
        # Multi-line replacement (more complex - using temporary approach)
        {
          head -n $((START_LINE - 1)) "$FILE_PATH"
          cat "$TEMP_FILE"
          tail -n +$((END_LINE + 1)) "$FILE_PATH"
        } > "${FILE_PATH}.new"
        mv "${FILE_PATH}.new" "$FILE_PATH"
      fi
      
      rm -f "$TEMP_FILE" "${FILE_PATH}.bak"
      echo "  ✅ Applied suggestion to $FILE_PATH"
    else
      echo "  ❌ File not found: $FILE_PATH"
      rm -f "$TEMP_FILE"
    fi
  done
  
  # Check if there are changes to commit
  if git diff --quiet; then
    echo "ℹ️  No changes to commit for PR #$PR"
  else
    echo "💾 Committing changes..."
    git add -A
    git commit -m "Apply Copilot review suggestions for PR #$PR" --no-verify
    
    echo "📤 Pushing changes..."
    git push origin "$BRANCH"
    
    echo "✅ Successfully applied and pushed suggestions for PR #$PR"
  fi
  
  echo ""
done

# Return to original branch
echo "📍 Returning to original branch: $CURRENT_BRANCH"
git checkout "$CURRENT_BRANCH"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Copilot suggestion processing complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
