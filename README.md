# Fulcrum

Fulcrum es un gestor de proyectos agentico, pensado para integrarse con Coder (https://coder.com) y GitHub Codespaces.

## Features

- **Project Status**: Get a high-level overview of any project in `/Projects`.
- **Git Integration**: Sees branch info, dirty state, and recent commits via `mcp-server-git`.
- **GitHub Integration**: Lists issues and PRs via `github-mcp-server`.
- **Task Management**: Create, track, and update tasks for each project.
- **AI Suggestions**: Actionable next steps based on project state.

## Installation in Coder

1. Clone this repository into your workspace.
2. Run the setup script:
   ```bash
   bash scripts/coder-setup.sh
   ```
3. Start the MCP server:
   ```bash
   bash scripts/start-server.sh
   ```

## MCP Tools

### `project.list_available`
Lists all git repositories in `/Projects`.

### `project.status`
Comprehensive project status aggregating Git, GitHub, and Tasks.

### `project.suggest_next_steps`
AI-powered suggestions based on project state.

### `tasks.list`
List tasks with optional filters.

### `tasks.create`
Create a new task.

### `tasks.update`
Update task status.

## Configuration

- `PROJECTS_ROOT`: Directory containing projects (default: `/home/coder/Projects`)
- `DATABASE_URL`: Postgres DSN (default in Docker: `postgresql+asyncpg://postgres:postgres@db:5432/fulcrum`)
- `GITHUB_TOKEN`: GitHub Personal Access Token (can be retrieved from `gh auth token`)

## Notes

- The app uses Postgres (see `docker-compose.yml`) and does not use SQLite.

## License
MIT
