"""Run the RAG evaluation pipeline and print results (Task 6).

Usage:
    python scripts/run_eval.py
    python scripts/run_eval.py --k 15 --rerank
    python scripts/run_eval.py --k 5 --sport running
    python scripts/run_eval.py --dataset tests/eval_dataset.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from pathlib import Path


def _load_dataset(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Eval dataset not found: {path}\n"
            "Run: python scripts/generate_eval_dataset.py first."
        )
    return json.loads(p.read_text())


def _print_table(rows: list[tuple]) -> None:
    if not rows:
        return
    col_widths = [max(len(str(c)) for c in col) for col in zip(*rows)]
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    header, *body = rows
    print(fmt.format(*header))
    print("  ".join("-" * w for w in col_widths))
    for row in body:
        print(fmt.format(*row))


async def _run_faithfulness(dataset: list[dict], store, k: int, use_rerank: bool) -> dict:
    from app.services import rag_engine
    from app.services.evaluator import evaluate_faithfulness

    rag_results = []
    for entry in dataset[:20]:  # cap at 20 for speed
        try:
            answer, hits = await rag_engine.ask(
                query=entry["query"],
                store=store,
                k=k,
                top_n=5,
                use_rerank=use_rerank,
            )
            rag_results.append({
                "question": entry["query"],
                "answer": answer,
                "contexts": [doc.page_content for doc, _ in hits],
            })
        except Exception:
            pass

    if not rag_results:
        return {"faithfulness": 0.0, "answer_relevance": 0.0}
    return await evaluate_faithfulness(rag_results)


def run_eval(
    dataset_path: str = "tests/eval_dataset.json",
    k: int = 5,
    use_rerank: bool = False,
    sport_filter: str | None = None,
) -> None:
    from app.services.embedder import get_vector_store
    from app.services.evaluator import evaluate_retrieval

    dataset = _load_dataset(dataset_path)
    print(f"\nLoaded {len(dataset)} eval entries from {dataset_path}")

    store = get_vector_store()

    # Overall retrieval metrics
    overall_filter = {"user_id": "eval_user"}
    if sport_filter:
        overall_filter["activity_type"] = sport_filter

    overall = evaluate_retrieval(store, dataset, k=k, filter_dict=overall_filter)

    print(f"\n{'='*50}")
    print(f"Overall  k={k}  rerank={use_rerank}")
    print(f"  Hit Rate@{k}: {overall['hit_rate']:.3f}  ({overall['hits']}/{overall['total']})")
    print(f"  MRR:         {overall['mrr']:.3f}")

    # Per-sport breakdown
    by_sport: dict[str, list[dict]] = defaultdict(list)
    for entry in dataset:
        sport = entry.get("activity_type") or entry.get("data_type") or "other"
        by_sport[sport].append(entry)

    if len(by_sport) > 1:
        print(f"\nPer-sport breakdown (k={k}):")
        rows = [("Sport", "Count", f"HitRate@{k}", "MRR")]
        for sport, entries in sorted(by_sport.items()):
            sport_filter_dict = {**overall_filter, "activity_type": sport} if sport not in ("sleep", "personal_record") else overall_filter
            m = evaluate_retrieval(store, entries, k=k, filter_dict=sport_filter_dict)
            rows.append((sport, str(m["total"]), f"{m['hit_rate']:.3f}", f"{m['mrr']:.3f}"))
        _print_table(rows)

    # Faithfulness (async)
    print("\nRunning faithfulness evaluation (first 20 queries)...")
    faith = asyncio.run(_run_faithfulness(dataset, store, k=k, use_rerank=use_rerank))
    print(f"  Faithfulness:     {faith['faithfulness']:.3f}")
    print(f"  Answer Relevance: {faith['answer_relevance']:.3f}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG evaluation")
    parser.add_argument("--dataset", default="tests/eval_dataset.json")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--sport", default=None)
    args = parser.parse_args()

    run_eval(
        dataset_path=args.dataset,
        k=args.k,
        use_rerank=args.rerank,
        sport_filter=args.sport,
    )
