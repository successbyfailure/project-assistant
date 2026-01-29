#!/bin/bash
set -e

echo "🚀 Starting Project Assistant Setup..."

# 1. Verify Coder Environment
if [ -z "$CODER_WORKSPACE_NAME" ] && [ "$CODER" != "true" ]; then
    echo "⚠️ Warning: Not running in a Coder workspace."
else
    echo "✅ Running in Coder workspace: ${CODER_WORKSPACE_NAME:-unknown}"
fi

# 2. Check Projects Directory
PROJECTS_ROOT=${PROJECTS_ROOT:-"/home/coder/Projects"}
if [ -d "$PROJECTS_ROOT" ]; then
    echo "✅ Projects directory found: $PROJECTS_ROOT"
    ls -d $PROJECTS_ROOT/*/ 2>/dev/null | wc -l | xargs echo "📁 Projects found:"
else
    echo "❌ Projects directory NOT found: $PROJECTS_ROOT"
    mkdir -p "$PROJECTS_ROOT"
    echo "📁 Created projects directory: $PROJECTS_ROOT"
fi

# 3. Check GitHub CLI Auth
if gh auth status >/dev/null 2>&1; then
    echo "✅ GitHub CLI is authenticated."
else
    echo "❌ GitHub CLI is NOT authenticated. Please run 'gh auth login'."
fi

# 4. Install Dependencies
echo "📦 Installing dependencies..."
pip install -e ".[dev]"

# 5. Initialize Database (placeholder for now)
DB_PATH="$HOME/.project-assistant/db.sqlite"
mkdir -p "$(dirname "$DB_PATH")"
echo "🗄️ Database location: $DB_PATH"

echo "✨ Setup complete!"
