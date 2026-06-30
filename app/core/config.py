import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Central configuration for the entire application.
    Every module reads settings from here instead of calling
    os.getenv() scattered throughout the codebase.
    """

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    APP_NAME: str = os.getenv("APP_NAME", "NexusIQ")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    CHAT_MODEL: str = "gpt-4o"
    CHAT_MODEL_FAST: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    DEFAULT_TEMPERATURE: float = 0.1
    DEFAULT_MAX_TOKENS: int = 1500
    DEFAULT_RETRIEVAL_COUNT: int = 5

    CHROMA_PERSIST_DIRECTORY: str = os.getenv(
        "CHROMA_PERSIST_DIRECTORY", "./data/chroma"
    )


settings = Settings()