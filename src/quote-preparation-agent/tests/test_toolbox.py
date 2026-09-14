"""Unit tests for the quote-preparation agent's tool wrappers.

Verifies get_application/get_rulebook return the same shapes the Phase 4
MCP servers' own tests expect, calculate_quote matches the Phase 2
calculator directly, and -- critically -- that this module never exposes a
wrapper for approve/reject/revise/open_training_preview: those transitions
may only be performed by a human reviewer, never by agent code. No
network, LLM, or hosted-agent access is used anywhere in this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(REPO_ROOT / "apps" / "workshop"))

import toolbox  # noqa: E402
from calculator import calculate_quote as _direct_calculate_quote  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "data" / "synthetic" / "fixtures"


def test_get_application_returns_known_fixture_input():
    result = toolbox.get_application("CASE-SYN-001")

    assert result == {
        "fixtureId": "CASE-SYN-001",
        "input": {
            "locale": "fr-CA",
            "jurisdiction": "ON",
            "vehicleClass": "COMPACT",
            "plan": "TRAINING_EXTENDED",
        },
    }


def test_get_application_rejects_unknown_fixture_id():
    result = toolbox.get_application("CASE-SYN-999")

    assert result["fixtureId"] == "CASE-SYN-999"
    assert "error" in result


def test_get_rulebook_returns_pinned_rulebook():
    result = toolbox.get_rulebook("RULEBOOK-SYN-ON")

    assert result["id"] == "RULEBOOK-SYN-ON"
    assert result["authority"] == "WORKSHOP_AUTHORS_ONLY"
    assert result["baseCents"] == {"COMPACT": 80000, "SEDAN": 90000}


def test_get_rulebook_rejects_unknown_rulebook_id():
    result = toolbox.get_rulebook("RULEBOOK-DOES-NOT-EXIST")

    assert "error" in result


def test_calculate_quote_matches_calculator_directly():
    application = toolbox.get_application("CASE-SYN-001")
    rulebook = toolbox.get_rulebook("RULEBOOK-SYN-ON")

    via_toolbox = toolbox.calculate_quote(application["input"], rulebook)
    direct = _direct_calculate_quote(application["input"], rulebook)

    assert via_toolbox == direct
    assert via_toolbox["amountCents"] == 100000


def test_toolbox_creates_draft_and_submits_for_review():
    repository = toolbox.ApprovalRepository()

    draft = toolbox.create_draft(repository, "CASE-SYN-001", "AGENT-INTAKE")
    assert draft.state == "DRAFT"

    submitted = toolbox.submit_for_review(repository, "CASE-SYN-001", "AGENT-INTAKE")
    assert submitted.state == "PENDING_REVIEW"


def test_toolbox_never_wraps_approve_reject_or_revise():
    # This is the structural guarantee behind "the agent must never call
    # approve/reject/revise": no such function exists to call.
    for forbidden in ("approve", "reject", "revise", "open_training_preview"):
        assert not hasattr(toolbox, forbidden), f"toolbox must never expose {forbidden!r}"
