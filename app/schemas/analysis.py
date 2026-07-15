from pydantic import BaseModel, Field
from typing import Optional


class QuestionRequest(BaseModel):
    """
    Request body for the /ask endpoint.
    Field(...) means required. The constraints are validated automatically.
    """
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The question to answer from the documents"
    )
    document_filter: Optional[str] = Field(
        None,
        description="If set, only search within this document name"
    )
    n_results: Optional[int] = Field(
        5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve (1-20)"
    )


class AnalysisRequest(BaseModel):
    """Request body for the full multi-agent analysis endpoint."""
    document_name: str = Field(
        ...,
        description="Exact filename of the document to analyze"
    )