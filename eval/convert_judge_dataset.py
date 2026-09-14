"""Convert `eval/judge-dataset.jsonl` into the Azure AI Evaluation SDK's
`{"data": [...]}` envelope, for a single requested locale.

Adapted from the sibling `foundry-hosted-agents` repository's
`eval/convert_for_ai_agent_evals.py`, but reading this repo's bilingual
`judge-dataset.jsonl` shape instead of `input.messages`: each input
record's `query`/`context` fields are themselves `{"en-CA": str, "fr-CA":
str}` locale maps, so the `--locale` selector picks which language's text
becomes the flat `query`/`context` string in the output envelope. Fails
closed (raises `ValueError`) if any record is missing the requested
locale's `query` or `context` text, rather than silently dropping the
record or falling back to another locale.

This converter is eval-metadata tooling only: it produces the input file
consumed by the (author-only, gated) `eval/run_judge_evaluation.py`
harness. It does not call any model, evaluator, or network endpoint
itself.

Usage:
    python eval/convert_judge_dataset.py <input.jsonl> <output.json> [--locale en-CA|fr-CA]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SUPPORTED_LOCALES = ("en-CA", "fr-CA")
DEFAULT_LOCALE = "en-CA"

DATASET_NAME = "quote-preparation-agent-judge-dataset"
EVALUATORS = ["builtin.coherence", "builtin.groundedness", "builtin.task_adherence"]


def load_records(input_path: Path) -> list[dict[str, Any]]:
    """Read one JSON object per line from `input_path`, skipping blank lines."""
    records: list[dict[str, Any]] = []
    for line in input_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def convert(records: list[dict[str, Any]], locale: str) -> dict[str, Any]:
    """Build the `{"name", "evaluators", "data": [...]}` envelope for `locale`.

    Raises `ValueError` (fail closed) if `locale` is unsupported, or if any
    record is missing the requested locale's `query` or `context` text.
    """
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(f"Unsupported locale {locale!r}; expected one of {SUPPORTED_LOCALES}")

    data = []
    for record in records:
        record_id = record.get("id")
        query = (record.get("query") or {}).get(locale)
        context = (record.get("context") or {}).get(locale)
        if not query or not context:
            raise ValueError(f"Record {record_id!r} is missing {locale!r} query/context text")
        data.append(
            {
                "id": record_id,
                "query": query,
                "context": context,
                "expected": record.get("expected"),
            }
        )

    return {"name": DATASET_NAME, "evaluators": EVALUATORS, "data": data}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to eval/judge-dataset.jsonl (or compatible file)")
    parser.add_argument("output", type=Path, help="Path to write the converted JSON envelope")
    parser.add_argument("--locale", choices=SUPPORTED_LOCALES, default=DEFAULT_LOCALE)
    args = parser.parse_args()

    records = load_records(args.input)
    envelope = convert(records, args.locale)
    args.output.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(envelope['data'])} records ({args.locale}) to {args.output}")


if __name__ == "__main__":
    main()
