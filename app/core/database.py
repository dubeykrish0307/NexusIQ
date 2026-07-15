import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String,
    DateTime, Text, Float, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nexusiq.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class QuestionLog(Base):
    """
    Every question asked via /analysis/ask gets logged here.
    Enables usage analytics and conversation history.
    """
    __tablename__ = "question_logs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    document_filter = Column(String(255), nullable=True)
    chunks_retrieved = Column(Integer, default=0)
    had_sufficient_context = Column(Integer, default=1)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalysisRun(Base):
    """
    Every full four-agent analysis run gets stored here.
    Stores the complete report so it can be retrieved without re-running.
    """
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String(255), nullable=False, index=True)
    overall_assessment = Column(String(50), nullable=True)
    executive_summary = Column(Text, nullable=True)
    business_analysis = Column(Text, nullable=True)
    validation_notes = Column(Text, nullable=True)
    outlook = Column(Text, nullable=True)
    report_confidence = Column(String(20), nullable=True)
    financial_snapshot = Column(JSON, nullable=True)
    risk_landscape = Column(JSON, nullable=True)
    pipeline_stats = Column(JSON, nullable=True)
    agents_run = Column(Integer, default=4)
    total_tool_calls = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentRegistry(Base):
    """
    Tracks every document that has been uploaded and ingested.
    Stores metadata detected during ingestion for quick retrieval.
    """
    __tablename__ = "document_registry"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False, unique=True)
    file_type = Column(String(20), nullable=True)
    document_category = Column(String(100), nullable=True)
    detected_title = Column(String(500), nullable=True)
    detected_date = Column(String(100), nullable=True)
    chunks_created = Column(Integer, default=0)
    char_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency injector for FastAPI route handlers.
    Yields a database session and ensures it closes after the request,
    even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()