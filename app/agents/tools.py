from app.vectorstore import search_documents


def search_document_tool(query: str, document_filter: str = None) -> str:
    """What actually runs when an agent calls search_documents: vector search, formatted as plain text."""
    results = search_documents(query=query, n_results=5, document_filter=document_filter)
    if not results:
        return "No relevant content found in the documents."

    return "\n\n".join(
        f"[Chunk {i} | {r.document_name} | Page {r.page_number}]\n{r.text}"
        for i, r in enumerate(results, start=1)
    )


SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": (
            "Search the uploaded documents for content relevant to a query. "
            "Use this whenever you need specific facts, figures, or text "
            "from the documents to complete your task. Returns the most "
            "relevant text chunks."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query. Be specific — e.g. "
                        "'revenue figures' or 'risk factors related to competition'."
                    ),
                },
                "document_filter": {
                    "type": "string",
                    "description": (
                        "Optional. If set, only search within this specific "
                        "document name. Leave empty to search all documents."
                    ),
                },
            },
            "required": ["query"],
        },
    },
}
