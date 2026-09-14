<!-- markdownlint-disable-file -->
# RPI Validation: Desjardins Bilingual Hosted Agents Workshop — Phase 5

**Plan**: .copilot-tracking/plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md
**Phase validated**: Implementation Phase 5: Hosted LangGraph Quote-Preparation Agent (local, unhosted)
**Changes log**: .copilot-tracking/changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md
**Research document**: .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md
**Details file**: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md
**Planning log**: .copilot-tracking/plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md
**Validation date**: 2026-09-13

## Scope

Plan checkboxes for Phase 5 (all marked `[x]`):

* Step 5.1: Adapt the supervisor/specialist LangGraph topology for intake, reference lookup, and composition
* Step 5.2: Wire the agent to the Phase 4 MCP tools and the Phase 2/3 calculator and approval repository, with bounded applicant-facing output
* Step 5.3: Validate phase changes (local test harness, no Azure calls, no hosted deployment)

## Plan Item → Changes Log → File Evidence Comparison

| Plan item | Changes log evidence | File evidence | Status |
|---|---|---|---|
| Step 5.1: supervisor/specialist LangGraph topology (intake, reference lookup, composition) | Changes log Added: "src/quote-preparation-agent/state.py, toolbox.py, graph.py, main.py, __init__.py, requirements.txt, tests/test_graph.py, tests/test_toolbox.py - Phase 5: local (unhosted) LangGraph supervisor/specialist agent (intake -> reference lookup -> composition)..." | [src/quote-preparation-agent/graph.py](../../../../src/quote-preparation-agent/graph.py) defines `supervisor_node`, `decide_next_step`, `intake_node`, `reference_lookup_node`, `composition_node`, and wires them via `StateGraph` with conditional edges (lines 118-198 approx.); [src/quote-preparation-agent/state.py](../../../../src/quote-preparation-agent/state.py) defines `QuotePreparationState` with `STAGE_INTAKE`/`STAGE_REFERENCE_LOOKUP`/`STAGE_COMPOSITION` (lines 18-48) | Met |
| Step 5.1 success criterion: graph compiles/runs locally with no hosted Foundry call | Changes log Additional/Deviating Changes: "Phase 5's toolbox.py calls the Phase 4 MCP servers' tool functions in-process..." | [src/quote-preparation-agent/main.py](../../../../src/quote-preparation-agent/main.py) — module docstring (lines 1-9) states "No Azure/Foundry SDK calls and no hosted-agent deployment code exist in this module"; `graph.py` builds without a checkpointer (module docstring, lines 15-16) | Met |
| Step 5.1 success criterion: no node infers rates/discounts/coverage outside the calculator | (implied by Phase 2 calculator reuse) | `composition_node` (graph.py, lines ~200-235) calls only `toolbox.calculate_quote(...)`, which forwards to the Phase 2 calculator (toolbox.py lines 100-108); no other node touches amounts | Met |
| Step 5.2: wire to Phase 4 MCP tools + Phase 2/3 calculator/approval repository | Changes log Added entry (same line as above) | `reference_lookup_node` calls `toolbox.get_application`/`toolbox.get_rulebook` (graph.py lines ~178-196); `composition_node` calls `toolbox.create_draft`/`toolbox.submit_for_review` (graph.py lines ~236-247) | Met |
| Step 5.2: applicant output uses bounded templates only, never raw composer/reviewer fields | (implied) | `_STATUS_TEMPLATES` + `_bounded_message` (graph.py lines 65-99) build applicant text from fixed templates plus the rulebook's own `notice` field only; `tests/test_graph.py::_assert_message_is_bounded` (lines 30-33, 82-85) asserts absence of `baseCents`, `planAddOnCents`, `WORKSHOP_AUTHORS_ONLY`, `reviewerId`, `actorId`, `auditEvent`, and literal computed amounts in every applicant message | Met |
| Step 5.2: agent never transitions a case to APPROVED / never calls approve/reject/revise | Changes log docstring cross-reference (toolbox.py design-choice note) | `toolbox.py` exports only `create_draft`/`submit_for_review` from `ApprovalRepository`, never `approve`/`reject`/`revise`/`open_training_preview` (toolbox.py `__all__`, lines 118-127); `tests/test_toolbox.py::test_toolbox_never_wraps_approve_reject_or_revise` (lines 74-78) asserts `not hasattr(toolbox, forbidden)`; `tests/test_graph.py::_SpyRepository` (lines 43-56) raises `AssertionError` if agent code ever calls those methods | Met |
| Step 5.2 file: `tests/test_agent_local.py` per details file (Lines 263-282) | Changes log Additional/Deviating Changes: "Test file names (test_graph.py, test_toolbox.py) differ from the details file's suggested test_agent_local.py per this execution's explicit instructions." | Actual files are `tests/test_graph.py` and `tests/test_toolbox.py`, not `tests/test_agent_local.py` | Deviation — disclosed (see Minor-1) |
| Step 5.2 success criterion: passes for CASE-SYN-001 and one UNSUPPORTED fixture | (implied) | `test_graph.py::test_ready_case_matches_exact_expected_amount` uses CASE-SYN-001 (lines 66-76); `test_unsupported_case_never_invents_an_amount` uses CASE-SYN-003 (lines 79-88) | Met |
| Step 5.3: validate phase changes — run local agent tests, no Azure calls, no hosted deployment attempted | Changes log Release Summary: "Test results (final Phase 9 sweep): `pytest apps/workshop mcp src/quote-preparation-agent eval -q` → 49 passed, 0 failed." Also: "No deploy/provision/apply command was run" (Phase 8 note, applies repo-wide) | Re-executed independently in this validation: `pytest src/quote-preparation-agent/tests -q` → **11 passed, 0 failed** (see Test Execution below) | Met |

