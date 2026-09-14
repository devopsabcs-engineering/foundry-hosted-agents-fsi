---
applyTo: '.copilot-tracking/changes/2026-09-14/continuous-test-trends-llm-judge-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: Continuous test trends (graphs/tables) and LLM-judge evaluation parity

## Overview

Bring `foundry-hosted-agents-fsi` to parity with the sibling `foundry-hosted-agents` repo's continuous test-trend reporting (`Continuous-Test-Trends.md` wiki page with tables + mermaid charts, backed by a `trend-history/` folder) and its real Azure AI Evaluation SDK LLM-judge metrics (coherence/groundedness/task_adherence), while respecting this repo's existing "AUTHOR-ONLY / NOT DEPLOYED" gate (G2/G3/G6) -- judge-pipeline code is written and wired but stays inert (guarded no-op) until the agent is actually hosted. Also deliver richer, data-driven GitHub Actions job summaries across all four existing workflows.

## Objectives

### User Requirements

* Bring continuous trends testing (graphs and tables) up to parity with the sibling, published to the wiki -- Source: user request "bring up to par all the continuous trends testing with graphs and tables ... in wiki"
* Add groundedness/correctness(coherence)/task_adherence metrics -- Source: user request; confirmed via clarifying question the user wants real Azure AI Evaluation SDK judge metrics (all three), not just deterministic-gate data
* Improve GitHub workflow summaries -- Source: user request "also github workflow summaries"

### Derived Objectives (from clarifying-question decisions)

* Add all three sibling metrics (`coherence`, `groundedness`, `task_adherence`) and author a real system-prompt/instructions constant to support `task_adherence` -- Derived from: user's explicit decision ("All three, and add a real system prompt now")
* Create a new, separate `eval/judge-dataset.jsonl` rather than repurposing `eval/golden-dataset.jsonl` -- Derived from: user's explicit decision; `golden-dataset.jsonl` has no `query`/`context` shape and is load-bearing for `deterministic-tests/checks.py`
* Wire `publish-test-trends.yml` to use `secrets.WIKI_PUSH_TOKEN` for a real wiki push; the user will provision the secret manually -- Derived from: user's explicit decision
* Split `pytest --junitxml` invocations per test suite for a granular "Test Suite Growth" trend breakdown -- Derived from: user's explicit decision

### Constraints Carried Forward From Research

* The judge-evaluation harness and its `deploy-and-evaluate.yml` wiring must remain inert/guarded (no real Azure call) until Gates G2/G3/G6 clear and a real hosted endpoint exists -- Derived from: repo's existing "AUTHOR-ONLY / NOT DEPLOYED" banners in `azure.yaml`/`deploy-and-evaluate.yml`/`hosted-agent-cd.yml`
* The new agent-instructions constant is eval-metadata only; it must not be wired into the graph's actual execution path or change `default_model`'s deterministic, network-free behavior -- Derived from: `graph.py`/`state.py`/`main.py` docstrings explicitly guaranteeing no LLM/network calls in this phase
* `Continuous-Test-Trends.md`/`trend-history/` must be generated from real data only; any section with no real data yet (judge metrics) must render an explicit "not yet available" fallback, never a fabricated number -- Derived from: sibling's own `render_trends()` fallback convention and this workspace's established no-fabrication discipline (see prior Planning Log DR-04)
* `scripts/deployment_summary.py` (sibling) is out of scope for porting -- Derived from: research Section (deployment_summary.py) confirming it hard-codes sibling-specific live URLs (Container Apps, Foundry projects) that do not exist for this never-deployed repo; porting it would fabricate links

## Context Summary

### Project Files

