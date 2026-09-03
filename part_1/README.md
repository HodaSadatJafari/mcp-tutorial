Part 1 — Build Your First MCP Server
We're going to build a Calculator MCP Server in Python from scratch.

pip install "mcp[cli]"

pip show mcp

uv run mcp dev server.py

Inspector
   │
   │ connect
   ▼
MCP Server
   │
   │ "What tools do you have?"
   ▼
tools/list
   │
   ▼
┌─────────────────────────┐
│ add                     │
│ subtract                │
│ multiply                │
│ divide                  │
└─────────────────────────┘