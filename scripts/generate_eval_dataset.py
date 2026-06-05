"""Generate a golden evaluation dataset from real Garmin sample data (Task 6).

Usage:
    python scripts/generate_eval_dataset.py --n 80
    python scripts/generate_eval_dataset.py --data-dir data/samples --output tests/eval_dataset.json

Steps:
  1. parse_garmin_zip() on a ZIP in data-dir (or the first .zip found)
  2. chunk_garmin_data(parsed, user_id="eval_user")
  3. For each sampled document, ask Gemini to generate a realistic query + expected answer
  4. Throttle: asyncio.sleep between batches to avoid rate limits
  5. Write JSON array to output path

Review tests/eval_dataset.json manually before committing — AI-generated
questions may not all be meaningful.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


def _find_zip(data_dir: str) -> Path:
    data_path = Path(data_dir)
    zips = sorted(data_path.glob("*.zip"))
    if not zips:
        raise FileNotFoundError(f"No .zip files found in {data_dir}")
    return zips[0]


async def generate_eval_dataset(
    data_dir: str = "data/samples",
    output_path: str = "tests/eval_dataset.json",
    n: int = 80,
    batch_size: int = 5,
    throttle_seconds: float = 1.5,
    seed: int = 42,
) -> None:
    from app.core.config import settings
    from app.services.chunker import chunk_garmin_data
    from app.services.parser import parse_garmin_zip

    zip_path = _find_zip(data_dir)
    print(f"Parsing {zip_path} ...")
    parsed = parse_garmin_zip(zip_path)
    docs = chunk_garmin_data(parsed, user_id="eval_user")
    print(f"Total documents: {len(docs)}")

    rng = random.Random(seed)
    sample = rng.sample(docs, min(n, len(docs)))

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=0.4,
        max_output_tokens=256,
    )

    gen_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are generating evaluation data for a fitness RAG system. "
            "Given a fitness data excerpt, produce ONE realistic user question that can be "
            "answered from this excerpt, and a concise expected answer. "
            "Output ONLY valid JSON: {\"query\": \"...\", \"expected_answer\": \"...\"}",
        ),
        ("human", "Excerpt:\n{text}"),
    ])

    dataset: list[dict] = []
    for i in range(0, len(sample), batch_size):
        batch = sample[i: i + batch_size]
        for doc in batch:
            try:
                resp = await (gen_prompt | llm).ainvoke({"text": doc.page_content})
                raw = resp.content.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                parsed_resp = json.loads(raw)
                entry = {
                    "query": parsed_resp.get("query", ""),
                    "expected_answer": parsed_resp.get("expected_answer", ""),
                    "expected_doc_ids": [str(doc.metadata.get("record_id"))],
                    "data_type": doc.metadata.get("data_type"),
                    "activity_type": doc.metadata.get("activity_type"),
                    "source_text": doc.page_content,
                }
                dataset.append(entry)
                print(f"  [{len(dataset)}/{n}] {entry['query'][:60]}")
            except Exception as exc:
                print(f"  [skip] {exc}")

        if i + batch_size < len(sample):
            await asyncio.sleep(throttle_seconds)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2))
    print(f"\nWrote {len(dataset)} entries to {output_path}")
    print("Review the file manually before committing.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate RAG evaluation dataset")
    parser.add_argument("--data-dir", default="data/samples")
    parser.add_argument("--output", default="tests/eval_dataset.json")
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    asyncio.run(generate_eval_dataset(
        data_dir=args.data_dir,
        output_path=args.output,
        n=args.n,
        seed=args.seed,
    ))