* eval/evaluation_gate.py - deterministic gate; stays unchanged; new judge module must not alter its `METRICS`-free contract
* eval/golden-dataset.jsonl - deterministic fixture dataset; must not be restructured
* eval/deterministic-tests/checks.py - underlying deterministic checks; unaffected by this plan
* eval/results.json - deterministic gate's machine-readable output; primary real-data source for trend totals
* src/quote-preparation-agent/graph.py - target location for the new eval-only instructions constant; `default_model` must remain untouched
* .github/workflows/continuous-validation.yml - only workflow that runs unattended today; primary trend-history seed source; needs split JUnit output + data-driven summary
* .github/workflows/deploy-and-evaluate.yml - AUTHOR-ONLY; needs guarded judge step, split JUnit output, and new summaries
* .github/workflows/publish-test-trends.yml - existing placeholder; needs real `ci_results.py` invocation + wiki push wiring
* .github/workflows/hosted-agent-cd.yml - thin wrapper; no changes expected beyond confirming summaries flow through
* azure.yaml - confirms `gpt-4o-mini` deployment name to reuse as judge deployment (no second deployment needed)
* C:\temp\fsi-wiki - wiki clone; add `Continuous-Test-Trends.md`, `trend-history/` seed files, update `Home.md`/`_Sidebar.md`/`Workflows.md`

### References

* .copilot-tracking/research/2026-09-14/continuous-test-trends-llm-judge-research.md - primary research document (sections A-J plus Consolidated Findings) with verbatim sibling source excerpts for `run_hosted_evaluation.py`, `ci_results.py`, `publish-test-trends.yml`, `trend-history` JSON schema, and target-repo current-state findings
* .copilot-tracking/plans/logs/2026-09-14/hosted-agents-sibling-parity-log.md - prior Planning Log; contains DR-02/DR-03/WI-02/WI-03/WI-06 entries this plan resolves

### Standards References

* None discovered beyond conventions already captured in the research document (gating-banner pattern, no-fabrication discipline)

## Implementation Checklist

### [x] Implementation Phase 1: Judge-ready dataset and eval-only agent instructions metadata

<!-- parallelizable: true -->

* [x] Step 1.1: Create `eval/judge-dataset.jsonl` (new, bilingual `query`/`context`/`expected` records derived from existing golden-dataset scenarios)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 13-45)
* [x] Step 1.2: Create `eval/convert_judge_dataset.py` (adapted converter producing the `{"data": [...]}` envelope `run_hosted_evaluation.py` expects)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 46-70)
* [x] Step 1.3: Add `AGENT_TASK_INSTRUCTIONS` module-level constant to `src/quote-preparation-agent/graph.py`, clearly documented as eval-metadata-only (not wired into `default_model`/graph execution)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 71-95)
* [x] Step 1.4: Add unit tests for the converter and dataset shape (`eval/tests/test_convert_judge_dataset.py`)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 96-108)

### [x] Implementation Phase 2: Judge evaluation harness (author-only, gated)

<!-- parallelizable: false -->

* [x] Step 2.1: Create `eval/judge_gate.py` (new sibling module to `evaluation_gate.py`; defines `METRICS = ("coherence", "groundedness", "task_adherence")` and `validate_results()`, ported near-verbatim)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 112-140)
* [x] Step 2.2: Create `eval/run_judge_evaluation.py` (adapted `run_hosted_evaluation.py`; swaps `agent_instructions()` for the new `AGENT_TASK_INSTRUCTIONS` constant; `capture()`'s hosted-invocation step is guarded to raise a clear "no hosted endpoint available yet" error rather than silently no-op) (depends on Step 1.3, Step 2.1)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 141-185)
* [x] Step 2.3: Add unit tests covering `criteria()`, `agent_instructions()`-equivalent extraction, and the guarded capture failure path (`eval/tests/test_run_judge_evaluation.py`)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 186-200)

### [x] Implementation Phase 3: Wire guarded judge step into deploy-and-evaluate.yml

<!-- parallelizable: false -->

* [x] Step 3.1: Add an `evaluate` job step installing eval SDKs (`azure-ai-projects==2.6.0`, `openai==3.6.0`, `azure-identity==1.25.3`) and invoking `eval/run_judge_evaluation.py`, guarded so it fails fast with an explicit, non-Azure-calling message until this repo has a real hosted endpoint (depends on Step 2.2)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 204-235)
* [x] Step 3.2: Update the workflow's header banner comment to describe the new guarded judge step and its activation prerequisites
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 236-245)

### [x] Implementation Phase 4: Split JUnit output per test suite

<!-- parallelizable: true -->