## Cross-Check Against Research Guidance (LangGraph state/toolbox/graph pattern)

Research document, Implementation Patterns (lines ~130-145) and Technical Scenarios Mermaid diagram (lines ~209-220):

* "Select one hosted LangGraph orchestrator containing logical intake/reference specialists and a tool-free composer" — Met. `graph.py` implements exactly three specialist nodes (`intake`, `reference_lookup`, `composition`) behind a `supervisor` routing node; `composition_node` calls no MCP tool, only the calculator and approval-repository draft/submit functions (graph.py lines 199-247).
* "Expose only get_application(fixtureId) and get_rulebook(rulebookId). No arbitrary SQL, URLs, paths, write tools, approval tools" — Met. `toolbox.py` exposes exactly `get_application`, `get_rulebook`, `calculate_quote`, `create_draft`, `submit_for_review`; `test_toolbox_never_wraps_approve_reject_or_revise` structurally enforces the write-tool exclusion.
* "Do not store shared approval in an applicant's hosted session or infer it from model text" — Met. `default_model`/injected `model` callable is used only for an `intake_note` acknowledgement string (graph.py lines 155-160); no code path derives `intake_valid`, `workflow_state`, or approval status from the model's return value — validity comes from `CASE_ID_PATTERN.match` (graph.py line 152) and repository state.
* "Applicant output uses bounded intake/status templates, never raw employee-facing composer output" — Met, per the bounded-message evidence above.
* Keep the framework (LangGraph), no migration performed — Met. `requirements.txt` pins `langgraph>=0.2,<0.3` / `langchain-core>=0.3,<0.4`, consistent with Risk Register RR6 mitigation cited in the details file (Step 5.1 discrepancy references).

One research-adjacent point the research does not explicitly cover: the research's Implementation Patterns section describes the intended runtime shape (a hosted LangGraph orchestrator calling MCP tools) without specifying in-process vs. networked binding for the *local, unhosted* phase — that binding choice is a plan/execution decision, not a research deviation. See Planning Log cross-check below for how it was actually decided and recorded.

## Planning Log Cross-Check (DD-*/DR-* and the MCP-client discrepancy)

* No DD-* or DR-* entry in the Discrepancy Log section is scoped to Phase 5 specifically (DD-01, DR-01, DR-02, DR-03 all concern Phase 1/6 lab-count and PDF-evidence conflicts, unrelated to Phase 5).
* The specific discrepancy the user asked about — **whether `toolbox.py` uses a real MCP client or an in-process call** — is not filed as a DD-/DR- entry, but it **is** documented in three places, consistently:
  1. Changes log, Additional or Deviating Changes: *"Phase 5's toolbox.py calls the Phase 4 MCP servers' tool functions in-process (loading main.py under a private module name) rather than over a real MCP client/streamable-http session, since this phase is explicitly forbidden from running any hosted/networked deployment. Swapping to a real client session is deferred until Gates G2/G3/G6 clear."*
  2. `toolbox.py` module docstring itself (lines 1-24) — a detailed "Design choice — in-process calls, not an MCP client session" rationale, matching the changes-log wording.
  3. Planning log, Suggested Follow-On Work, **WI-10**: *"Before any hosted deployment, decide whether src/quote-preparation-agent/toolbox.py should switch from in-process MCP tool calls to a real MCP client/streamable-http session against the deployed application-server and rulebook-server."* (Priority: Medium, sourced from "Phase 5 completion report, Executive Details and Suggested Additional Steps.")
