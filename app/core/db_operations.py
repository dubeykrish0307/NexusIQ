from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import QuestionLog, AnalysisRun, DocumentRegistry


def log_question(
    db: Session,
    question: str,
    answer: str,
    document_filter: str = None,
    chunks_retrieved: int = 0,
    had_sufficient_context: bool = True,
    model_used: str = None
) -> QuestionLog:
    """Save a Q&A interaction to the database."""
    log = QuestionLog(
        question=question,
        answer=answer,
        document_filter=document_filter,
        chunks_retrieved=chunks_retrieved,
        had_sufficient_context=1 if had_sufficient_context else 0,
        model_used=model_used
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def log_analysis_run(
    db: Session,
    document_name: str,
    report: dict,
    pipeline_stats: dict
) -> AnalysisRun:
    """Save a complete analysis run to the database."""
    run = AnalysisRun(
        document_name=document_name,
        overall_assessment=report.get("overall_assessment"),
        executive_summary=report.get("executive_summary"),
        business_analysis=report.get("business_analysis"),
        validation_notes=report.get("validation_notes"),
        outlook=report.get("outlook"),
        report_confidence=report.get("report_confidence"),
        financial_snapshot=report.get("financial_snapshot"),
        risk_landscape=report.get("risk_landscape"),
        pipeline_stats=pipeline_stats,
        agents_run=pipeline_stats.get("agents_run", 4),
        total_tool_calls=pipeline_stats.get("total_tool_calls", 0)
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def register_document(
    db: Session,
    file_name: str,
    file_type: str,
    document_category: str,
    detected_title: str,
    detected_date: str,
    chunks_created: int,
    char_count: int,
    word_count: int
) -> DocumentRegistry:
    """
    Register an uploaded document.
    Uses upsert pattern — update if exists, insert if new.
    """
    existing = db.query(DocumentRegistry).filter(
        DocumentRegistry.file_name == file_name
    ).first()

    if existing:
        existing.document_category = document_category
        existing.detected_title = detected_title
        existing.detected_date = detected_date
        existing.chunks_created = chunks_created
        existing.char_count = char_count
        existing.word_count = word_count
        existing.uploaded_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    doc = DocumentRegistry(
        file_name=file_name,
        file_type=file_type,
        document_category=document_category,
        detected_title=detected_title,
        detected_date=detected_date,
        chunks_created=chunks_created,
        char_count=char_count,
        word_count=word_count
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_analysis_history(
    db: Session,
    document_name: str = None,
    limit: int = 20
) -> list[AnalysisRun]:
    """
    Retrieve past analysis runs.
    If document_name is provided, filter to that document only.
    """
    query = db.query(AnalysisRun).order_by(
        AnalysisRun.created_at.desc()
    )
    if document_name:
        query = query.filter(
            AnalysisRun.document_name == document_name
        )
    return query.limit(limit).all()


def get_question_history(
    db: Session,
    limit: int = 50
) -> list[QuestionLog]:
    """Retrieve recent questions, most recent first."""
    return db.query(QuestionLog).order_by(
        QuestionLog.created_at.desc()
    ).limit(limit).all()


def get_usage_stats(db: Session) -> dict:
    """
    Aggregate usage statistics across the entire database.
    Used for the dashboard in the Streamlit UI.
    """
    total_questions = db.query(QuestionLog).count()
    total_analyses = db.query(AnalysisRun).count()
    total_documents = db.query(DocumentRegistry).count()

    sufficient_context = db.query(QuestionLog).filter(
        QuestionLog.had_sufficient_context == 1
    ).count()

    success_rate = (
        round(sufficient_context / total_questions * 100, 1)
        if total_questions > 0 else 0
    )

    recent_analyses = db.query(AnalysisRun).order_by(
        AnalysisRun.created_at.desc()
    ).limit(5).all()

    return {
        "total_questions": total_questions,
        "total_analyses": total_analyses,
        "total_documents": total_documents,
        "context_success_rate": success_rate,
        "recent_analyses": [
            {
                "document": r.document_name,
                "assessment": r.overall_assessment,
                "confidence": r.report_confidence,
                "timestamp": r.created_at.isoformat()
            }
            for r in recent_analyses
        ]
    }