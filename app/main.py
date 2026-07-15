from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes.documents import router as documents_router
from app.api.routes.analysis import router as analysis_router

load_dotenv()

app = FastAPI(
    title="NexusIQ",
    description=(
        "Multi-agent document intelligence system. "
        "Upload financial and legal documents, ask questions, "
        "and run deep four-agent analysis pipelines."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check():
    """Health check — confirms the API is running."""
    return {
        "status": "NexusIQ is running",
        "version": "1.0.0",
        "agents": [
            "Extractor",
            "Analyst",
            "Validator",
            "Synthesizer"
        ],
        "endpoints": {
            "docs": "/docs",
            "upload": "/documents/upload",
            "ask": "/analysis/ask",
            "analyze": "/analysis/analyze"
        }
    }


app.include_router(
    documents_router,
    prefix="/documents",
    tags=["Documents"]
)

app.include_router(
    analysis_router,
    prefix="/analysis",
    tags=["Analysis"]
)