# =========================================================
# Read documents → split them → create embeddings → store them in ChromaDB.
# =========================================================

import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

openai_client = OpenAI(
    base_url=os.environ["BASE_URL"],
    api_key=os.environ["API_KEY"],
)

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).parent

DOCUMENTS_DIR = BASE_DIR / "documents"

CHROMA_DIR = BASE_DIR / "chroma_db"


# =========================================================
# CHROMA
# =========================================================

chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

collection = chroma_client.get_or_create_collection(name="documents")


# =========================================================
# CHUNKING
# =========================================================


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[str]:
    """
    Split text into overlapping chunks.
    """

    text = text.strip()

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# =========================================================
# EMBEDDINGS
# =========================================================


def create_embeddings(
    texts: list[str],
) -> list[list[float]]:

    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )

    return [item.embedding for item in response.data]


# =========================================================
# INGEST DOCUMENTS
# =========================================================


def ingest_documents():

    print("=" * 60)
    print("DOCUMENT INGESTION")
    print("=" * 60)

    all_chunks = []
    all_ids = []
    all_metadata = []

    for document_path in DOCUMENTS_DIR.glob("*.txt"):

        print(f"\nProcessing: " f"{document_path.name}")

        text = document_path.read_text(encoding="utf-8")

        chunks = chunk_text(text)

        print(f"Chunks created: {len(chunks)}")

        for index, chunk in enumerate(chunks):

            chunk_id = f"{document_path.name}" f":chunk:{index}"

            all_chunks.append(chunk)

            all_ids.append(chunk_id)

            all_metadata.append(
                {
                    "filename": document_path.name,
                    "chunk_index": index,
                }
            )

    if not all_chunks:

        print("\nNo documents found.")

        return

    print(f"\nTotal chunks: " f"{len(all_chunks)}")

    print("\nCreating embeddings...")

    embeddings = create_embeddings(all_chunks)

    print("Storing vectors in ChromaDB...")

    collection.upsert(
        ids=all_ids,
        documents=all_chunks,
        embeddings=embeddings,
        metadatas=all_metadata,
    )

    print("\nIngestion completed.")

    print(f"Vectors stored: " f"{collection.count()}")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    ingest_documents()
