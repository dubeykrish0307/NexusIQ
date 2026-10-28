from app.core.config import settings
from app.core.rag_engine import RAGEngine, RAGResponse

__all__ = ["settings", "RAGEngine", "RAGResponse", "get_rag_engine", "ask"]

_rag_engine = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine


def ask(question: str, **kwargs) -> RAGResponse:
    return get_rag_engine().answer_question(question, **kwargs)
