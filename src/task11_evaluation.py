"""Run the 20-case dense-only versus hybrid+RRF RAG evaluation."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.task5_semantic_search import semantic_search
from src.task9_retrieval_pipeline import SCORE_THRESHOLD, retrieve
from src.task10_generation import (
    LLM_MODEL,
    LLM_PROVIDER,
    SYSTEM_PROMPT,
    call_llm,
    format_context,
    reorder_for_llm,
)


ROOT = Path(__file__).resolve().parent.parent
EVALUATION_DIR = ROOT / "group_project" / "evaluation"
GOLDEN_PATH = EVALUATION_DIR / "golden_dataset.json"
RAW_RESULTS_PATH = EVALUATION_DIR / "evaluation_results.json"
REPORT_PATHS = [EVALUATION_DIR / "RESULT.md", ROOT / "reports" / "RESULT.md"]
TOP_K = int(os.getenv("EVALUATION_TOP_K", "5"))
GENERATION_ATTEMPTS = int(os.getenv("EVALUATION_GENERATION_ATTEMPTS", "4"))
GENERATION_DELAY = float(os.getenv("EVALUATION_GENERATION_DELAY_SECONDS", "5"))


def _load_json(path: Path, default):
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _generate(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return "Tôi không thể xác minh thông tin này từ nguồn hiện có."
    ordered = reorder_for_llm(chunks)
    message = (
        f"Context:\n{format_context(ordered)}\n\nQuestion: {question}\n\n"
        "Cite sources using [Source N] exactly as labeled above."
    )
    for attempt in range(GENERATION_ATTEMPTS):
        try:
            return call_llm(SYSTEM_PROMPT, message)
        except Exception:
            if attempt == GENERATION_ATTEMPTS - 1:
                raise
            time.sleep(GENERATION_DELAY * (2**attempt))
    raise RuntimeError("generation failed")


def collect_answers(golden: list[dict], existing: list[dict]) -> list[dict]:
    completed = {(row["config"], row["question"]) for row in existing}
    rows = list(existing)
    configs = (
        ("A", "dense-only"),
        ("B", "hybrid+RRF"),
    )
    for case_index, case in enumerate(golden, 1):
        for config, strategy in configs:
            key = (config, case["question"])
            if key in completed:
                continue
            started = time.perf_counter()
            if config == "A":
                chunks = semantic_search(case["question"], top_k=TOP_K)
            else:
                chunks = retrieve(
                    case["question"],
                    top_k=TOP_K,
                    score_threshold=SCORE_THRESHOLD,
                    use_reranking=True,
                )
            answer = _generate(case["question"], chunks)
            row = {
                "case": case_index,
                "config": config,
                "strategy": strategy,
                "question": case["question"],
                "reference": case["expected_answer"],
                "reference_context": case["expected_context"],
                "answer": answer,
                "contexts": [chunk["content"] for chunk in chunks],
                "source_ids": [chunk["id"] for chunk in chunks],
                "latency_seconds": round(time.perf_counter() - started, 3),
            }
            rows.append(row)
            _save_json(RAW_RESULTS_PATH, rows)
            print(f"Generated {case_index}/{len(golden)} config {config}", flush=True)
    return rows


def score_with_ragas(rows: list[dict]) -> list[dict]:
    import ragas
    from google import genai
    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import embedding_factory
    from ragas.llms import llm_factory
    from ragas.metrics import (
        Faithfulness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        ResponseRelevancy,
    )
    from ragas.run_config import RunConfig

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    client = genai.Client(api_key=api_key)
    run_config = RunConfig(timeout=180, max_retries=8, max_wait=60, max_workers=1)
    evaluator_llm = llm_factory(
        LLM_MODEL, provider="google", client=client, temperature=0
    )
    evaluator_embeddings = embedding_factory(
        "google",
        model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
        client=client,
        run_config=run_config,
    )
    metrics = [
        Faithfulness(llm=evaluator_llm),
        ResponseRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        LLMContextRecall(llm=evaluator_llm),
        LLMContextPrecisionWithReference(llm=evaluator_llm),
    ]
    samples = [
        {
            "user_input": row["question"],
            "retrieved_contexts": row["contexts"],
            "response": row["answer"],
            "reference": row["reference"],
            "reference_contexts": [row["reference_context"]],
        }
        for row in rows
    ]
    result = evaluate(
        EvaluationDataset.from_list(samples),
        metrics=metrics,
        run_config=run_config,
        raise_exceptions=False,
        show_progress=True,
        batch_size=1,
    )
    frame = result.to_pandas()
    aliases = {
        "faithfulness": "faithfulness",
        "answer_relevancy": "answer_relevance",
        "context_recall": "context_recall",
        "llm_context_precision_with_reference": "context_precision",
        "context_precision": "context_precision",
    }
    for row, (_, scored) in zip(rows, frame.iterrows()):
        row["scores"] = {
            target: float(scored[source])
            for source, target in aliases.items()
            if source in scored and not math.isnan(float(scored[source]))
        }
    print(f"Scored with Ragas {ragas.__version__}", flush=True)
    _save_json(RAW_RESULTS_PATH, rows)
    return rows


def _mean(rows: list[dict], metric: str) -> float:
    values = [row["scores"].get(metric) for row in rows]
    values = [value for value in values if value is not None]
    return statistics.fmean(values) if values else float("nan")


def _fmt(value: float) -> str:
    return "N/A" if math.isnan(value) else f"{value:.4f}"


def write_report(rows: list[dict], golden_size: int) -> None:
    import ragas

    grouped = {config: [row for row in rows if row["config"] == config] for config in "AB"}
    metrics = (
        ("Faithfulness", "faithfulness"),
        ("Answer relevance", "answer_relevance"),
        ("Context recall", "context_recall"),
        ("Context precision", "context_precision"),
    )
    means = {
        config: {metric: _mean(grouped[config], metric) for _, metric in metrics}
        for config in "AB"
    }
    averages = {
        config: statistics.fmean(means[config].values()) for config in "AB"
    }
    winner = "Config B — hybrid + RRF" if averages["B"] >= averages["A"] else "Config A — dense-only"
    latency = {
        config: statistics.fmean(row["latency_seconds"] for row in grouped[config])
        for config in "AB"
    }
    for row in rows:
        row["average_score"] = statistics.fmean(row.get("scores", {}).values()) if row.get("scores") else 0.0
    worst = sorted(rows, key=lambda row: row["average_score"])[:3]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        commit = "unknown"

    score_lines = []
    for label, metric in metrics:
        a, b = means["A"][metric], means["B"][metric]
        score_lines.append(f"| {label} | {_fmt(a)} | {_fmt(b)} | {_fmt(b-a)} |")
    score_lines.append(
        f"| **Average** | **{_fmt(averages['A'])}** | **{_fmt(averages['B'])}** | **{_fmt(averages['B']-averages['A'])}** |"
    )
    worst_lines = []
    for index, row in enumerate(worst, 1):
        scores = row.get("scores", {})
        failure = "retrieval" if means[row["config"]]["context_recall"] < 0.5 else "generation"
        worst_lines.append(
            f"| {index} | {row['question']} | {row['config']} | "
            f"{_fmt(scores.get('faithfulness', float('nan')))} | "
            f"{_fmt(scores.get('answer_relevance', float('nan')))} | "
            f"{_fmt(scores.get('context_recall', float('nan')))} | "
            f"{_fmt(scores.get('context_precision', float('nan')))} | {failure} | "
            "Lowest per-case average; inspect retrieved contexts and answer. |"
        )
    report = f"""# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | {date.today().isoformat()} |
