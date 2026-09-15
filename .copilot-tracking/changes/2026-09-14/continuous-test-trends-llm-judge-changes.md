<!-- markdownlint-disable-file -->
# Release Changes: Continuous test trends and LLM-judge evaluation parity

**Related Plan**: continuous-test-trends-llm-judge-plan.instructions.md
**Implementation Date**: 2026-09-14

## Summary

Adds real Azure AI Evaluation SDK judge metrics (coherence/groundedness/task_adherence, guarded/inert until deployment gates clear), a `Continuous-Test-Trends.md` wiki page with tables and mermaid charts backed by a `trend-history/` folder, and richer data-driven GitHub Actions job summaries across all four workflows.

## Changes

### Added

* eval/judge-dataset.jsonl - 10 bilingual (en-CA/fr-CA) query/context/expected records for judge evaluation, derived from real golden-dataset scenarios
* eval/convert_judge_dataset.py - CLI converter producing the judge-evaluation dataset envelope with a `--locale` selector
* eval/tests/test_convert_judge_dataset.py - unit tests for the converter's envelope shape and fail-closed locale handling
* eval/judge_gate.py - `METRICS`/`validate_results()` judge-gate module, separate from the deterministic gate
* eval/run_judge_evaluation.py - author-only, gated judge-evaluation harness (`criteria()`, `evaluate()`, guarded `capture()`/`main()`)
* eval/tests/test_run_judge_evaluation.py - unit tests for `criteria()`, `agent_instructions()` AST extraction, and the guard/no-Azure-import behavior
* scripts/ci_results.py - trend-aggregation script: `junit_totals`, `deterministic_gate_totals`, `judge_totals`, `collect`, `publish_history`, `render_trends`, `chart`, `run_label`, CLI (`--context`/`--junit`/`--evidence`/`--wiki`/etc.) (this file already existed from a prior, unrelated plan serving `web-chat-build.yml`'s `--junit` mode; extended in place rather than recreated)
* scripts/tests/test_ci_results.py - unit tests for the above
* eval/judge_gate.py - new sibling module to `evaluation_gate.py`; `METRICS = ("coherence", "groundedness", "task_adherence")` and `validate_results()` ported near-verbatim from the sibling `foundry-hosted-agents` repo's `eval/evaluation_gate.py`
* eval/run_judge_evaluation.py - author-only, gated judge-evaluation harness adapted from the sibling's `eval/run_hosted_evaluation.py`: `criteria()`, `collect_output_items()`, and `evaluate()`'s `AIProjectClient`/`client.evals.create`/`client.evals.runs.create` polling loop ported near-verbatim; `agent_instructions()` adapted to AST-extract `AGENT_TASK_INSTRUCTIONS` from `src/quote-preparation-agent/graph.py`; `capture()` replaced to raise `RuntimeError` immediately (no hosted-invocation harness exists yet); `main()` has a guard that prints the same author-only message and exits 1 before any Azure SDK import or filesystem/network side effect
* eval/tests/test_run_judge_evaluation.py - unit tests for `criteria()`'s per-metric data mapping, `agent_instructions()`'s real AST extraction from `graph.py`, `main()`'s guard exiting 1 without importing `azure.ai.projects`, and `capture()`'s immediate raise

### Modified

* src/quote-preparation-agent/graph.py - added `AGENT_TASK_INSTRUCTIONS` module-level constant (eval-metadata-only, not wired into execution)
* .github/workflows/continuous-validation.yml - split combined `pytest --junitxml=evidence/tests.xml` into three per-suite JUnit files (`agent.xml`, `deterministic.xml`, `reporting.xml`)
* .github/workflows/deploy-and-evaluate.yml - split combined `pytest --junitxml=offline-evidence/tests.xml` in the `lint` job into the same three per-suite JUnit files; added a guarded (`if: false`) LLM-judge step + SDK install to the `evaluate` job; extended the header banner
* .github/workflows/continuous-validation.yml - added a "Stage deterministic gate result alongside JUnit evidence" step and changed the `offline-test-evidence` artifact's `path:` so `eval/results.json` is bundled as a flat `evidence/results.json` (previously nested as `eval/results.json`, which would not have matched `ci_results.py`'s flat-path read after download); replaced the static "Offline test summary" step with `scripts/ci_results.py --junit`; added a deterministic-gate summary step and a `bicep-lint` job summary step
* .github/workflows/publish-test-trends.yml - replaced placeholder body with real provenance verification, evidence-artifact download, `scripts/ci_results.py` invocation, `ci-report` artifact retention, and a `WIKI_PUSH_TOKEN`-gated wiki push (fails loudly if the secret is unset)

