import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from mcp.server import MCPServer

# ============================================================
# Configuration
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).parent
CHROMA_DIR = BASE_DIR / "chroma_db"

EMBEDDING_MODEL = "text-embedding-3-small"

DEFAULT_TOP_K = 5
MAX_TOP_K = 10

# IMPORTANT:
# This is only a starting value.
# You should tune it based on your own documents and queries.
SIMILARITY_THRESHOLD = 0.55


# ============================================================
# Clients
# ============================================================

openai_client = OpenAI(
    base_url=os.environ["BASE_URL"],
    api_key=os.environ["API_KEY"],
)

chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

collection = chroma_client.get_or_create_collection(name="documents")

mcp = MCPServer("RAG Document Server")


# ============================================================
# Embeddings
# ============================================================


def create_query_embedding(query: str) -> list[float]:
    """
    Convert the user's query into an embedding vector.
    """

    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
    )

    return response.data[0].embedding


# ============================================================
# Search
# ============================================================


@mcp.tool()
def search_documents(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    filename: str | None = None,
) -> dict:
    """
    Search the document collection using semantic similarity.

    Args:
        query:
            Natural-language question or search query.

        top_k:
            Maximum number of chunks to retrieve.

        filename:
            Optional filename filter.

    Returns:
        A structured response containing relevant document chunks,
        metadata, similarity distance, and source information.
    """

    # --------------------------------------------------------
    # Validate query
    # --------------------------------------------------------

    query = query.strip()

    if not query:
        return {
            "query": query,
            "results": [],
            "message": "Query cannot be empty.",
        }

    # --------------------------------------------------------
    # Validate top_k
    # --------------------------------------------------------

    if top_k < 1:
        top_k = DEFAULT_TOP_K

    top_k = min(top_k, MAX_TOP_K)

    # --------------------------------------------------------
    # Validate filename filter
    # --------------------------------------------------------

    if filename is not None:
        filename = filename.strip()

        if not filename:
            filename = None

    # --------------------------------------------------------
    # Create query embedding
    # --------------------------------------------------------
    print("**************")
    print(query)
    query_embedding = create_query_embedding(query)

    # --------------------------------------------------------
    # Build metadata filter
    # --------------------------------------------------------

    where = None

    if filename:
        where = {"filename": filename}

    # --------------------------------------------------------
    # Query ChromaDB
    # --------------------------------------------------------

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
    )

    # --------------------------------------------------------
    # Extract results
    # --------------------------------------------------------

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    relevant_results = []

    # --------------------------------------------------------
    # Apply similarity threshold
    # --------------------------------------------------------

    for document, metadata, distance, chunk_id in zip(
        documents,
        metadatas,
        distances,
        ids,
    ):
        if distance < SIMILARITY_THRESHOLD:
            continue

        filename_value = metadata.get(
            "filename",
            "unknown",
        )

        chunk_index = metadata.get(
            "chunk_index",
            -1,
        )

        # ----------------------------------------------------
        # Convert distance to a simple relevance score.
        #
        # This is NOT a universal similarity formula.
        # It is only a convenient score for displaying results.
        # Lower cosine distance => higher relevance.
        # ----------------------------------------------------

        relevance_score = max(
            0.0,
            1.0 - distance,
        )

        relevant_results.append(
            {
                "id": chunk_id,
                "filename": filename_value,
                "chunk_index": chunk_index,
                "distance": round(distance, 4),
                "relevance_score": round(
                    relevance_score,
                    4,
                ),
                "source": filename_value,
                "content": document,
            }
        )

    # --------------------------------------------------------
    # Return structured result
    # --------------------------------------------------------

    return {
        "query": query,
        "results": relevant_results,
        "result_count": len(relevant_results),
    }


# ============================================================
# List available documents
# ============================================================


@mcp.tool()
def list_documents() -> dict:
    """
    List all documents currently stored in the vector database.
    """

    results = collection.get(include=["metadatas"])

    metadatas = results.get(
        "metadatas",
        [],
    )

    documents = {}

    for metadata in metadatas:
        if not metadata:
            continue

        filename = metadata.get("filename")

        if filename:
            documents[filename] = True

    filenames = sorted(documents.keys())

    return {
        "documents": filenames,
        "count": len(filenames),
    }


# ============================================================
# Collection information
# ============================================================


@mcp.tool()
def collection_info() -> dict:
    """
    Return information about the RAG vector collection.
    """

    return {
        "collection": collection.name,
        "document_chunks": collection.count(),
        "embedding_model": EMBEDDING_MODEL,
        "default_top_k": DEFAULT_TOP_K,
        "max_top_k": MAX_TOP_K,
        "similarity_threshold": SIMILARITY_THRESHOLD,
    }


# ============================================================
# Server
# ============================================================

if __name__ == "__main__":
    mcp.run()
