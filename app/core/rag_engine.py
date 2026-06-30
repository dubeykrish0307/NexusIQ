import os
from dataclasses import dataclass, field
from openai import OpenAI
from dotenv import load_dotenv

from app.core.config import settings
from app.core.prompts import RAG_SYSTEM_PROMPT, build_rag_user_prompt
from app.vectorstore import search_documents
from app.vectorstore.store import SearchResult

load_dotenv()


@dataclass
class RAGResponse:
    """
    The complete output of a RAG query.
    Contains the answer plus full traceability back to source chunks.
    """
    question: str
    answer: str
    sources: list[SearchResult]
    model_used: str
    chunks_retrieved: int
    had_sufficient_context: bool


class RAGEngine:
    """
    Connects the vector store (retrieval) to the LLM (generation).
    This is the core question-answering capability of NexusIQ.
    """

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def answer_question(
        self,
        question: str,
        n_results: int = None,
        document_filter: str = None,
        model: str = None
    ) -> RAGResponse:
        """
        The full RAG pipeline: retrieve relevant chunks, build a prompt,
        call the LLM, return a structured answer with sources.
        """
        n_results = n_results or settings.DEFAULT_RETRIEVAL_COUNT
        model = model or settings.CHAT_MODEL

        search_results = search_documents(
            query=question,
            n_results=n_results,
            document_filter=document_filter
        )

        if not search_results:
            return RAGResponse(
                question=question,
                answer=(
                    "No documents have been uploaded yet, or no relevant "
                    "content was found. Please upload a document first."
                ),
                sources=[],
                model_used=model,
                chunks_retrieved=0,
                had_sufficient_context=False
            )

        context_chunks = [
            {
                "text": result.text,
                "document_name": result.document_name,
                "page_number": result.page_number
            }
            for result in search_results
        ]

        user_prompt = build_rag_user_prompt(question, context_chunks)

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=settings.DEFAULT_TEMPERATURE,
            max_tokens=settings.DEFAULT_MAX_TOKENS
        )

        answer = response.choices[0].message.content

        had_sufficient_context = (
            "do not contain enough information" not in answer.lower()
        )

        return RAGResponse(
            question=question,
            answer=answer,
            sources=search_results,
            model_used=model,
            chunks_retrieved=len(search_results),
            had_sufficient_context=had_sufficient_context
        )
    
    def answer_question_streaming(
        self,
        question: str,
        n_results: int = None,
        document_filter: str = None,
        model: str = None
    ):
        """
        Same as answer_question, but yields tokens as they're generated
        instead of waiting for the full response. Used for the live
        'typing' effect in the Streamlit UI.
        
        This is a generator function — it yields text chunks one at a time
        rather than returning a single value.
        """
        n_results = n_results or settings.DEFAULT_RETRIEVAL_COUNT
        model = model or settings.CHAT_MODEL

        search_results = search_documents(
            query=question,
            n_results=n_results,
            document_filter=document_filter
        )

        if not search_results:
            yield "No documents have been uploaded yet. Please upload a document first."
            return

        context_chunks = [
            {
                "text": result.text,
                "document_name": result.document_name,
                "page_number": result.page_number
            }
            for result in search_results
        ]

        user_prompt = build_rag_user_prompt(question, context_chunks)

        stream = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=settings.DEFAULT_TEMPERATURE,
            max_tokens=settings.DEFAULT_MAX_TOKENS,
            stream=True
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta