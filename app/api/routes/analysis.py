from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core import ask
from app.core import get_rag_engine
from app.agents.orchestrator import Orchestrator
from app.schemas.analysis import QuestionRequest, AnalysisRequest
from app.schemas.report import ReportResponse

router = APIRouter()

_orchestrator = None


def get_orchestrator() -> Orchestrator:
    """
    Singleton orchestrator — initialized once at first request,
    reused for all subsequent requests. Avoids re-loading all four
    agents on every API call.
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


@router.post("/ask")
async def ask_question(request: QuestionRequest):
    """
    Answer a question using RAG.
    Fast path — no agent coordination, just retrieve and generate.
    Typical response time: 3-8 seconds.
    """
    response = ask(
        question=request.question,
        n_results=request.n_results,
        document_filter=request.document_filter
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
    """
    Same as /ask but streams response tokens as they arrive.
    Creates the live 'typing' effect in the UI.
    Returns a plain text stream.
    """
    engine = get_rag_engine()

    def generate():
        for token in engine.answer_question_streaming(
            question=request.question,
            n_results=request.n_results,
            document_filter=request.document_filter
        ):
            yield token

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )


@router.post("/analyze", response_model=ReportResponse)
async def analyze_document(request: AnalysisRequest):
    """
    Run the full four-agent pipeline on a document.
    Extractor → Analyst → Validator → Synthesizer.
    Typical response time: 60-90 seconds.
    Returns a complete structured intelligence report.
    """
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