* [x] Step 4.1: Change `continuous-validation.yml`'s `offline` job to write separate `--junitxml` files per test directory (e.g. `evidence/agent.xml`, `evidence/deterministic.xml`, `evidence/reporting.xml`)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 249-275)
* [x] Step 4.2: Apply the same split to `deploy-and-evaluate.yml`'s `lint` job
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 276-290)

### [x] Implementation Phase 5: Port trend-aggregation script (`scripts/ci_results.py`)

<!-- parallelizable: false -->

* [x] Step 5.1: Create `scripts/ci_results.py` with `junit_totals()` (adapted `by_type` labels for this repo's suite names), a new `deterministic_gate_totals()` (reads `eval/results.json`'s real schema), a `judge_totals()` (reads judge-evaluation evidence when present; returns `None`/graceful-missing otherwise), `collect()`, `publish_history()`, `render_trends()`, `chart()`, `run_label()` (depends on Step 4.1, Step 2.1)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 294-360)
* [x] Step 5.2: Add CLI surface (`--context`, `--junit`, `--evidence/--run/--jobs/--output/--wiki` modes) matching the sibling's `main()` contract
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 361-385)
* [x] Step 5.3: Add unit tests (`scripts/tests/test_ci_results.py`) covering `junit_totals`, `deterministic_gate_totals`, `collect`/`publish_history` merge behavior, and `render_trends`'s no-judge-data fallback text
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 386-405)

### [x] Implementation Phase 6: Update publish-test-trends.yml and add richer workflow summaries

<!-- parallelizable: false -->

* [x] Step 6.1: Replace `publish-test-trends.yml`'s placeholder body with real `scripts/ci_results.py --evidence --run --jobs --output` invocation, a `WIKI_PUSH_TOKEN`-gated wiki checkout/commit/push step (mirroring sibling's exact `git -c http.extraheader` pattern), and artifact retention independent of wiki-push success (depends on Step 5.2)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 409-450)
* [x] Step 6.2: Replace `continuous-validation.yml`'s static "Offline test summary" step with a data-driven one (pass/fail/skip counts, dataset size, bilingual-parity result) using `scripts/ci_results.py --junit`
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 451-470)
* [x] Step 6.3: Add `$GITHUB_STEP_SUMMARY` writes to `deploy-and-evaluate.yml`'s `deploy-staging`, `evaluate`, and `promote-production` jobs
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 471-495)
* [x] Step 6.4: Add a summary step to `continuous-validation.yml`'s `bicep-lint` job
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 496-505)

### [ ] Implementation Phase 7: Wiki authoring -- Continuous-Test-Trends.md, trend-history/, navigation updates

<!-- parallelizable: false -->

* [x] Step 7.1: Seed `C:\temp\fsi-wiki\trend-history\` and generate an initial `Continuous-Test-Trends.md` by running the ported `scripts/ci_results.py` locally against the most recent real `continuous-validation.yml` run's data (via `gh api`) (depends on Step 5.2)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 509-535)
* [x] Step 7.2: Add a "Test Trends" entry to `Home.md` and `_Sidebar.md`; update `Workflows.md`'s stale "fully deterministic and local" sentence and its "Release path" diagram to reflect the new (gated) judge stage (depends on Step 7.1)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 536-560)
* [x] Step 7.3: Commit and push the wiki changes (live-mutation step -- confirm with user before running)
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 561-570)
  * Pushed to origin/master as commit c3b1bb4 with user confirmation.

### [x] Implementation Phase 8: Validation

<!-- parallelizable: false -->

* [x] Step 8.1: Run full pytest sweep (`eval`, `scripts/tests`) and `python eval/evaluation_gate.py`; confirm `ruff`/lint clean; confirm `eval/judge_gate.py` importable without executing any Azure call
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 574-595)
* [x] Step 8.2: Validate `az bicep build`/workflow YAML syntax (`actionlint`/`yamllint` if available, else manual review) for all four modified workflows
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 596-605)
* [x] Step 8.3: Confirm `Continuous-Test-Trends.md` renders with real data in the "Recent Runs"/"Test Suite Growth"/"Test Failures" sections and an explicit "not yet available" fallback in "Evaluation Trends"
  * Details: .copilot-tracking/details/2026-09-14/continuous-test-trends-llm-judge-details.md (Lines 606-615)
