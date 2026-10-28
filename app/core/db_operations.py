from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import AnalysisRun, DocumentRegistry, QuestionLog


def _save(db: Session, row):
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def log_question(
    db: Session,
    question: str,
    answer: str,
    document_filter: str = None,
    chunks_retrieved: int = 0,
    had_sufficient_context: bool = True,
    model_used: str = None,
) -> QuestionLog:
    return _save(db, QuestionLog(
        question=question,
        answer=answer,
        document_filter=document_filter,
        chunks_retrieved=chunks_retrieved,
        had_sufficient_context=1 if had_sufficient_context else 0,
        model_used=model_used,
    ))


def log_analysis_run(db: Session, document_name: str, report: dict, pipeline_stats: dict) -> AnalysisRun:
    return _save(db, AnalysisRun(
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
        total_tool_calls=pipeline_stats.get("total_tool_calls", 0),
    ))


def register_document(
    db: Session,
    file_name: str,
    file_type: str,
    document_category: str,
    detected_title: str,
    detected_date: str,
    chunks_created: int,
    char_count: int,
    word_count: int,
) -> DocumentRegistry:
    """Insert the document, or refresh its details if the same file was uploaded before."""
    doc = db.query(DocumentRegistry).filter(DocumentRegistry.file_name == file_name).first()

    if doc is None:
        doc = DocumentRegistry(file_name=file_name, file_type=file_type)
        db.add(doc)
    else:
        doc.uploaded_at = datetime.utcnow()

    doc.document_category = document_category
    doc.detected_title = detected_title
    doc.detected_date = detected_date
    doc.chunks_created = chunks_created
    doc.char_count = char_count
    doc.word_count = word_count

    db.commit()
    db.refresh(doc)
    return doc


def get_analysis_history(db: Session, document_name: str = None, limit: int = 20) -> list[AnalysisRun]:
    query = db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc())
    if document_name:
        query = query.filter(AnalysisRun.document_name == document_name)
    return query.limit(limit).all()


def get_question_history(db: Session, limit: int = 50) -> list[QuestionLog]:
    return db.query(QuestionLog).order_by(QuestionLog.created_at.desc()).limit(limit).all()


def get_usage_stats(db: Session) -> dict:
    total_questions = db.query(QuestionLog).count()
    answered = db.query(QuestionLog).filter(QuestionLog.had_sufficient_context == 1).count()
    success_rate = round(answered / total_questions * 100, 1) if total_questions > 0 else 0

    recent = db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(5).all()

    return {
        "total_questions": total_questions,
        "total_analyses": db.query(AnalysisRun).count(),
        "total_documents": db.query(DocumentRegistry).count(),
        "context_success_rate": success_rate,
        "recent_analyses": [
            {
                "document": r.document_name,
                "assessment": r.overall_assessment,
                "confidence": r.report_confidence,
                "timestamp": r.created_at.isoformat(),
            }
            for r in recent
        ],
    }
