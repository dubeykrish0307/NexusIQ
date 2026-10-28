from dataclasses import dataclass

from openai import OpenAI

from app.core.config import settings
from app.core.prompts import RAG_SYSTEM_PROMPT, build_rag_user_prompt
from app.vectorstore import search_documents
from app.vectorstore.store import SearchResult

NO_CONTEXT_PHRASE = "do not contain enough information"


@dataclass
class RAGResponse:
    question: str
    answer: str
    sources: list[SearchResult]
    model_used: str
    chunks_retrieved: int
    had_sufficient_context: bool


class RAGEngine:
    """Retrieve the most relevant chunks, then let the model answer from them only."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def _retrieve(self, question, n_results, document_filter):
        return search_documents(
            query=question,
            n_results=n_results or settings.DEFAULT_RETRIEVAL_COUNT,
            document_filter=document_filter,
        )

    def _complete(self, question, results, model, stream=False):
        context = [
            {"text": r.text, "document_name": r.document_name, "page_number": r.page_number}
            for r in results
        ]
        return self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": build_rag_user_prompt(question, context)},
            ],
            temperature=settings.DEFAULT_TEMPERATURE,
            max_tokens=settings.DEFAULT_MAX_TOKENS,
            stream=stream,
        )

    def answer_question(
        self,
        question: str,
        n_results: int = None,
        document_filter: str = None,
        model: str = None,
    ) -> RAGResponse:
        model = model or settings.CHAT_MODEL
        results = self._retrieve(question, n_results, document_filter)

        if not results:
            return RAGResponse(
                question=question,
                answer=(
                    "No documents have been uploaded yet, or no relevant "
                    "content was found. Please upload a document first."
                ),
                sources=[],
                model_used=model,
                chunks_retrieved=0,
                had_sufficient_context=False,
            )

        answer = self._complete(question, results, model).choices[0].message.content

        return RAGResponse(
            question=question,
            answer=answer,
            sources=results,
            model_used=model,
            chunks_retrieved=len(results),
            # the system prompt tells the model to use this exact phrase when it can't answer
            had_sufficient_context=NO_CONTEXT_PHRASE not in answer.lower(),
        )

    def answer_question_streaming(
        self,
        question: str,
        n_results: int = None,
        document_filter: str = None,
        model: str = None,
    ):
        """Same as answer_question, but yields the answer piece by piece as it's generated."""
        model = model or settings.CHAT_MODEL
        results = self._retrieve(question, n_results, document_filter)

        if not results:
            yield "No documents have been uploaded yet. Please upload a document first."
            return

        for chunk in self._complete(question, results, model, stream=True):
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
