#!/bin/bash
# Push changes to GitHub with a timestamped message
# Usage: ./push_changes.sh "Simple message"

MESSAGE="$1"
if [ -z "$MESSAGE" ]; then
    MESSAGE="Update $(date '+%Y-%m-%d %H:%M:%S')"
fi

echo "🚀 Pushing changes: $MESSAGE"
git add .
git commit -m "$MESSAGE"
git push origin main
echo "✅ Changes pushed successfully!"
