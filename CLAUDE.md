# PROJECT ASSISTANT - Development Guide for Claude Code

## 🎯 Project Overview

**Project Assistant** is an MCP-based orchestration system designed to manage software projects within Coder workspaces. It acts as an intelligent layer between AI agents (like Android Assistant, Claude Code) and development environments, providing high-level project management, task tracking, and workflow automation.

### Key Innovation
Unlike traditional project management tools, Project Assistant is **AI-native**: it's designed to be consumed by AI agents via MCP (Model Context Protocol), enabling voice-driven development, autonomous task execution, and intelligent project insights.

---

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────┐
│              EXTERNAL CLIENTS                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Android    │  │  Web UI     │  │  Claude     │    │
│  │  Assistant  │  │  (future)   │  │  Code       │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
└─────────┼─────────────────┼─────────────────┼──────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │ MCP over HTTPS/STDIO
┌───────────────────────────▼─────────────────────────────┐
│         PROJECT ASSISTANT (Coder Workspace)             │
│  ┌──────────────────────────────────────────────────┐  │
│  │  MCP Server Layer (Exposed to clients)           │  │
│  │  • project.status                                │  │
│  │  • project.list_available                        │  │
│  │  • project.suggest_next_steps                    │  │
│  │  • tasks.* (create/list/update)                  │  │
│  │  • orchestration.run_workflow                    │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Business Logic Layer                            │  │
│  │  • TaskManager (CRUD + persistence)              │  │
│  │  • ProjectContext (multi-source aggregation)     │  │
│  │  • WorkflowOrchestrator (multi-step automation)  │  │
│  │  • ResearchEngine (AI task execution - future)   │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  MCP Client Layer (Consumes Coder services)     │  │
│  │  • GitMCPClient → mcp-server-git                 │  │
│  │  • GitHubMCPClient → github-mcp-server           │  │
│  │  • FileSystemMCPClient → mcp-server-filesystem   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────┘
                          │ MCP STDIO (local)
