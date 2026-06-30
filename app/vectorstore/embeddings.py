import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class EmbeddingGenerator:
    """
    Converts text into vector embeddings using OpenAI's embedding model.
    Handles batching so we never exceed API rate limits.
    """

    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    BATCH_SIZE = 100

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single piece of text.
        Used for query embedding at search time.
        """
        text = self._prepare_text(text)

        response = self.client.embeddings.create(
            model=self.MODEL,
            input=text
        )

        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts efficiently using batched API calls.
        OpenAI allows up to 2048 inputs per request, but we batch
        at 100 to stay well within rate limits and handle errors cleanly.
        """
        if not texts:
            return []

        prepared = [self._prepare_text(t) for t in texts]
        all_embeddings = []

        for i in range(0, len(prepared), self.BATCH_SIZE):
            batch = prepared[i: i + self.BATCH_SIZE]
            batch_num = (i // self.BATCH_SIZE) + 1
            total_batches = (len(prepared) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

            print(f"  Embedding batch {batch_num}/{total_batches} "
                  f"({len(batch)} texts)...")

            response = self.client.embeddings.create(
                model=self.MODEL,
                input=batch
            )

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

            if i + self.BATCH_SIZE < len(prepared):
                time.sleep(0.1)

        return all_embeddings

    def _prepare_text(self, text: str) -> str:
        """
        Clean text before embedding.
        OpenAI's embedding model has a token limit — we truncate
        at 8000 characters as a safe proxy for staying under it.
        Empty strings cause API errors, so we substitute a placeholder.
        """
        text = text.strip()

        if not text:
            return "[empty]"

        if len(text) > 8000:
            text = text[:8000]

        return text