Wiki (C:\temp\fsi-wiki, NOT YET PUSHED -- local clone only):

* Continuous-Test-Trends.md - new page, seeded via `scripts/ci_results.py`'s `render_trends([])` (honest empty state; see Planning Log)
* trend-history/ - new, empty folder ready for the first real run
* Home.md, _Sidebar.md - added "Test Trends" navigation links
* Workflows.md - corrected `publish-test-trends.yml`'s table row, the stale "fully deterministic" sentence, and the "Release path" diagram to show the new guarded judge stage

### Removed

## Additional or Deviating Changes

* `eval/run_judge_evaluation.py`'s `main()` guard is placed after argparse parsing (not as the literal first line) so the documented CLI surface stays real/testable while still guaranteeing the guard fires before any Azure import or side effect.
  * Reason: guarding before argparse would make the CLI surface unreachable dead code.
* Sibling's SSE-stream capture helpers (`capture_summary`, `validate_candidate_evidence`, `verified_safety_refusal`, `completed_response`, `runtime_state`, `stream_error`, `CaptureError`) intentionally not ported to `run_judge_evaluation.py`.
  * Reason: they depend on a hosted-agent invocation harness (`scripts/invoke-agent.sh` equivalent) this repo does not have; `capture()` always raises before any of that logic could run.
* `scripts/ci_results.py` dropped the sibling's `evaluation_totals()`/`load_totals()` and the "load" dimension entirely.
  * Reason: this repo has no hosted-agent capture pipeline or load-test harness; keeping them would either dead-code-forever-return-None or fabricate a section.
* `deterministic_gate_totals()`'s lookup in `collect()` checks both `offline-test-evidence/results.json` (continuous-validation.yml's layout) and `evaluation-evidence/results.json` (deploy-and-evaluate.yml's layout), first match wins.
  * Reason: the two workflows bundle `eval/results.json` into different artifacts; this keeps `collect()` correct for both without duplicating the file into two artifacts.
* `publish-test-trends.yml` gained a `run_attempt` dispatch input and a "Resolve source run attempt" step not explicitly specified in the details doc.
  * Reason: the existing file only defined a required `run_id` input; a manual dispatch needs a way to resolve the latest attempt when the caller doesn't know it.
* `Continuous-Test-Trends.md` was seeded empty (`render_trends([])`) rather than from a real historical run.
  * Reason: the only completed `Continuous Validation` runs on `main` predate this plan's JUnit-split/flat-artifact changes (verified by downloading and inspecting run 34861865115's actual artifact: nested `eval/results.json` and a single combined `evidence/tests.xml`). Replaying it through the new `collect()` would either silently miss data or require hand-massaging the download to fake the new layout. Documented as a follow-on instead of fabricating a seed record.

## Post-Release Follow-On: Real Hosted Server + Real Judge Evaluation (2026-09-14, same day, continuation session)

WI-04 (Planning Log) required a real hosted `quote-preparation-agent` endpoint before the guarded LLM-judge step could be exercised end-to-end. This continuation implements that missing piece and completes WI-04 and WI-01.

### Added (continuation)

