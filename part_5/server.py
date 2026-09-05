import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

from mcp.server import MCPServer

# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).parent

CHROMA_DIR = BASE_DIR / "chroma_db"


# =========================================================
# CLIENTS
# =========================================================

openai_client = OpenAI(
    base_url=os.environ["BASE_URL"],
    api_key=os.environ["API_KEY"],
)

chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

collection = chroma_client.get_or_create_collection(name="documents")


# =========================================================
# MCP SERVER
# =========================================================

mcp = MCPServer("RAG Document Server")


# =========================================================
# EMBEDDING
# =========================================================


def create_query_embedding(
    query: str,
) -> list[float]:

    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )

    return response.data[0].embedding


# =========================================================
# MCP TOOL — SEMANTIC SEARCH
# =========================================================


@mcp.tool()
def search_documents(
    query: str,
    top_k: int = 3,
) -> list[dict]:
    """
    Search documents using semantic similarity.

    Returns the most relevant document chunks.
    """

    if not query.strip():
        return []

    query_embedding = create_query_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    documents = results.get("documents", [[]])[0]

    metadatas = results.get("metadatas", [[]])[0]

    distances = results.get("distances", [[]])[0]

    output = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):

        output.append(
            {
                "filename": metadata["filename"],
                "chunk_index": metadata["chunk_index"],
                "distance": distance,
                "content": document,
            }
        )

    return output


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":
    mcp.run()
