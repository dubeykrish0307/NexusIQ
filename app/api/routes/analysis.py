from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core import ask, get_rag_engine
from app.agents.orchestrator import Orchestrator
from app.schemas.analysis import QuestionRequest, AnalysisRequest
from app.schemas.report import ReportResponse
from app.core.database import get_db
from app.core.db_operations import (
    log_question,
    log_analysis_run,
    get_analysis_history,
    get_question_history,
    get_usage_stats
)

router = APIRouter()

_orchestrator = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


@router.post("/ask")
async def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db)
):
    """Answer a question using RAG. Logs every interaction."""
    response = ask(
        question=request.question,
        n_results=request.n_results,
        document_filter=request.document_filter
    )

    log_question(
        db=db,
        question=request.question,
        answer=response.answer,
        document_filter=request.document_filter,
        chunks_retrieved=response.chunks_retrieved,
        had_sufficient_context=response.had_sufficient_context,
        model_used=response.model_used
    )

    return {
        "question": response.question,
        "answer": response.answer,
        "sources": [
            {
                "document": s.document_name,
                "page": s.page_number,
                "relevance_score": s.relevance_score,
                "preview": s.text[:200]
            }
            for s in response.sources
        ],
        "model_used": response.model_used,
        "had_sufficient_context": response.had_sufficient_context
    }


@router.post("/ask/stream")
async def ask_question_streaming(request: QuestionRequest):
    """Stream response tokens as they arrive."""
    engine = get_rag_engine()

    def generate():
        for token in engine.answer_question_streaming(
            question=request.question,
            n_results=request.n_results,
            document_filter=request.document_filter
        ):
            yield token

    return StreamingResponse(generate(), media_type="text/plain")


@router.post("/analyze", response_model=ReportResponse)
async def analyze_document(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """Run the full four-agent pipeline. Saves the complete report."""
    orchestrator = get_orchestrator()
    result = orchestrator.analyze_document(
        document_name=request.document_name
    )

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis pipeline failed: {result.error}"
        )

    report = result.final_report
    pipeline_stats = {
        "agents_run": len(result.agent_responses),
        "total_tool_calls": sum(
            len(r.tool_calls_made) for r in result.agent_responses
        ),
        "validation_status": result.validation.get(
            "validation_status"
        ),
        "verified_claims": len(
            result.validation.get("verified_claims", [])
        )
    }

    log_analysis_run(
        db=db,
        document_name=result.document_name,
        report=report,
        pipeline_stats=pipeline_stats
    )

    return ReportResponse(
        document_name=result.document_name,
        overall_assessment=report.get("overall_assessment"),
        executive_summary=report.get("executive_summary"),
        financial_snapshot=report.get("financial_snapshot"),
        business_analysis=report.get("business_analysis"),
        risk_landscape=report.get("risk_landscape"),
        validation_notes=report.get("validation_notes"),
        outlook=report.get("outlook"),
        report_confidence=report.get("report_confidence"),
        pipeline_stats=pipeline_stats,
        success=True
    )


@router.get("/history")
async def get_history(
    document_name: str = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Retrieve past analysis runs.
    Optionally filter by document name.
    """
    runs = get_analysis_history(db, document_name, limit)
    return {
        "runs": [
            {
                "id": r.id,
                "document_name": r.document_name,
                "overall_assessment": r.overall_assessment,
                "report_confidence": r.report_confidence,
                "agents_run": r.agents_run,
                "total_tool_calls": r.total_tool_calls,
                "executive_summary": r.executive_summary,
                "created_at": r.created_at.isoformat()
            }
            for r in runs
        ],
        "total": len(runs)
    }


@router.get("/questions")
async def get_questions(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve recent question history."""
    questions = get_question_history(db, limit)
    return {
        "questions": [
            {
                "id": q.id,
                "question": q.question,
                "answer": q.answer[:300],
                "had_sufficient_context": bool(
                    q.had_sufficient_context
                ),
                "created_at": q.created_at.isoformat()
            }
            for q in questions
        ],
        "total": len(questions)
    }


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Usage statistics across the entire system."""
    return get_usage_stats(db)