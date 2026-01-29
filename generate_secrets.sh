#!/bin/bash

# Initialize secrets if .env doesn't exist
if [ ! -f .env ]; then
    echo "🚀 Initializing random secrets..."
    python3 scripts/init-secrets.py
else
    echo "⚠️  .env already exists. Run 'rm .env' first if you want to re-generate."
fi

echo "✅ Secrets generation complete."
echo "Use 'docker-compose up --build' to start the services."
