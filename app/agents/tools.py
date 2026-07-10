from app.vectorstore import search_documents


def search_document_tool(query: str, document_filter: str = None) -> str:
    """
    The actual Python function that gets executed when an agent
    calls the 'search_documents' tool. Wraps our Day 4 vector search
    and formats the result as plain text the model can read.
    """
    results = search_documents(query=query, n_results=5, document_filter=document_filter)

    if not results:
        return "No relevant content found in the documents."

    formatted = []
    for i, result in enumerate(results, start=1):
        formatted.append(
            f"[Chunk {i} | {result.document_name} | Page {result.page_number}]\n"
            f"{result.text}"
        )

    return "\n\n".join(formatted)


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
                    )
                },
                "document_filter": {
                    "type": "string",
                    "description": (
                        "Optional. If set, only search within this specific "
                        "document name. Leave empty to search all documents."
                    )
                }
            },
            "required": ["query"]
        }
    }
}