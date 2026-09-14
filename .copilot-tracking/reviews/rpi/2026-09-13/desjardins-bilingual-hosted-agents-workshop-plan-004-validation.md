<!-- markdownlint-disable-file -->
# RPI Validation: Desjardins Bilingual Hosted Agents Workshop — Phase 4

**Phase Validated**: Implementation Phase 4: Read-Only MCP Services
**Plan**: .copilot-tracking/plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md
**Changes Log**: .copilot-tracking/changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md
**Research**: .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md
**Details**: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md
**Planning Log**: .copilot-tracking/plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md
**Validation Date**: 2026-09-13

## Scope

Phase 4 ("Read-Only MCP Services") comprises three checklist steps, all marked `[x]` in the plan:

* Step 4.1: Implement `application-server` (`get_application`) as a read-only FastMCP service.
* Step 4.2: Implement `rulebook-server` (`get_rulebook`) as a read-only FastMCP service.
* Step 4.3: Validate phase changes (run MCP unit/smoke tests locally; confirm no write tools; confirm unknown IDs rejected).

## Plan Item to Changes Log Comparison

| Plan/Details Item | Changes Log Evidence | Status |
|---|---|---|
| Step 4.1 — `application-server` exposing `get_application(fixtureId)` only | Changes log "Added" entry: `mcp/application-server/main.py, application_data_loader.py, requirements.txt, tests/test_application_server.py - Phase 4: read-only FastMCP service exposing get_application (known-fixture lookup, explicit not-found for unknown IDs).` | Matched |
| Step 4.2 — `rulebook-server` exposing `get_rulebook(rulebookId)` only | Changes log "Added" entry: `mcp/rulebook-server/main.py, rulebook_data_loader.py, requirements.txt, tests/test_rulebook_server.py - Phase 4: read-only FastMCP service exposing get_rulebook (pinned rate table lookup, explicit not-found for unknown IDs).` | Matched |
| Step 4.3 — run MCP unit/smoke tests locally | No phase-specific test count is itemized in the changes log for Phase 4 alone (only the Phase 9 combined sweep: "49 passed, 0 failed" across all phases). Independently re-run for this validation (see Test Execution below): 8/8 passed. | Matched (verified independently) |
| Removed: `mcp/application-server/.gitkeep`, `mcp/rulebook-server/.gitkeep` | Changes log "Removed" entry, Phase 4. | Matched |

## File Evidence Verification

All claimed files exist on disk and were read directly:

* [mcp/application-server/main.py](../../../../mcp/application-server/main.py) — exposes exactly one tool, `get_application(fixture_id)`, backed by an in-memory dict built once at import from `application_data_loader.load_applications()`. Returns `{"fixtureId": ..., "error": "fixture not found"}` for unknown IDs, never a fabricated record.
* [mcp/application-server/application_data_loader.py](../../../../mcp/application-server/application_data_loader.py) — loads every `*.json` file under `data/synthetic/fixtures/` once and narrows each to `{"fixtureId", "input"}` only, deliberately excluding `expectedCalculation`, `workflow`, and `nextCommand` test-scaffolding fields.
* [mcp/rulebook-server/main.py](../../../../mcp/rulebook-server/main.py) — exposes exactly one tool, `get_rulebook(rulebook_id)`, backed by the single pinned rulebook loaded from `data/synthetic/rulebook.json`. Returns `{"rulebookId": ..., "error": "rulebook not found"}` for any ID other than the pinned `RULEBOOK-SYN-ON`.
* [mcp/rulebook-server/rulebook_data_loader.py](../../../../mcp/rulebook-server/rulebook_data_loader.py) — reads `data/synthetic/rulebook.json` once; no fabrication path.
* [mcp/application-server/tests/test_application_server.py](../../../../mcp/application-server/tests/test_application_server.py) — 5 tests: known-fixture lookup, response-shape narrowing (`{"fixtureId","input"}` only), unknown-ID rejection, all-fixtures-resolvable loop, and `test_server_exposes_only_get_application` (asserts `mcp.list_tools()` returns exactly `["get_application"]`).
* [mcp/rulebook-server/tests/test_rulebook_server.py](../../../../mcp/rulebook-server/tests/test_rulebook_server.py) — 3 tests: known-ID exact-match, unknown-ID rejection (`"baseCents" not in result`), and `test_server_exposes_only_get_rulebook` (asserts exactly `["get_rulebook"]`).
* [data/synthetic/rulebook.json](../../../../data/synthetic/rulebook.json) (line 1-4) — confirms `id: "RULEBOOK-SYN-ON"`, `authority: "WORKSHOP_AUTHORS_ONLY"`, matching both servers' docstring claims.
* [data/synthetic/fixtures/case-syn-001.json](../../../../data/synthetic/fixtures/case-syn-001.json) (lines 1-40) — confirms the full fixture carries `expectedCalculation` and `workflow` (with an audit trail) that `application_data_loader.py` correctly strips before serving.

