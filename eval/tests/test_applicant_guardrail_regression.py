"""Applicant-guardrail regression for the reviewer-app case-store changes.

The reviewer surface exists precisely to show the calculated premium. The
applicant surface must never show it. Phase 1 persisted the calculation at
submission time and moved the agent onto a pluggable `CaseStore`, so the risk
this suite guards against is that a new backend -- or the factory that selects
one -- perturbs the applicant-facing output that `_STATUS_TEMPLATES` and
`_bounded_message` in `src/quote-preparation-agent/graph.py` are supposed to
hold fixed.

Three assertions, in increasing strictness:

* every `check_type: "agent"` golden-dataset record produces a byte-identical
  `applicant_message` under `ApprovalRepository`, `SqliteCaseStore`, and the
  store returned by `build_case_store()`;
* that output hashes to a pinned digest, so a template edit cannot pass
  unnoticed just because all three backends drifted together;
* no applicant message contains the premium that the store now persists, and
  `check_no_invented_amount` still passes for every one of those records.

`eval/deterministic-tests/checks.py` is imported, never modified: the guardrail
itself is the thing under test.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "eval"

for _dir in (
    EVAL_DIR / "deterministic-tests",
    REPO_ROOT / "apps" / "workshop",
    REPO_ROOT / "src" / "quote-preparation-agent",
):
    _path = str(_dir)
    if _path not in sys.path:
        sys.path.insert(0, _path)

import checks  # noqa: E402
from approval_repository import ApprovalRepository  # noqa: E402
from case_store import CaseStore, build_case_store  # noqa: E402
from sqlite_case_store import SqliteCaseStore  # noqa: E402

import main as agent_main  # noqa: E402

# `endpoint=""` pins the factory to SQLite even when COSMOS_ENDPOINT is set in
# the ambient environment, so this suite never reaches the network.
CASE_STORE_FACTORIES: dict[str, Callable[[], CaseStore]] = {
    "ApprovalRepository": lambda: ApprovalRepository(":memory:"),
    "SqliteCaseStore": lambda: SqliteCaseStore(":memory:"),
    "build_case_store": lambda: build_case_store(db_path=":memory:", endpoint=""),
}

# sha256 of the canonical form produced by `_applicant_message_digest` below.
# Regenerate only alongside a deliberate, reviewed change to the applicant-facing
# templates in src/quote-preparation-agent/graph.py.
PINNED_APPLICANT_MESSAGE_DIGEST = "0dddb4ef78d98e594b38a3f7421b32e310f6b7090977dbd345c81992bf6f4d40"


def _agent_records() -> list[dict[str, Any]]:
    records = [record for record in checks.load_golden_dataset() if record["check_type"] == "agent"]
    assert records, "golden dataset carries no check_type='agent' records to guard"
    return records


def _run_agent_record(record: dict[str, Any], store: CaseStore) -> dict[str, Any]:
    """Mirror `checks.run_agent_record` but against a caller-supplied store."""
    model = None
    injected_instruction = record.get("injected_instruction")
    if injected_instruction is not None:
        injected_text = injected_instruction.get("en-CA", "")
        model = lambda _prompt, _text=injected_text: _text  # noqa: E731
    return agent_main.run_case(record["case_id"], repository=store, model=model)


def _run_all(factory: Callable[[], CaseStore]) -> list[tuple[str, dict[str, Any]]]:
    """Run every agent record on a fresh store and return (record id, final state)."""
    outcomes: list[tuple[str, dict[str, Any]]] = []
    for record in _agent_records():
        store = factory()
        try:
            outcomes.append((record["id"], _run_agent_record(record, store)))
        finally:
            close = getattr(store, "close", None)
            if close is not None:
                close()
    return outcomes


def _applicant_message_digest(outcomes: list[tuple[str, dict[str, Any]]]) -> str:
    """Canonical form: dataset-ordered `{"id", "applicant_message"}` objects,
    compact-separator JSON with sorted keys and unescaped non-ASCII."""
    payload = [
        {"id": record_id, "applicant_message": state["applicant_message"]}
        for record_id, state in outcomes
    ]
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def test_applicant_messages_are_identical_across_every_case_store_backend():
    digests = {
        name: _applicant_message_digest(_run_all(factory))
        for name, factory in CASE_STORE_FACTORIES.items()
    }

    assert len(set(digests.values())) == 1, f"applicant output diverged by backend: {digests}"


def test_applicant_message_digest_matches_the_pinned_value():
    digest = _applicant_message_digest(_run_all(CASE_STORE_FACTORIES["ApprovalRepository"]))

    assert digest == PINNED_APPLICANT_MESSAGE_DIGEST


def test_applicant_messages_never_carry_the_persisted_premium():
    outcomes = _run_all(CASE_STORE_FACTORIES["SqliteCaseStore"])
    priced = 0

    for record_id, state in outcomes:
        amount_cents = (state.get("calculation") or {}).get("amountCents")
        if amount_cents is None:
            continue
        priced += 1
        forbidden = {
            str(amount_cents),
            f"{amount_cents // 100}",
            f"{amount_cents / 100:.2f}",
            f"{amount_cents / 100:,.2f}",
        }
        for locale, text in state["applicant_message"].items():
            leaked = sorted(token for token in forbidden if token in text)
            assert not leaked, f"{record_id} leaked {leaked} into the {locale} applicant message"

    assert priced, "no agent record produced a premium, so this check proved nothing"


def test_no_invented_amount_still_passes_for_every_agent_record():
    verdicts = 0

    for record in _agent_records():
        actual = {"final_state": _run_agent_record(record, ApprovalRepository(":memory:"))}

        result = checks.check_no_invented_amount(record, actual)

        # None means the record produced no calculation at all (e.g. an invalid
        # case reference), which the guardrail treats as not applicable.
        if result is None:
            continue
        verdicts += 1
        assert result.passed, f"{record['id']}: {result.message}"

    assert verdicts, "no agent record reached the no_invented_amount guardrail"
