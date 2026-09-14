<!-- markdownlint-disable-file -->
# Task Review: Desjardins Bilingual Hosted Agents Workshop

## Review Metadata

* **Review date**: 2026-09-13
* **Implementation plan**: [.copilot-tracking/plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md](../../plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md)
* **Changes log**: [.copilot-tracking/changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md](../../changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md)
* **Research document**: [.copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md](../../research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md)
* **Planning log**: [.copilot-tracking/plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md](../../plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md)
* **Details file**: [.copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md](../../details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md)
* **Plan phases**: 9 (all marked `[x]` complete)

## Status

Phase 1 (Artifact Discovery): Complete.
Phase 2 (RPI Validation): Complete.
Phase 3 (Quality Validation): Complete.
Phase 4 (Review Completion): Complete.

## Per-Phase RPI Validation Results

| Phase | Status | Critical | Major | Minor | Validation File |
|---|---|---|---|---|---|
| 1: Repository and Bilingual Site Scaffold | Partial | 0 | 1 | 2 | [001](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan-001-validation.md) |
| 2: Synthetic Fixtures, JSON Schema, and Deterministic Calculator | Passed | 0 | 0 | 2 | [002](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan-002-validation.md) |
| 3: Approval Repository and State Machine | Partial | 0 | 3 | 1 | [003](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan-003-validation.md) |
| 4: Read-Only MCP Services | Passed | 0 | 0 | 4 | [004](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan-004-validation.md) |
| 5: Hosted LangGraph Quote-Preparation Agent (local, unhosted) | Passed | 0 | 0 | 2 | [005](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan-005-validation.md) |
| 6: Bilingual Lab Curriculum and Shared Deck | Partial | 0 | 1 | 1 | [006](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan-006-validation.md) |
| 7: Evaluation Suite | Partial | 0 | 1 | 1 | [007](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan-007-validation.md) |
| 8: Infrastructure Scaffolding (author only, gated) | Passed | 0 | 0 | 2 | [008](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan-008-validation.md) |
| 9: Final Validation | Passed | 0 | 0 | 2 | [009](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan-009-validation.md) |

## Implementation Quality Validation

Performed directly (the `Implementation Validator` subagent reported no file tools available in its session on two independent attempts — logged as a process finding). Full report: [implementation-quality](rpi/2026-09-13/desjardins-bilingual-hosted-agents-workshop-implementation-quality.md).

* Security (SQL injection in `approval_repository.py`, path traversal in the MCP data loaders, hard-coded secrets in Bicep/`azure.yaml`): **0 findings** — verified clean (parameterized queries throughout; fixed, non-user-controlled file paths; only env-var placeholders in `azure.yaml`).
* Code quality/consistency: 1 Minor (no `pyrightconfig`/`pyproject.toml` suppressing expected editor-only "unable to import" false positives from the intentional per-directory `sys.path` pattern).
* Markdown/writing style: 0 findings (spot-check of `docs/labs/lab-00-setup.md` consistent with instructions; corroborates Phase 6 RPI spot-check).
* Process: 1 Minor (`Implementation Validator` subagent unusable in this environment — no file tools registered).

## Validation Commands

| Command | Result |
|---|---|
| `pytest apps/workshop mcp src/quote-preparation-agent eval -q` (`.venv` Python) | **49 passed**, 1 non-blocking deprecation warning, 1.18s — independently re-run for this review, matches changes log and Phase 9 RPI validation exactly |
| `python eval/evaluation_gate.py` | 12/12 passed, `bilingual_parity=PASS`, exit 0 — confirmed by Phase 7 and Phase 9 RPI validators |
| `az bicep build --file infra/main.bicep` | Compiles with 2 non-blocking `BCP318` null-check warnings (`acr.properties.loginServer`), no errors — confirmed by Phase 8 and Phase 9 RPI validators |
| `get_errors` across `apps/workshop`, `mcp`, `src/quote-preparation-agent`, `eval`, `infra` | Only expected editor-only Pylance false positives (cross-directory imports via `sys.path`, pytest fixture-shadowing idiom, `global` usage, LangGraph node signature params) plus the 2 known Bicep `BCP318` warnings — no undisclosed real errors |

## Severity Summary

| Severity | Count |
|---|---|
| Critical | 0 |
| Major | 6 |
| Minor | 19 |

Major findings breakdown (all details in the linked per-phase files):

