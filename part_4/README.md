Part 4 — Tools vs Resources

A tool means:

"The AI can ask the server to perform an action."

But MCP also has resources.

A resource means:

"The server has some context/data that the client can read."

Think about the difference:

TOOL                         RESOURCE
────                         ────────
"Do something"               "Give me something"

calculate()                  document
create_ticket()              configuration
send_email()                 database record
search_database()            README


                    ┌─────────────────────┐
                    │    client.py        │
                    │                     │
User question ────► │ MCP Client          │
                    └──────────┬──────────┘
                               │
                         MCP / stdio
                               │
                    ┌──────────▼──────────┐
                    │ document_server.py  │
                    │                     │
                    │ Tools:              │
                    │  search_documents   │
                    │                     │
                    │ Resources:          │
                    │  document://{file}  │
                    └──────────┬──────────┘
                               │
                         documents/
                         ├── mcp.txt
                         ├── python.txt
                         └── django.txt