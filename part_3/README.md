Part 3 — MCP + LLM + Tool Calling 🤖

                  User
                   │
                   ▼
             ┌───────────┐
             │    LLM    │
             └─────┬─────┘
                   │
             decides tool
                   │
                   ▼
             ┌───────────┐
             │ MCP Client│
             └─────┬─────┘
                   │
                   ▼
             ┌───────────┐
             │MCP Server │
             └─────┬─────┘
                   │
             percentage()
             multiply()
                   │
                   ▼
                 result

pip install openai python-dotenv

Create:

.env

with:

OPENAI_API_KEY=your_api_key_here


USER
│
│ "What is 15% of 240?"
▼
LLM
│
│ percentage(240,15)
▼
MCP CLIENT
│
│ call tool
▼
MCP SERVER
│
│
▼
30
│
│ tool result
▼
LLM
│
▼
"15% of 240 is 30."