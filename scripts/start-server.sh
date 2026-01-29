#!/bin/bash
set -e

# Load environment variables if .env exists
if [ -f .env ]; then
  export $(cat .env | xargs)
fi

export PROJECT_ASSISTANT_DB="${PROJECT_ASSISTANT_DB:-$HOME/.project-assistant/db.sqlite}"
export PROJECTS_ROOT="${PROJECTS_ROOT:-/home/coder/Projects}"

echo "Starting Project Assistant MCP Server..."
echo "Database: $PROJECT_ASSISTANT_DB"
echo "Projects: $PROJECTS_ROOT"

PYTHONPATH=. python src/main.py
