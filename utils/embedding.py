from __future__ import annotations

import numpy as np
from openai import AzureOpenAI
from config import PRODUCTS_ENDPOINT, PRODUCTS_OPENAI_KEY

API_VER = "2023-05-15"
EMBED_MODEL = "text-embedding-3-large"

_embed_client = AzureOpenAI(
    azure_endpoint=PRODUCTS_ENDPOINT,
    api_key=PRODUCTS_OPENAI_KEY,
    api_version=API_VER,
)


def embed_text(text: str) -> list[float]:
    """Return embedding vector for *text* using Azure OpenAI."""
    resp = _embed_client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    va = np.array(a, dtype="float32")
    vb = np.array(b, dtype="float32")
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
