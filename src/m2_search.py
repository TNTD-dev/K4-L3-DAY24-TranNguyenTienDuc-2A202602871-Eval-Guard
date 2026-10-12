"""Module 2: Hybrid Search (BM25 + Dense Retrieval)."""
from __future__ import annotations

from dataclasses import dataclass
import math
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BM25_TOP_K, DENSE_TOP_K, HYBRID_TOP_K, OPENAI_API_KEY


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict[str, Any]


def tokenize(text: str) -> list[str]:
    """Simple alphanumeric tokenizer for Vietnamese/English."""
    return re.findall(r"\w+", text.lower())


class HybridSearch:
    def __init__(self):
        self.chunks: list[dict] = []
        self.bm25 = None
        self.embeddings: list[list[float]] = []
        self._openai_client = None

    def _get_client(self):
        if self._openai_client is None and OPENAI_API_KEY:
            from openai import OpenAI
            self._openai_client = OpenAI()
        return self._openai_client

    def _embed(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        if not client or not texts:
            return [[0.0] * 128 for _ in texts]
        # Batch in chunks of 50 to avoid payload limit
        all_embeddings = []
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = [t[:8000] for t in texts[i:i + batch_size]]
            resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )
            all_embeddings.extend([d.embedding for d in resp.data])
        return all_embeddings

    def index(self, chunks: list[dict]) -> None:
        """Index chunks using BM25 and Dense embeddings."""
        self.chunks = chunks
        if not chunks:
            return

        # 1. BM25 indexing
        from rank_bm25 import BM25Okapi
        corpus = [tokenize(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(corpus)

        # 2. Dense embeddings
        texts = [c["text"] for c in chunks]
        self.embeddings = self._embed(texts)

        # 3. Optionally index into Qdrant if running
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            from config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME

            qclient = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=3.0)
            if self.embeddings and len(self.embeddings[0]) > 0:
                dim = len(self.embeddings[0])
                qclient.recreate_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )
                points = [
                    PointStruct(
                        id=idx,
                        vector=emb,
                        payload={"text": c["text"], "metadata": c["metadata"]},
                    )
                    for idx, (c, emb) in enumerate(zip(chunks, self.embeddings))
                ]
                qclient.upsert(collection_name=COLLECTION_NAME, points=points)
        except Exception:
            # In-memory fallback if Qdrant container is not reachable
            pass

    def search(self, question: str, top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
        """Hybrid search combining BM25 and vector similarity."""
        if not self.chunks:
            return []

        q_tokens = tokenize(question)
        n = len(self.chunks)

        # BM25 scores
        bm25_scores = [0.0] * n
        if self.bm25 and q_tokens:
            bm25_raw = self.bm25.get_scores(q_tokens)
            max_bm25 = max(bm25_raw) if len(bm25_raw) > 0 and max(bm25_raw) > 0 else 1.0
            bm25_scores = [s / max_bm25 for s in bm25_raw]

        # Dense cosine similarity scores
        dense_scores = [0.0] * n
        if self.embeddings:
            q_emb_list = self._embed([question])
            if q_emb_list:
                q_emb = q_emb_list[0]
                q_norm = math.sqrt(sum(x * x for x in q_emb)) or 1.0
                for i, emb in enumerate(self.embeddings):
                    dot = sum(a * b for a, b in zip(q_emb, emb))
                    norm = math.sqrt(sum(x * x for x in emb)) or 1.0
                    dense_scores[i] = max(0.0, dot / (q_norm * norm))

        # Combine with weights (0.4 BM25 + 0.6 Dense)
        combined = []
        for i in range(n):
            score = 0.4 * bm25_scores[i] + 0.6 * dense_scores[i]
            combined.append((score, i))

        combined.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, idx in combined[:top_k]:
            c = self.chunks[idx]
            results.append(SearchResult(
                text=c["text"],
                score=float(score),
                metadata=c["metadata"],
            ))
        return results