1. **Phase 1** — Just the Docs theme license-check (Risk Register RR12) never performed or recorded.
2. **Phase 3** — `ApprovalRepository` implements only 4 of 6 Mermaid-diagram states (`INCOMPLETE`/`UNSUPPORTED` missing as repository states/transitions/tests).
3. **Phase 3** — No `commandId`/`recordVersion`-based idempotency or stale-conflict test, as the details file specifies.
4. **Phase 3** — No test demonstrates rejection of a forged/spoofed reviewer identity (research V11); only self-approval is covered.
5. **Phase 6** — Lab topics (01-08) diverge entirely from the plan/details file's specified topics (architecture, mcp-servers, deploy-agent, invoke-agent, CI/CD, troubleshooting/RBAC, production-readiness content is completely absent), with no discrepancy-log or changes-log record explaining the divergence; the PptxGenJS license check (Step 6.3) was also never documented as done or skipped.
6. **Phase 7** — Missing "injection attempt" fault case and injection-resistance/case-isolation deterministic checks required by the details file and research document, undisclosed despite Steps 7.1/7.2 being marked complete.

## Missing Work and Deviations

* All 6 Major findings above represent gaps between what the plan/details/research documents specify and what was actually built or tested, none of which are disclosed in the changes log's "Additional or Deviating Changes" section — this is itself a pattern worth flagging: several phases mark checkboxes complete without the changes log surfacing partial-completion caveats that the underlying code reveals on inspection.
* No critical findings: nothing was found broken, insecure, or falsely claimed as tested when it silently wasn't run at all. All Major items are scope/coverage gaps against the plan's own stated acceptance criteria, not runtime defects.
* Non-blocking, already-disclosed items (not counted as new findings): markdownlint-cli2 sandbox restriction, PptxGenJS dependency not installable in this environment, runtime-notice wording vs. docs disclaimer wording, toolbox.py in-process vs. real-MCP-client design deferral (tracked as WI-10), and the two Bicep `BCP318` warnings.

## Follow-Up Recommendations

### Deferred From Scope (already tracked)

* Gates G1-G6 and Work Items WI-01 through WI-13 in the planning log remain open and are unaffected by this review.

### Discovered During Review (new)

* **F-01 (Major)**: Add `ApprovalRepository` support for `INCOMPLETE`/`UNSUPPORTED` states, transitions, and tests, or explicitly document in the changes log why the calculator-layer handling of these is sufficient and the repository intentionally omits them.
* **F-02 (Major)**: Add idempotency/stale-conflict tests keyed on `commandId`/`recordVersion` per the details file, or document why the existing state+revision WHERE-guard is an accepted substitute.
* **F-03 (Major)**: Add a test for forged/spoofed reviewer identity rejection (research V11), distinct from self-approval.
* **F-04 (Major)**: Reconcile lab curriculum topics (01-08) against the plan/details file's specified topics, or add a discrepancy-log entry explaining the intentional retheming toward codebase-aligned lab titles.
* **F-05 (Major)**: Perform and record the PptxGenJS license check (Step 6.3), or document why it's deferred alongside the already-disclosed install-failure note.
* **F-06 (Major)**: Add an "injection attempt" fault-case record to `eval/golden-dataset.jsonl` and a corresponding deterministic check, per the details file and research document.
* **F-07 (Minor)**: Add a `pyrightconfig.json` or `pyproject.toml` `[tool.pyright]`/`[tool.ruff]` section documenting the intentional per-directory `sys.path` pattern so editor false positives don't confuse future contributors.
* **F-08 (Minor)**: Reconcile the changes log's Added/Removed file accounting for stale `.gitkeep` files (Phase 1) and the undercounted "Files removed" total (Phase 9, off by one for `eval/tests/__init__.py`).
* **F-09 (Process)**: The `Implementation Validator` subagent is not currently usable in this environment (no file tools). Investigate its configuration before relying on it in future reviews.

## Overall Status

**⚠️ Needs Rework** — no critical findings and all 49 tests/eval-gate/Bicep-build checks independently reproduce cleanly, but 6 Major findings represent real, undisclosed gaps between the plan's/research's own acceptance criteria and what was built (Phases 1, 3, 6, 7). None of these block the workshop from being usable as a learning exercise today, but they should be resolved or explicitly accepted-as-deferred (with changes-log/discrepancy-log entries) before this is considered fully plan-conformant.
