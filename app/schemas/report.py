from pydantic import BaseModel
from typing import Optional


class ReportResponse(BaseModel):
    """Complete output of a multi-agent analysis run."""
    document_name: str
    overall_assessment: Optional[str]
    executive_summary: Optional[str]
    financial_snapshot: Optional[dict]
    business_analysis: Optional[str]
    risk_landscape: Optional[list]
    validation_notes: Optional[str]
    outlook: Optional[str]
    report_confidence: Optional[str]
    pipeline_stats: dict
    success: bool
    error: Optional[str] = None