No files were found modified or created for Phase 4 beyond what the changes log lists; no additional relevant files were found missing from the log.

## Research Cross-Check

Research document (.copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md, line 134): "Expose only get_application(fixtureId) and get_rulebook(rulebookId). No arbitrary SQL, URLs, paths, write tools, approval tools, or insurer integrations. Read-only annotations alone are not enforcement: use strict schemas, immutable fixtures, fixed allowlists, and authorization."

* **Only two tools total, one per server** — verified by `test_server_exposes_only_get_application` and `test_server_exposes_only_get_rulebook` (both assert `list_tools()` returns a single-element list). Confirmed by direct code read: each `main.py` registers exactly one `@mcp.tool()` function.
* **No arbitrary SQL/URL/path access** — both loaders resolve fixed, hard-coded repository-relative paths (`data/synthetic/fixtures/`, `data/synthetic/rulebook.json`); the caller-supplied `fixture_id`/`rulebook_id` is used only as a dictionary key or equality check, never as a path or query fragment. No path traversal or injection surface exists.
* **Fixed allowlists / immutable fixtures** — both servers build their in-memory dataset once at import time from on-disk fixtures; nothing is written back, and unknown IDs are explicitly rejected rather than silently defaulted.
* **No write, approval, or insurer-integration tools** — confirmed; the `ApprovalRepository` (Phase 3, `apps/workshop/approval_repository.py`) is the only write-capable component in the project and is never imported by either MCP server (each server's docstring explicitly states this and the imports confirm it).

Both servers therefore comply with the research's read-only MCP constraint as implemented in code (not merely by tool annotation).

## Planning Log Cross-Check (DD-*/DR-*)

Reviewed all Discrepancy Log entries in .copilot-tracking/plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md:

* DR-01 (gate-numbering mismatch), DR-02 (PDF timing conflicts), DR-03 (unresolved LIDIA/PDM acronyms) — none reference Phase 4, the MCP servers, or read-only tool exposure. Not applicable.
* DD-01 (nine vs. ten labs) — applies to Phase 6 (bilingual lab curriculum), not Phase 4. Not applicable.

**No planning-log discrepancy items are relevant to Phase 4.** This is itself worth noting: the changes log's own "Additional or Deviating Changes" section documents two Phase-4-specific deviations (unique data-loader module names to avoid a `sys.modules` collision, and no Dockerfile in this phase) that were never promoted into the Planning Log's Discrepancy Log, even though the Planning Log is the designated location for tracking deviations. This is a documentation-process gap, not a functional one (see Minor-3 below).

## Test Execution

Re-ran the Phase 4 test suites independently using the workspace virtual environment, per the plan's Step 4.3 validation command (`pytest mcp/application-server/tests mcp/rulebook-server/tests`):

```text
python -m pytest mcp/application-server/tests -q          -> 5 passed in 0.61s
python -m pytest mcp/rulebook-server/tests -q              -> 3 passed in 0.55s
python -m pytest mcp -q                                    -> 8 passed in 0.58s
```

All 8 Phase 4 tests pass, matching the changes log's claim that Phase 4 tests are part of the Phase 9 combined "49 passed, 0 failed" sweep.

**Environment note (not a code defect):** invoking the combined `mcp/application-server/tests mcp/rulebook-server/tests` target with pytest's `-v` (verbose) flag intermittently raised a `KeyboardInterrupt` deep inside `colorama`'s Windows console writer during this validation session, after all tests had already reported `PASSED`. This reproduced across three attempts with `-v` and did not reproduce at all across three attempts with `-q`. This is a terminal/colorama interaction specific to this sandboxed environment, unrelated to the Phase 4 implementation — the same `-q` invocation the changes log implies for the Phase 9 "49 passed" sweep runs cleanly. Recorded here only so a future validator does not mistake it for a hang in the MCP server code itself.

## Findings

### Critical

None.

### Major

None. All Phase 4 success criteria from the details file are met:

* `get_application` returns fixture data for known IDs and a clear rejection for unknown IDs; no additional tools registered.
* `get_rulebook` returns the pinned rulebook for the known ID and a clear rejection for any other ID; no additional tools registered.
* No write, SQL, URL, or path-based tool is exposed by either server.

### Minor

* **Minor-1 — Undocumented file-naming deviation from the details spec.** The details file (.copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md, Step 4.1 "Files:" and Step 4.2 "Files:") specifies `mcp/application-server/server.py` and `mcp/rulebook-server/server.py` as the entry-point filenames. The actual implementation uses `main.py` for both (confirmed by directory listing and changes log). The changes log's "Additional or Deviating Changes" section for Phase 4 documents the unique data-loader module names (`application_data_loader.py` / `rulebook_data_loader.py`) but does not mention or justify the `server.py` → `main.py` rename. Functionally harmless (the plan file itself never names `server.py`), but it is an undisclosed deviation from the authoritative details spec.
* **Minor-2 — `get_application` response shape narrower than the details file's literal success-criteria wording.** Details file Step 4.1 success criteria states: "`get_application` returns the exact fixture content for a known fixtureId." The implementation instead returns only `{"fixtureId", "input"}`, deliberately excluding `expectedCalculation`/`workflow`/`nextCommand` — which is the *correct* behavior per the research document's tighter constraint (research line 134, "No arbitrary SQL, URLs, paths, write tools... use strict schemas, immutable fixtures, fixed allowlists") and per the code's own docstring ("Never returns expectedCalculation, workflow, or nextCommand test scaffolding"). The implementation is right and the research is authoritative over the details file per the plan's Context Summary, but the changes log never reconciles this literal wording gap against the details file, so a future reader comparing details-to-code in isolation could flag it as a false regression.
* **Minor-3 — Phase-4 deviations not promoted to the Planning Log.** The changes log's Phase 4 entry under "Additional or Deviating Changes" records two real deviations (data-loader naming to avoid a `sys.modules` collision; no Dockerfile in this phase, deferred to Phase 8) that do not appear anywhere in the Planning Log's Discrepancy Log (DD-*/DR-*), even though that log is the designated location per the plan's own "Planning Log" section pointer. Process/documentation gap only.
* **Minor-4 — The "deferred to Phase 8" Dockerfile claim was not fulfilled.** The Phase 4 changes log states no Dockerfile was added for either MCP server, "deferred to Phase 8 (infrastructure scaffolding)." A workspace-wide search for `Dockerfile*` found none, and `infra/modules/mcp-container-apps.bicep` documents that images are "intended to be built and pushed via `az acr build`" against `applicationImage`/`rulebookImage` parameters that currently default to a public placeholder image (`mcr.microsoft.com/k8se/quickstart:latest`), not a project-built image. Phase 8 itself is out of scope for this Phase 4 validation, but the forward reference made in the Phase 4 log did not come true, and Phase 8's own changes-log section does not flag this as a residual gap. Recommend cross-referencing this note when Phase 8 is separately validated.

## Coverage Assessment

Phase 4's two required deliverables (read-only `application-server` and `rulebook-server`) are both fully implemented, correctly scoped to their single allow-listed tool each, reject unknown IDs explicitly, expose no write/SQL/URL/path tools, and are covered by 8 passing unit tests that were independently re-executed during this validation. Coverage of the plan's Step 4.1–4.3 checklist items is complete. The only gaps found are documentation/traceability gaps (naming deviation not disclosed, deviations not promoted to the Planning Log, and a broken forward-reference to Phase 8) rather than functional or test gaps.

## Clarifying Questions

None required to complete this validation. Optional follow-up for the plan owner: confirm whether the `server.py` → `main.py` rename (Minor-1) should be back-filled into the details file for consistency, and whether Minor-4's Dockerfile/ACR-build gap should be added to the Planning Log's Suggested Follow-On Work list (it is not currently tracked as WI-* anywhere).
