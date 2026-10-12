"""Module 4: RAGAS Evaluation Adapter."""
from __future__ import annotations

from dataclasses import dataclass
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY


@dataclass
class RagasPerQuestionMetric:
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def evaluate_ragas(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
) -> dict:
    """Evaluate questions using RAGAS 4 core metrics.
    
    Returns:
        dict containing:
            "per_question": list of objects each having faithfulness, answer_relevancy,
                            context_precision, context_recall (floats in [0, 1])
            "metadata": {"evaluator_models": [model_id, ...]}
    """
    if len({len(questions), len(answers), len(contexts), len(ground_truths)}) != 1:
        raise ValueError("Questions, answers, contexts, ground_truths must have identical lengths.")

    evaluator_models = ["gpt-4o-mini", "text-embedding-3-small"]

    if not questions:
        return {"per_question": [], "metadata": {"evaluator_models": evaluator_models}}

    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from ragas.run_config import RunConfig

    eval_llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=OPENAI_API_KEY,
        request_timeout=120,
    )
    eval_embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=OPENAI_API_KEY,
        request_timeout=60,
    )

    data_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(data_dict)

    # Configure Vietnamese language prompt adaptation for answer_relevancy
    try:
        answer_relevancy.question_generation.language = "vietnamese"
    except Exception:
        pass

    results = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=eval_llm,
        embeddings=eval_embeddings,
        run_config=RunConfig(timeout=180, max_retries=2, max_workers=2),
        raise_exceptions=False,
    )

    df = results.to_pandas()
    per_question = []

    for _, row in df.iterrows():
        f = float(row.get("faithfulness", 0.0))
        ar = float(row.get("answer_relevancy", 0.0))
        cp = float(row.get("context_precision", 0.0))
        cr = float(row.get("context_recall", 0.0))

        # Clamp and clean NaN/inf
        def clean_val(v: float) -> float:
            if not math.isfinite(v) or math.isnan(v):
                return 0.0
            return max(0.0, min(1.0, v))

        per_question.append(RagasPerQuestionMetric(
            faithfulness=clean_val(f),
            answer_relevancy=clean_val(ar),
            context_precision=clean_val(cp),
            context_recall=clean_val(cr),
        ))

    return {
        "per_question": per_question,
        "metadata": {
            "evaluator_models": evaluator_models,
        },
    }
