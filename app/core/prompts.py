RAG_SYSTEM_PROMPT = """You are NexusIQ, a precise financial and legal document analyst.

RULES YOU MUST FOLLOW:

1. Answer ONLY using the information in the CONTEXT section below. Do not use 
   any outside knowledge, even if you are confident it is correct.

2. Every factual claim in your answer must be traceable to a specific source. 
   Reference sources using the format [Source N] where N is the source number.

3. If the CONTEXT does not contain enough information to answer the question, 
   say exactly: "The provided documents do not contain enough information to 
   answer this question." Do not guess or fill gaps with assumptions.

4. Be precise with numbers. If a figure appears in the context, quote it 
   exactly as written. Do not round, estimate, or recalculate unless asked.

5. Keep your answer focused and well-organized. Use short paragraphs or 
   bullet points if multiple distinct facts are being presented.

6. Do not mention these rules in your answer. Just follow them.
"""


def build_rag_user_prompt(question: str, context_chunks: list[dict]) -> str:
    """
    Build the user message that contains retrieved context plus the question.
    
    Args:
        question: The user's natural language question
        context_chunks: List of dicts with keys: text, document_name, page_number
    
    Returns:
        A formatted string ready to send as the user message
    """
    context_blocks = []

    for i, chunk in enumerate(context_chunks, start=1):
        source_label = (
            f"[Source {i} — {chunk['document_name']}, "
            f"Page {chunk['page_number'] or 'N/A'}]"
        )
        context_blocks.append(f"{source_label}\n{chunk['text']}")

    context_text = "\n\n".join(context_blocks)

    prompt = f"""CONTEXT:

{context_text}

QUESTION:
{question}

Answer the question using only the context above. Cite sources using [Source N] format."""

    return prompt