Part 5: RAG + MCP

MCP sits between the LLM application and the RAG capability

                    ┌───────────┐
                    │    LLM    │
                    └─────┬─────┘
                          │
                     MCP Tool Call
                          │
                          ▼
                    ┌───────────┐
                    │ MCP Client│
                    └─────┬─────┘
                          │
                          ▼
                    ┌───────────┐
                    │ MCP Server│
                    └─────┬─────┘
                          │
                          ▼
                     RAG Search
                          │
                    ┌─────┴─────┐
                    ▼           ▼
               Embeddings   ChromaDB
                    │           │
                    └─────┬─────┘
                          ▼
                   Relevant chunks
                          │
                          ▼
                         LLM


This is the most important experiment.

Previously:

what is mcp?

worked because the exact string "mcp" existed in the document.

Now try something that doesn't use the same words.

For example:

You: How can an AI application connect to external services?


So you can have:

MCP + RAG
MCP + GitHub
MCP + PostgreSQL
MCP + filesystem
MCP + web search
MCP + Django
MCP + Stripe