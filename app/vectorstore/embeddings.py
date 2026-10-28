import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class EmbeddingGenerator:
    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    BATCH_SIZE = 100
    MAX_CHARS = 8000  # rough stand-in for the model's token limit

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def embed_text(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.MODEL, input=self._prepare_text(text))
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        prepared = [self._prepare_text(t) for t in texts]
        total_batches = (len(prepared) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        embeddings = []

        for i in range(0, len(prepared), self.BATCH_SIZE):
            batch = prepared[i:i + self.BATCH_SIZE]
            print(f"  Embedding batch {i // self.BATCH_SIZE + 1}/{total_batches} ({len(batch)} texts)...")

            response = self.client.embeddings.create(model=self.MODEL, input=batch)
            embeddings.extend(item.embedding for item in response.data)

            if i + self.BATCH_SIZE < len(prepared):
                time.sleep(0.1)

        return embeddings

    def _prepare_text(self, text: str) -> str:
        text = text.strip()
        # the API rejects empty input
        return text[:self.MAX_CHARS] if text else "[empty]"
