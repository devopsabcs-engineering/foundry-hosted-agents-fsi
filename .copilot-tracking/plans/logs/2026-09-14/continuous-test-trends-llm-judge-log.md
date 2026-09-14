<!-- markdownlint-disable-file -->
# Planning Log: Continuous test trends and LLM-judge evaluation parity

**Related Plan**: continuous-test-trends-llm-judge-plan.instructions.md

## Discrepancy Log

### Implementation Deviations

* DD-01: `eval/run_judge_evaluation.py`'s `main()` guard placed after argparse parsing, not as the literal first line.
  * Plan specifies: guard "at the very top" of `main()`.
  * Implementation differs: guard fires immediately after argument parsing/validation, before any Azure import or side effect.
  * Rationale: guarding before argparse would make the documented CLI surface unreachable dead code; the safety property ("no Azure import/network call before the guard") is preserved either way.
* DD-02: `scripts/ci_results.py` was not a new file -- it already existed from an earlier, unrelated plan (`hosted-agents-sibling-parity-plan`) serving `web-chat-build.yml`'s `--junit`-only mode.
  * Plan specifies: create `scripts/ci_results.py` as new.
  * Implementation differs: extended the existing file in place, preserving its `backend`/`frontend` by-type labels for `web-chat-build.yml` compatibility (verified via a real local run against `apps/web-chat/tests` JUnit output).
* DD-03: Dropped `evaluation_totals()`/`load_totals()` and the "load" dimension entirely instead of porting stubs.
  * Plan specifies: port `evaluation_totals` (sibling name); no explicit mention of `load_totals`.
  * Implementation differs: neither exists in this repo's design (no hosted-capture pipeline, no load-test harness); keeping them would either dead-code-forever-return-None or fabricate a section.
  * Rationale: more faithful to the workspace's no-fabrication convention.
* DD-04: `deterministic_gate_totals()`'s lookup in `collect()` checks two locations (`offline-test-evidence/results.json` and `evaluation-evidence/results.json`), not the single location the details doc specified.
  * Plan specifies: `evidence / "offline-test-evidence" / "results.json"` only.
  * Implementation differs: `deploy-and-evaluate.yml`'s `evaluate` job bundles `eval/results.json` into a separate `evaluation-evidence` artifact, not `offline-test-evidence`; `collect()` now tries both so trend data is correct regardless of which workflow produced the source run.
* DD-05: Fixed an artifact-layout bug discovered during Phase 5/6 work: `continuous-validation.yml`'s original `offline-test-evidence` artifact `path:` (`evidence/*.xml` + `eval/results.json`) has different top-level directories, so GitHub's least-common-ancestor rule would nest the downloaded content as `.../evidence/*.xml` and `.../eval/results.json` -- neither matching `ci_results.py`'s flat-path reads. Fixed by adding a "Stage deterministic gate result alongside JUnit evidence" step (`cp -f eval/results.json evidence/results.json`) and changing the artifact `path:` to two entries both rooted under `evidence/`.
  * Not explicitly anticipated by the plan/details docs; discovered by direct code inspection before Phase 6 execution.
* DD-06: `Continuous-Test-Trends.md` was seeded empty (`render_trends([])`) rather than from a real historical run, and `trend-history/` was left empty.
  * Plan specifies (Step 7.1): seed from "the most recent real `continuous-validation.yml` run's data."
  * Implementation differs: the most recent completed runs on `main` (verified via `gh api`, e.g. run 34861865115) all predate this plan's JUnit-split and flat-artifact-layout changes -- their real downloaded artifact content is `eval/results.json` (nested) and a single combined `evidence/tests.xml`, neither matching the new `collect()`'s expectations. Replaying them would silently produce degraded/misleading data (e.g. all tests under "Other JUnit", deterministic gate always N/A) rather than the real per-suite breakdown this plan exists to deliver.
  * Impact: low -- the page renders correctly with an explicit, honest "no data yet" note; `publish-test-trends.yml` will populate it automatically the next time any of the three trigger workflows completes on `main` with the current (post-this-plan) definitions.

## Suggested Follow-On Work

* WI-01: After this plan's workflow changes are merged to `main` and the first `Continuous Validation` (or `Deploy and Evaluate` / `Hosted Agent CI/CD`) run completes, verify `publish-test-trends.yml` actually produces a real, populated `trend-history/<run_id>-<attempt>.json` entry and a non-empty `Continuous-Test-Trends.md` (medium priority -- closes DD-06).
  * Source: Phase 7, Step 7.1
  * Dependency: this plan's workflow-file changes must be pushed to `main` first.
* WI-02: Provision the `WIKI_PUSH_TOKEN` repository secret (a GitHub PAT or fine-grained token with wiki write access) so `publish-test-trends.yml`'s wiki-push step succeeds instead of failing loudly (high priority -- without it, every run of this workflow will report a failed job by design).
  * Source: Phase 6, Step 6.1 / user's explicit decision to wire the token now
  * Dependency: none; can be done at any time by a repository admin. **I cannot create this secret myself.**
* WI-03: Confirm GitHub Environment protection rules (required reviewers) are actually configured for the `production` environment referenced by `deploy-and-evaluate.yml`'s `promote-production` job -- flagged as still-open in the original research document's "Recommended next research" list; not verified in this implementation pass since it does not block any of this plan's file changes.
  * Source: research document, Consolidated Findings
  * Dependency: none; a repository-settings check, not a code change.
  * Priority: low.
* WI-04: Once Gates G2/G3/G6 clear and a real hosted `quote-preparation-agent` endpoint exists, flip `deploy-and-evaluate.yml`'s guarded `if: false` LLM-judge step to `if: true` and confirm `eval/run_judge_evaluation.py --output-dir judge-evidence` actually produces a `judge-results.json` matching `scripts/ci_results.py`'s `judge_totals()` expectations end-to-end against a real Azure AI Evaluation SDK call.
  * Source: Phase 3, Step 3.1
  * Dependency: Gates G2/G3/G6 sign-off; a real hosted endpoint; `AGENT_VERSION`/`PROJECT_ENDPOINT` outputs from `deploy-staging` actually populated with real values (currently placeholder-shaped since the job itself is never dispatched for real).
* WI-05: A full end-to-end read of `eval/deterministic-tests/checks.py` (flagged as still-open in the original research document) was not performed in this implementation pass; not needed since this plan did not modify that module, but still open for a future research pass if that module needs to change.
  * Source: research document, Recommended next research
  * Priority: low.

## User Decisions

* ID-01: Add all three sibling metrics (coherence, groundedness, task_adherence) and author a real system-prompt/instructions constant now, rather than deferring or scoping to two metrics.
  * Rationale: user chose the more complete option; implemented as `AGENT_TASK_INSTRUCTIONS` in `graph.py`, explicitly eval-metadata-only.
* ID-02: Create a new, separate `eval/judge-dataset.jsonl` rather than repurposing `eval/golden-dataset.jsonl`.
  * Rationale: user's explicit decision; `golden-dataset.jsonl` is structurally incompatible and load-bearing for the deterministic checks.
* ID-03: Wire `publish-test-trends.yml` to use `secrets.WIKI_PUSH_TOKEN` for a real wiki push now (user will provision the secret manually).
  * Rationale: user's explicit decision; see WI-02 above for the outstanding manual step.
* ID-04: Split `pytest --junitxml` invocations per test suite for a granular "Test Suite Growth" trend breakdown.
  * Rationale: user's explicit decision; implemented in both `continuous-validation.yml` and `deploy-and-evaluate.yml`'s `lint` job.
