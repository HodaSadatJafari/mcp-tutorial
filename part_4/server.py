from pathlib import Path

from mcp.server import MCPServer

# ---------------------------------------------------------
# MCP SERVER
# ---------------------------------------------------------
mcp = MCPServer("Document Server")


# ---------------------------------------------------------
# DOCUMENT DIRECTORY
# ---------------------------------------------------------
DOCUMENTS_DIR = Path(__file__).parent / "documents"


def get_document_path(filename: str) -> Path:
    """
    Safely resolve a document path.

    This prevents paths such as:
        ../../some-file
    from escaping the documents directory.
    """

    documents_dir = DOCUMENTS_DIR.resolve()
    path = (documents_dir / filename).resolve()

    if not path.is_relative_to(documents_dir):
        raise ValueError("Access outside the documents directory is not allowed.")

    if path.suffix.lower() != ".txt":
        raise ValueError("Only .txt documents are supported.")

    if not path.exists():
        raise ValueError(f"Document not found: {filename}")

    if not path.is_file():
        raise ValueError(f"Not a file: {filename}")

    return path


# ---------------------------------------------------------
# TOOL
# ---------------------------------------------------------
@mcp.tool()
def search_documents(query: str) -> list[str]:
    """
    Search all documents for a text query.

    Returns the filenames of documents containing the query.
    """

    query = query.strip().lower()

    if not query:
        return []

    results = []

    for path in DOCUMENTS_DIR.glob("*.txt"):
        text = path.read_text(encoding="utf-8")

        if query in text.lower():
            results.append(path.name)

    return results


# ---------------------------------------------------------
# RESOURCE
# ---------------------------------------------------------
@mcp.resource(
    "document://{filename}",
    name="document",
    description="Read a text document by filename.",
    mime_type="text/plain",
)
def read_document(filename: str) -> str:
    """
    Read a document from the documents directory.
    """

    path = get_document_path(filename)

    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