| Framework and version | Ragas {ragas.__version__} |
| Evaluator model | {LLM_MODEL} |
| Generator model | {LLM_MODEL} |
| Embedding model | {os.getenv('EMBEDDING_MODEL', 'gemini-embedding-001')} |
| Corpus version/commit | {commit} |
| Golden dataset size | {golden_size} |
| `top_k` | {TOP_K} |
| Fallback threshold and calibration | {SCORE_THRESHOLD}; dense cosine threshold |

## Configurations

- **Config A — dense-only:** Gemini query embedding + Chroma cosine search.
- **Config B — hybrid + RRF:** dense and BM25 candidates fused once with RRF; PageIndex attempted below the dense threshold.

Both configurations used the same golden dataset, generator, evaluator, prompt and `top_k`; only retrieval strategy changed.

## Overall scores

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
{chr(10).join(score_lines)}

## A/B comparison

- Better configuration: {winner}.
- Evidence: average metric delta B−A is {_fmt(averages['B']-averages['A'])}.
- Latency/cost trade-off: mean latency A={latency['A']:.3f}s, B={latency['B']:.3f}s per case. Hybrid adds local BM25 and RRF work but uses the same number of generation calls.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
{chr(10).join(worst_lines)}

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Tune chunk size and overlap | Lowest cases show retrieval/context weaknesses | Improve recall without excessive context | Re-run the same 20 cases and compare recall/precision |
| 2 | Calibrate the dense fallback threshold | Current threshold is a fixed corpus-level starting value | Better separation of in-domain and out-of-domain queries | Test labeled in-domain/out-of-domain queries across thresholds |
| 3 | Strengthen citation validation | Generation is prompt-enforced but not post-validated | Reduce unsupported or mismatched citations | Add citation checks and compare faithfulness |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | ---: | ---: | --- |
| Not run | Current A/B evaluation | N/A | N/A | No bonus experiment was required for this run. |
"""
    for path in REPORT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--generation-only", action="store_true")
    args = parser.parse_args()
    golden = _load_json(GOLDEN_PATH, [])
    if args.limit is not None:
        golden = golden[: max(args.limit, 0)]
    if not golden:
        raise ValueError("Golden dataset is empty")
    existing = [] if args.fresh else _load_json(RAW_RESULTS_PATH, [])
    allowed_questions = {case["question"] for case in golden}
    existing = [row for row in existing if row["question"] in allowed_questions]
    rows = collect_answers(golden, existing)
    if args.generation_only:
        return
    rows = score_with_ragas(rows)
    write_report(rows, len(golden))
    print(f"Wrote {REPORT_PATHS[0]} and {REPORT_PATHS[1]}")


if __name__ == "__main__":
    main()
