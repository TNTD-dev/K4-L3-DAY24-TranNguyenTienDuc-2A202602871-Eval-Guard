"""Module 3: Cross-Encoder Reranking."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RerankResult:
    text: str
    score: float = 0.0
    metadata: dict[str, Any] = None


class CrossEncoderReranker:
    def __init__(self):
        self.ranker = None
        try:
            from flashrank import Ranker
            # Uses fast local onnx model
            self.ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir="/tmp/flashrank")
        except Exception:
            self.ranker = None

    def rerank(self, question: str, docs: list[dict], top_k: int = 3) -> list[RerankResult]:
        """Rerank candidate documents given a query.
        
        Args:
            question: query text
            docs: list of dicts with {"text": str, "score": float, "metadata": dict}
            top_k: number of reranked documents to return
            
        Returns:
            list of objects with .text attribute
        """
        if not docs:
            return []

        if self.ranker:
            try:
                from flashrank import RerankRequest
                passages = [{"id": i, "text": d["text"], "meta": d.get("metadata", {})} for i, d in enumerate(docs)]
                req = RerankRequest(query=question, passages=passages)
                ranked = self.ranker.rerank(req)
                return [
                    RerankResult(
                        text=r["text"],
                        score=float(r.get("score", 0.0)),
                        metadata=r.get("meta", {}),
                    )
                    for r in ranked[:top_k]
                ]
            except Exception:
                pass

        # Fallback: rank by original score
        sorted_docs = sorted(docs, key=lambda x: x.get("score", 0.0), reverse=True)
        return [
            RerankResult(
                text=d["text"],
                score=float(d.get("score", 0.0)),
                metadata=d.get("metadata", {}),
            )
            for d in sorted_docs[:top_k]
        ]