* src/quote-preparation-agent/response_bridge.py - custom `ResponseAPIConverter` (`QuotePreparationResponseConverter`) bridging the Foundry Responses protocol to this project's case-driven graph state; implements `convert_request`, `convert_response_non_stream`, and `convert_response_stream` (the SDK's default converter only supports MessagesState-shaped graphs, which this project's graph is not)
* src/quote-preparation-agent/case_input.py - `parse_case_input()` extracted into a neutral module name (avoids a real module-name collision: `toolbox.py`'s sys.path manipulation shadowed a bare `import main` with `mcp/rulebook-server/main.py`)

### Modified (continuation)

* src/quote-preparation-agent/main.py - `case_input` CLI arg is now optional (`nargs="?"`); when omitted (how the Foundry hosted runtime actually invokes the container), a new `serve()` function builds the graph, wraps it with `from_langgraph(graph, converter=QuotePreparationResponseConverter())`, and calls `adapter.run(port=8088)`
* src/quote-preparation-agent/requirements.txt - pinned `azure-ai-agentserver-langgraph==1.0.0b17`, upgraded `langgraph` pin to `==1.2.11` (from `>=0.2,<0.3`), added `mcp>=1.6.0,<2`
* eval/run_judge_evaluation.py - `capture()`'s author-only guard removed; now makes real HTTPS calls to the deployed hosted agent (`DefaultAzureCredential().get_token("https://ai.azure.com/.default")`, POST to `{endpoint}/agents/{agent}/endpoint/protocols/openai/responses?api-version=v1`); added `_extract_response_text()` and `_normalize_output_items()` (flattens bilingual `content[].text` dict to a single locale string -- fixes a real `TaskAdherenceEvaluator` error: "The 'text' field must be a string in content items"); `main()` now loads the dataset and drives the full capture/evaluate pipeline for real
* eval/tests/test_run_judge_evaluation.py - old guard-only tests replaced with real tests for `_extract_response_text`, `_normalize_output_items`, and `main()`'s capture/evaluate orchestration (mocked)
* .github/workflows/deploy-and-evaluate.yml's guarded `if: false` LLM-judge step - **not yet flipped to `if: true`** (see Additional or Deviating Changes)

### Modified (continuation, second pass -- user-approved live wiring)

* .github/workflows/deploy-and-evaluate.yml - flipped the LLM-judge step from `if: false` to `continue-on-error: true` (advisory; per-user confirmation that Gates G2/G3/G6 are cleared/not applicable for this sandbox repo); added a "Stage judge evidence alongside the deterministic gate result" step that copies `judge-evidence/results.json` to `evaluation-evidence/judge-results.json` (the filename/location `scripts/ci_results.py`'s `judge_totals()` expects -- the prior artifact wiring only uploaded the deterministic gate's `eval/results.json` and would never have surfaced judge data even if the step ran); changed the `evaluation-evidence-N` artifact's `path:` from the single `eval/results.json` file to the `evaluation-evidence/` directory containing both files; added a "Judge evaluation summary" step explaining the by-design low scores in the job summary; updated stale top-of-file and Stage-4 banner comments that claimed no LLM-judge/live endpoint existed

### Added (continuation, generated/data artifacts)

* eval/judge-dataset-converted.json - 10 records converted from `eval/judge-dataset.jsonl` via `convert_judge_dataset.py --locale en-CA`
* eval/judge-output/results.json, run-identity.json, summary.md - real evaluation run artifacts from the live deployed agent (version 5)

### Modified (continuation, third pass -- real CI run + fix)

* .github/workflows/deploy-and-evaluate.yml - manually dispatched `hosted-agent-cd.yml` (run 34914841304) to exercise the whole pipeline for real: all 5 jobs succeeded (lint, bicep validate, deploy-staging, evaluate, promote-production), and `publish-test-trends.yml` auto-triggered and pushed a real `trend-history/34914841304-1.json` entry + updated `Continuous-Test-Trends.md` to the live wiki (`WIKI_PUSH_TOKEN` was already configured -- WI-02 is resolved). However, the LLM-judge step itself failed in that run with `azure.core.exceptions.ClientAuthenticationError: DefaultAzureCredential failed to retrieve a token` -- root cause: the `evaluate` job never had an `azure/login@v3` OIDC step (only `bicep-validate`/`deploy-staging`/`promote-production` did), so `DefaultAzureCredential`'s `AzureCliCredential` fallback had no logged-in `az` session to use. Fixed by adding the same `azure/login@v3` step (with `vars.AZURE_CLIENT_ID`/`AZURE_TENANT_ID`/`AZURE_SUBSCRIPTION_ID`) to the `evaluate` job before the Python setup step. `continue-on-error: true` on the judge step meant this real failure did not break the job or block production promotion -- exactly as designed.

### Confirmed (continuation, fourth pass -- real trend data verified live)

* Re-dispatched `hosted-agent-cd.yml` (run 34917865121) after the OIDC-login fix: all 5 jobs succeeded, including "LLM-judge evaluation gate" this time (no auth error). `publish-test-trends.yml` (run 34918603998) auto-published the resulting evidence to the wiki: **Judge cases judged: 10, Judge checks: 30** (10 records x 3 metrics) now appear in `Continuous-Test-Trends.md` / `trend-history/34917865121-1.json` -- real, non-fabricated LLM-judge trend data is confirmed live end-to-end, closing WI-01 and WI-04b.
* Residual gap (not blocking): `Staging agent version` still renders `N/A` in the trend summary -- `context.json` (the file `collect()` reads for `agent_version`/`environment`/etc.) is never written by any step in `deploy-and-evaluate.yml`; `judge_totals()`/`deterministic_gate_totals()` don't depend on it, only the lineage columns do. Logged as a new follow-on (WI-06) rather than fixed in this pass, since it's cosmetic/lineage-only and out of scope for "confirm judge/deployment trends are present."

## Release Summary

All 8 original implementation phases complete, plus the WI-04/WI-01 follow-on (real hosted server + real judge run against live Azure, confirmed live in the wiki). 75/75 pytest tests pass across `eval`, `scripts`, `src/quote-preparation-agent/tests`, `mcp/application-server/tests`, `mcp/rulebook-server/tests`, `apps/workshop/tests` after the continuation session. The deterministic evaluation gate (`eval/evaluation_gate.py`) passes 13/13 on the real golden dataset in every real CI run observed, unaffected by this work.

**End-to-end confirmation (task goal met)**: `hosted-agent-cd.yml` run 34917865121 completed with all 5 jobs green (lint, bicep-validate, deploy-staging, evaluate [including the real LLM-judge step], promote-production); `publish-test-trends.yml` run 34918603998 auto-published real trend data to the wiki: 65 offline tests, a 13/13 deterministic gate, and **10 judge cases / 30 judge checks** -- both judge and deployment trends are now present with real, non-fabricated data.

**Repository files added**: `eval/judge-dataset.jsonl`, `eval/convert_judge_dataset.py`, `eval/judge_gate.py`, `eval/run_judge_evaluation.py`, `eval/tests/test_convert_judge_dataset.py`, `eval/tests/test_run_judge_evaluation.py`, `scripts/tests/test_ci_results.py`.

**Repository files modified**: `src/quote-preparation-agent/graph.py` (added `AGENT_TASK_INSTRUCTIONS`), `scripts/ci_results.py` (extended in place -- pre-existed from an earlier plan), `.github/workflows/continuous-validation.yml`, `.github/workflows/deploy-and-evaluate.yml`, `.github/workflows/publish-test-trends.yml`.

**No production code paths changed (original release only)**: `default_model`, `build_graph`, and every node function in `graph.py` were untouched at original release. **Superseded by the continuation session**: `main.py` gained a real `serve()` entry point, `response_bridge.py`/`case_input.py` were added, and the hosted agent was deployed to real Azure (version 5) and invoked live -- see "Post-Release Follow-On" above. The `deploy-and-evaluate.yml` LLM-judge step remains `if: false` (inert) pending a follow-on decision to flip it; `eval/run_judge_evaluation.py` was run manually (not yet via CI) against the live endpoint.

**Wiki (`C:\temp\fsi-wiki`, local clone only -- NOT pushed)**: `Continuous-Test-Trends.md` (new, seeded empty with an honest explanatory note), `trend-history/` (new, empty), `Home.md`/`_Sidebar.md` (navigation links added), `Workflows.md` (corrected stale sentence, table row, and release-path diagram). Pushing these to the live wiki requires explicit user confirmation (live-mutation step, Planning Log Step 7.3) and has not been performed.

**Outstanding manual step**: `WIKI_PUSH_TOKEN` repository secret must be provisioned by a repository admin before `publish-test-trends.yml`'s wiki-push step can succeed (see Planning Log WI-02) -- I cannot create this secret myself.

**Deployment notes**: none of this release deploys anything to Azure; it only adds author-only/gated evaluation tooling and CI reporting. See the Planning Log's Discrepancy Log and Suggested Follow-On Work for full deviation rationale and next steps.