* Conclusion: this is a **known, explicitly disclosed design deviation with a tracked follow-on item (WI-10)**, not an undocumented gap. It is consistent with the plan's own constraint that Phase 5 must not attempt any hosted/networked deployment (Gates G2/G3/G6 not cleared).

## Test Execution

Command run in this validation session:

```powershell
& "c:/src/GitHub/devopsabcs-engineering/foundry-hosted-agents-fsi/.venv/Scripts/python.exe" -m pytest src/quote-preparation-agent/tests -q -p "no:langsmith"
```

Result: **11 passed**, 1 warning (LangChain deprecation notice, non-blocking), 0 failed.

Note: the first invocation without `-p "no:langsmith"` hung/errored during plugin auto-discovery inside `langsmith`'s optional pytest plugin (`requests_toolbelt` import interaction with pytest's assertion rewriter); disabling that plugin let collection proceed normally. This is an environment/tooling quirk unrelated to Phase 5 code correctness — all 11 Phase 5 tests (4 in `test_graph.py`, 7 in `test_toolbox.py`) passed once collection succeeded.

This 11-test count is consistent with the changes log's Release Summary aggregate figure (49 passed across `apps/workshop mcp src/quote-preparation-agent eval`).

## Findings

### Critical

None.

### Major

None.

### Minor

* **Minor-1 — Test file naming deviates from the details file, but is disclosed.** The details file (Step 5.2, "Files") specifies `src/quote-preparation-agent/tests/test_agent_local.py`; the actual deliverable uses `tests/test_graph.py` and `tests/test_toolbox.py` instead. The changes log explicitly discloses this rename ("Test file names (test_graph.py, test_toolbox.py) differ from the details file's suggested test_agent_local.py per this execution's explicit instructions."). The plan's Step 5.3 validation command (`pytest src/quote-preparation-agent/tests/test_agent_local.py`) as literally written would fail with a collection error (file not found) if run verbatim; running `pytest src/quote-preparation-agent/tests` (as the Phase 9 sweep and this validation both did) succeeds. No functional gap — both required scenarios (CASE-SYN-001 ready case, CASE-SYN-003 unsupported case) are covered in `test_graph.py`.
* **Minor-2 — Loose dependency pins deferred to Gate G3, as planned.** `src/quote-preparation-agent/requirements.txt` pins `langgraph>=0.2,<0.3` and `langchain-core>=0.3,<0.4` (open ranges), which the changes log explicitly flags as intentional pending Gate G3's exact-version verification. This matches the plan/research's own stated gating and is not a defect, but is noted here since imprecise pins are a normal audit point for any phase claiming "done."

## Coverage Assessment

All three Phase 5 steps (5.1, 5.2, 5.3) have complete, verifiable evidence: the claimed files exist, contain the claimed structure (supervisor/specialist LangGraph topology, bounded applicant output, in-process-not-hosted tool binding), and the claimed tests exist and pass. The one known behavioral discrepancy called out for special attention in this validation request (in-process vs. real MCP client) is fully and consistently disclosed across the changes log, the source docstring, and the planning log's follow-on work list (WI-10). No plan checkbox in this phase lacks corresponding evidence.

**Phase 5 validation status: Passed** (0 Critical, 0 Major, 2 Minor — both pre-disclosed, non-blocking).

## Recommended Next Validations (not performed in this session)

* Validate Phase 4 (MCP application-server/rulebook-server) directly, since Phase 5's toolbox.py depends on those servers' exact tool signatures and error shapes.
* Validate Phase 9 (final integration/disclaimer sweep) to confirm the cross-phase 49-test aggregate and the applicant-notice wording follow-up item noted there.
* Once Gate G3 is cleared, re-validate `requirements.txt` pins for `langgraph`/`langchain-core` against the actual hosted Foundry runtime version, per WI-03/WI-10.

## Clarifying Questions

None — sufficient evidence was available in the plan, details file, changes log, planning log, and source tree to reach a definitive verdict for every Phase 5 checklist item.
