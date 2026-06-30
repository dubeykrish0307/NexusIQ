from app.core.config import settings
from app.core.rag_engine import RAGEngine, RAGResponse

_rag_engine_instance = None


def get_rag_engine() -> RAGEngine:
    """
    Singleton accessor for the RAG engine.
    Same pattern as get_store() from Day 4 — one instance, shared everywhere.
    """
    global _rag_engine_instance
    if _rag_engine_instance is None:
        _rag_engine_instance = RAGEngine()
    return _rag_engine_instance


def ask(question: str, **kwargs) -> RAGResponse:
    """
    The simplest possible interface to the RAG system.
    Any part of NexusIQ can call core.ask("some question") and get an answer.
    """
    engine = get_rag_engine()
    return engine.answer_question(question, **kwargs)