# Research: MCP vs Agent-to-Agent (A2A) for Fulcrum

## Objective
Decide how Fulcrum (Cloud) will talk to Remote Workspaces (Coder/GitHub).

## Option 1: MCP (Model Context Protocol) Bridge
- **Pros**: Standardized, handles tool definitions well, allows using existing MCP servers like `mcp-server-git`.
- **Cons**: Requires a bridge at the cloud level to proxy STDIO/SSE. Remote workspaces must host the MCP server.

## Option 2: Agent-to-Agent (A2A)
- **Pros**: More flexible for complex coordination. Can use existing protocols like OpenAgent.
- **Cons**: Newer, less standardized tools. Might require more boilerplate.

## Hybrid Approach
- Use MCP for simple tool execution (Git, FS).
- Use A2A for high-level coordination between the Cloud PM Agent and a Local Workspace Agent.

## Recommendation (Preliminary)
Leverage an **MCP-over-SSE/WebSocket bridge**. The Cloud PM Agent acts as an MCP client that connects to an MCP host running in the user's Coder workspace.