┌─────────────────────────▼───────────────────────────────┐
│          CODER NATIVE MCP SERVERS                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ mcp-server-  │  │ mcp-server-  │  │  github-mcp- │ │
│  │ git          │  │ filesystem   │  │  server      │ │
│  │              │  │              │  │  (uses gh)   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          ▼                  ▼                  ▼
    /Projects/*         /Projects/*        GitHub API
    (git repos)         (filesystem)       (via gh CLI)
```

### Key Principles

1. **Leverage Coder Infrastructure**: Don't reimplement what Coder provides
   - Git operations → use `mcp-server-git`
   - GitHub operations → use `github-mcp-server` (wraps `gh` CLI)
   - File operations → use `mcp-server-filesystem`

2. **Focus on Aggregation & Intelligence**
   - Combine data from multiple MCP sources
   - Add business logic (task management, workflows)
   - Provide AI-friendly abstractions

3. **Dual Role Architecture**
   - **MCP Client**: Consume Coder's MCP servers
   - **MCP Server**: Expose high-level tools to external clients

---

## 📁 Project Structure

```
project-assistant/
├── README.md                       # User-facing documentation
├── CLAUDE.md                       # This file - for Claude Code
├── IMPLEMENTATION_PLAN.md          # Detailed implementation roadmap
├── pyproject.toml                  # Python dependencies
├── mcp-client-config.json          # MCP client connections config
│
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Main settings (Pydantic)
│   └── coder.py                    # Coder-specific configuration
│
├── src/
│   ├── __init__.py
│   ├── main.py                     # Entry point (MCP Server)
│   │
│   ├── server/                     # MCP Server (exposed tools)
│   │   ├── __init__.py
│   │   ├── mcp_server.py          # Server initialization
│   │   └── tools/                  # MCP Tools implementation
│   │       ├── __init__.py
│   │       ├── project_tools.py   # project.* tools
│   │       ├── task_tools.py      # tasks.* tools
│   │       └── orchestration_tools.py  # orchestration.* tools
│   │
│   ├── clients/                    # MCP Clients (consume Coder)
│   │   ├── __init__.py
│   │   ├── git_client.py          # mcp-server-git client
│   │   ├── github_client.py       # github-mcp-server client
│   │   └── filesystem_client.py   # mcp-server-filesystem client
│   │
│   ├── core/                       # Business logic
│   │   ├── __init__.py
│   │   ├── project_context.py     # Project state aggregation
│   │   ├── task_manager.py        # Task CRUD + logic
│   │   ├── orchestrator.py        # Workflow execution
│   │   └── suggestions.py         # AI suggestions engine
│   │
│   ├── models/                     # Data models
│   │   ├── __init__.py
│   │   ├── task.py                # Task, TaskType, TaskStatus
│   │   ├── project.py             # ProjectStatus, GitInfo
│   │   └── workflow.py            # Workflow definitions
│   │
│   └── storage/                    # Persistence layer
│       ├── __init__.py
│       └── db.py                   # SQLAlchemy models + operations
│
├── scripts/
│   ├── coder-setup.sh             # Initial setup in Coder
│   ├── start-server.sh            # Start MCP server
│   └── test-mcp.sh                # Manual MCP testing
│
└── tests/
    ├── __init__.py
    ├── test_git_client.py
    ├── test_task_manager.py
    ├── test_project_context.py
    └── test_tools.py
```

---

## 🔧 Technology Stack

### Core Dependencies
- **Python 3.11+**: Runtime
- **MCP SDK**: Model Context Protocol (client + server)
- **Pydantic v2**: Data validation and settings
- **SQLAlchemy**: ORM for task persistence
- **aiosqlite**: Async SQLite driver

### Coder Integration
- **mcp-server-git**: Git operations (pre-installed in Coder)
- **github-mcp-server**: GitHub API via `gh` CLI (pre-installed)
- **mcp-server-filesystem**: File operations (pre-installed)

### Development Tools
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **black**: Code formatting
- **mypy**: Type checking

---

## 🚀 Getting Started in Coder

### Environment Detection
The system auto-detects if it's running in a Coder workspace by checking:
```python
is_coder = os.getenv("CODER_WORKSPACE_NAME") is not None
```

### Expected Coder Environment
- **Projects directory**: `/Projects` (contains git repositories)
- **GitHub CLI**: `gh` authenticated with user's GitHub account
- **Git config**: User's git credentials already configured
- **MCP servers**: Native Coder MCP servers available

### Initial Setup
```bash
# Run the setup script
./scripts/coder-setup.sh

# This will:
# - Verify Coder environment
# - Check gh CLI authentication
# - List available projects in /Projects
# - Install Python dependencies
# - Initialize SQLite database
# - Configure environment variables
```

---

## 📋 MCP Tools Specification

### Project Tools

#### `project.list_available`
Lists all git repositories in `/Projects`.

**Input:** None  
**Output:**
```json
{
  "projects": ["homehub", "ai-assistant", "website"],
  "total": 3,
  "location": "/Projects"
}
```

#### `project.status`
Comprehensive project status aggregating Git, GitHub, and Tasks.

**Input:**
```json
{
  "project_name": "homehub",
  "include_suggestions": true
}
```

**Output:**
```json
{
  "project": "homehub",
  "path": "/Projects/homehub",
  "git": {
    "branch": "feature/oauth2",
    "is_dirty": true,
    "ahead": 2,
    "behind": 0,
    "last_commit": {
      "hash": "a1b2c3d",
      "author": "John Doe",
      "message": "Add OAuth2 flow",
      "date": "2026-01-29T10:30:00Z"
    },
    "modified_files": ["src/auth.py", "tests/test_auth.py"]
  },
  "github": {
    "owner": "johndoe",
    "repo": "homehub",
    "issues": [
      {"number": 23, "title": "Add refresh token", "state": "open"}
    ]
  },
  "tasks": {
    "total": 5,
    "by_status": {"todo": 2, "in_progress": 1, "done": 2},
    "recent": [
      {"id": "task-123", "title": "Implement OAuth2", "status": "in_progress"}
    ]
  },
  "suggestions": [
    {
      "priority": "high",
      "action": "commit_changes",
      "description": "You have uncommitted changes",
      "files": ["src/auth.py", "tests/test_auth.py"]
    }
  ]
}
```

#### `project.suggest_next_steps`
AI-powered suggestions based on project state.

**Input:**
```json
{
  "project_name": "homehub"
}
```

**Output:**
```json
{
  "suggestions": [
    {
      "priority": "high",
      "action": "fix_failing_tests",
      "description": "3 tests are failing in AuthController",
      "can_automate": true
    },
    {
      "priority": "medium",
      "action": "review_issue",
      "description": "Issue #23 has been open for 5 days",
      "issue_number": 23
    }
  ]
}
```

### Task Tools

#### `tasks.list`
List tasks with optional filters.

**Input:**
```json
{
  "project_name": "homehub",
  "status": "in_progress",
  "type": "research"
}
```

#### `tasks.create`
Create a new task.

**Input:**
```json
{
  "project_name": "homehub",
  "type": "research",
  "title": "Investigate ESP32 WiFi 6 compatibility",
  "description": "Need to verify if ESP32-S3 supports WiFi 6",
  "deliverables": [
    {"type": "report", "format": "markdown"},
    {"type": "data", "format": "json"}
  ],
  "create_github_issue": true
}
```

#### `tasks.update`
Update task status or details.

**Input:**
```json
{
  "task_id": "task-123",
  "status": "done",
  "notes": "OAuth2 implementation complete"
}
```

### Orchestration Tools

#### `orchestration.run_workflow`
Execute multi-step workflows.

**Supported workflows:**
- `prepare_pr`: Create branch, commit, push, create PR
- `research_task`: Execute research with AI agent (future)
- `code_review`: Analyze code and create review tasks (future)

**Input:**
```json
{
  "workflow_type": "prepare_pr",
  "project_name": "homehub",
  "parameters": {
    "branch_name": "feature/oauth2",
    "commit_message": "Add OAuth2 authentication",
    "pr_title": "Feature: OAuth2 Support",
    "pr_body": "Implements OAuth2 authentication flow"
  }
}
```

**Output:**
```json
{
  "workflow": "prepare_pr",
  "status": "completed",
  "steps": [
    {"step": 1, "action": "verify_changes", "status": "ok"},
    {"step": 2, "action": "create_branch", "branch": "feature/oauth2", "status": "ok"},
    {"step": 3, "action": "commit", "message": "Add OAuth2...", "status": "ok"},
    {"step": 4, "action": "create_pr", "pr_number": 42, "status": "ok"}
  ],
  "pr_url": "https://github.com/johndoe/homehub/pull/42"
}
```

---

## 💾 Data Models

### Task Model
```python
class TaskType(str, Enum):
    STANDARD = "standard"          # Regular task
    RESEARCH = "research"          # AI-assisted investigation
    DEVELOPMENT = "development"    # Code implementation task

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"

class Task(BaseModel):
    id: str
    project_name: str             # Links to /Projects/{name}
    type: TaskType
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    
    # Assignment
    assigned_to: Optional[str]    # "human" or agent_id
    
    # For research/dev tasks
    deliverables: List[Deliverable]
    context_files: List[str]
    approval_required: bool
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    # GitHub integration
    github_issue_number: Optional[int]
    
    tags: List[str]
```

### ProjectContext Model
```python
class ProjectStatus(BaseModel):
    project: str
    path: str
    git: GitInfo
    github: GitHubInfo
    tasks: TaskSummary
    suggestions: List[Suggestion]
```

---

## 🧪 Testing Strategy

### Unit Tests
- Test each MCP client independently (mock MCP servers)
- Test business logic (TaskManager, ProjectContext)
- Test data models and validation

### Integration Tests
- Test MCP server tools end-to-end
- Test workflows with real Coder MCP servers (in CI)

### Manual Testing
Use MCP Inspector or `mcp-cli`:
```bash
# Test project.status tool
echo '{"method": "tools/call", "params": {"name": "project_status", "arguments": {"project_name": "homehub"}}}' | python -m src.main
```

---

## 🔐 Security Considerations

### Path Validation
- All file operations must stay within `/Projects`
- Prevent directory traversal attacks

### GitHub Token
- Use Coder's pre-authenticated `gh` CLI
- Never store tokens in code or config files

### MCP Server Exposure
- If exposing over HTTPS, implement authentication
- Use SSH tunneling for remote access from Android

---

## 📝 Development Guidelines

### Code Style
- Follow PEP 8
- Use type hints everywhere
- Write docstrings for all public functions
- Use `black` for formatting

### Async Patterns
- All MCP operations are async
- Use `async with` for MCP client sessions
- Handle connection failures gracefully

### Error Handling
```python
try:
    result = await mcp_client.call_tool("some_tool", args)
except MCPError as e:
    logger.error(f"MCP error: {e}")
    return error_response(str(e))
except Exception as e:
    logger.exception("Unexpected error")
    return error_response("Internal error")
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)

# Use structured logging
logger.info("Project status retrieved", extra={
    "project": project_name,
    "duration_ms": duration
})
```

---

## 🎯 MVP Scope (Phase 1)

**Goal**: Basic project status and task management

✅ **Must Have:**
- `project.list_available` tool
- `project.status` tool (Git + GitHub + Tasks)
- `tasks.create/list/update` tools
- Task persistence in SQLite
- Coder environment detection

❌ **Not in MVP:**
- Research task execution
- Multi-agent workflows
- Web dashboard
- Advanced AI suggestions

---

## 🚧 Known Limitations

1. **Single workspace**: Only works in the Coder workspace where it's installed
2. **GitHub dependency**: Requires `gh` CLI authentication
3. **No distributed tasks**: Tasks stored locally in SQLite
4. **Synchronous workflows**: No background job processing yet

---

## 📚 References

- [MCP Specification](https://modelcontextprotocol.io/)
- [Coder Documentation](https://coder.com/docs)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

## 🆘 Common Issues & Solutions

### Issue: MCP client can't connect to mcp-server-git
**Solution:** Verify mcp-server-git is installed: `uvx mcp-server-git --help`

### Issue: gh CLI not authenticated
**Solution:** Run `gh auth login` in the Coder workspace

### Issue: Projects directory not found
**Solution:** Ensure `/Projects` exists and contains git repositories

### Issue: Permission denied writing to database
**Solution:** Check `PROJECT_ASSISTANT_DB` path is writable

---

## 🎓 Next Steps for Development

1. **Read IMPLEMENTATION_PLAN.md** for detailed module breakdown
2. **Run coder-setup.sh** to verify environment
3. **Implement Module 1**: Coder environment detection
4. **Implement Module 2**: MCP clients (git, github)
5. **Implement Module 3**: Basic MCP server with project.status
6. **Test** with MCP Inspector
7. **Iterate** based on feedback

---

**Happy coding! 🚀**
