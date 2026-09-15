"""Temporary Phase 2 evidence capture: applicant-facing messages only.

Drives `main.run_case` exactly as `tests/test_graph.py` does, against a real
`SqliteCaseStore`, and prints the applicant message for every synthetic case.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "quote-preparation-agent"))
sys.path.insert(0, str(REPO_ROOT / "apps" / "workshop"))

import main  # noqa: E402
from sqlite_case_store import SqliteCaseStore  # noqa: E402

CASE_IDS = ["CASE-SYN-001", "CASE-SYN-002", "CASE-SYN-003", "CASE-SYN-004", "CASE-SYN-005"]

captured = []
for case_id in CASE_IDS:
    store = SqliteCaseStore(":memory:")
    try:
        final_state = main.run_case(case_id, repository=store, model=lambda prompt: "stub")
        captured.append({
            "caseId": case_id,
            "workflowState": final_state.get("workflow_state"),
            "issueCode": final_state.get("issue_code"),
            "applicantMessage": final_state.get("applicant_message"),
        })
    except Exception as exc:  # noqa: BLE001
        captured.append({"caseId": case_id, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        store.close()

print(json.dumps(captured, ensure_ascii=False, indent=2, sort_keys=True))
