<!-- markdownlint-disable-file -->
# Implementation Details: Continuous test trends and LLM-judge evaluation parity

Research source: .copilot-tracking/research/2026-09-14/continuous-test-trends-llm-judge-research.md (sections A-J, Consolidated Findings)

## Implementation Phase 1: Judge-ready dataset and eval-only agent instructions metadata

### Step 1.1: Create `eval/judge-dataset.jsonl`

* One JSON object per line, schema: `{"id": str, "category": str, "query": {"en-CA": str, "fr-CA": str}, "context": {"en-CA": str, "fr-CA": str}, "expected": {"safety_refusal_text": Optional[str], "allow_safety_refusal": bool}}`.
* `context` should restate the same synthetic case facts as `query` (mirrors sibling's `convert_for_ai_agent_evals.py` setting `context = query`; groundedness judges "no invented claims beyond input", not an external knowledge base -- Research Section A/J).
* Derive 8-12 bilingual records from existing `eval/golden-dataset.jsonl` scenarios (business-ready quote, incomplete application, invalid reference, unsupported input, self-approval fault, forged-actor fault, one prompt-injection-style case with `allow_safety_refusal: true`) -- reuse the existing case narratives/descriptions as natural-language `query` text instead of the structured `expected` fixtures.
* Do NOT modify `eval/golden-dataset.jsonl` itself -- this is fully additive, new file.

### Step 1.2: Create `eval/convert_judge_dataset.py`

* Adapted from sibling's `convert_for_ai_agent_evals.py` (Research Section J) but reading this repo's bilingual `judge-dataset.jsonl` shape from Step 1.1 instead of `input.messages`.
* CLI: `python eval/convert_judge_dataset.py <input.jsonl> <output.json> [--locale en-CA|fr-CA]` (bilingual dataset needs a locale selector since the sibling's dataset is English-only and this one is not).
* Output envelope: `{"name": "quote-preparation-agent-judge-dataset", "evaluators": ["builtin.coherence", "builtin.groundedness", "builtin.task_adherence"], "data": [{"id", "query", "context", "expected"}, ...]}` -- one record per input line, using the requested locale's `query`/`context` string.
* Fail closed (raise) on any record missing the requested locale's `query`/`context`.

### Step 1.3: Add `AGENT_TASK_INSTRUCTIONS` constant to `graph.py`

* Add as a module-level string constant near the top of `src/quote-preparation-agent/graph.py`, alongside the other module-level constants (`CASE_ID_PATTERN`, etc.), named `AGENT_TASK_INSTRUCTIONS` (mirrors sibling's `REPORT_COMPOSER_PROMPT` naming/AST-extraction pattern from Research Section A).
* Content: a plain-language description of what the composition stage is *intended* to produce (case reference validation, rulebook lookup, quote composition, bounded rejection on invalid input) -- derived from the module docstring's existing topology description, not invented.
* MUST include a docstring/comment immediately above it stating clearly: "Eval-metadata only. Not wired into `default_model`, `build_graph`, or any executed code path in this phase. Extracted via AST parsing by `eval/run_judge_evaluation.py` to give task_adherence judging a real instructions text; does not change graph execution or require network access." This preserves the file's own existing "no LLM/network calls in this phase" guarantee.
* Do NOT modify `default_model`, `build_graph`, or any node function.

### Step 1.4: Unit tests

* `eval/tests/test_convert_judge_dataset.py`: assert conversion produces the expected envelope shape for both locales, and raises on a record missing the requested locale.
* Reuse existing test conventions from `eval/tests/test_checks.py` (pytest, no special fixtures needed).

## Implementation Phase 2: Judge evaluation harness (author-only, gated)

### Step 2.1: Create `eval/judge_gate.py`

* Near-verbatim port of sibling's `eval/evaluation_gate.py` judge module (Research Section A's `METRICS`/`validate_results`, and the standalone sibling file at `foundry-hosted-agents/eval/evaluation_gate.py` read earlier in this session):
  ```python
  """Fail closed on incomplete, errored, unscored, or below-policy judge evaluations.

  Separate from eval/evaluation_gate.py (the deterministic gate) so that
  module's own docstring claim -- "there are no quality judges in this
  deterministic gate at all" -- stays true and auditable. This module is
  the LLM-judge counterpart, used only by eval/run_judge_evaluation.py,
  and only once this repository has a real hosted agent endpoint.
  """
  import math

  METRICS = ("coherence", "groundedness", "task_adherence")

  def validate_results(run, items, expected_count, minimum_pass_rate=1.0):
      # ... port verbatim from sibling eval/evaluation_gate.py validate_results ...
  ```
* Copy the sibling's `validate_results` body verbatim (already captured in this session's direct read of `foundry-hosted-agents/eval/evaluation_gate.py`); no logic changes needed, it is domain-agnostic.

### Step 2.2: Create `eval/run_judge_evaluation.py`

* Adapted from sibling's `eval/run_hosted_evaluation.py` (Research Section A full excerpt). Keep verbatim: `criteria()`, `collect_output_items()`, `evaluate()`'s `AIProjectClient`/`client.evals.create`/`client.evals.runs.create` polling loop, `validate_results` usage.
* Replace `agent_instructions()`:
  ```python
  def agent_instructions() -> str:
      source = Path(__file__).parents[1] / "src" / "quote-preparation-agent" / "graph.py"
      names = {"AGENT_TASK_INSTRUCTIONS"}
      # ... identical AST-parse body as sibling, just the new path/name ...
  ```
* Replace `capture()`: this repo has no `scripts/invoke-agent.sh` equivalent and no hosted endpoint (Research Section H). Implement `capture()` to raise immediately with a clear, explicit error (not a silent no-op):
  ```python
  def capture(records, args):
      raise RuntimeError(
          "No hosted-agent invocation harness exists yet in this repository "
          "(no scripts/invoke-agent.sh equivalent, no Responses-protocol "
          "endpoint). This step is author-only and cannot run until the "
          "agent is hosted and Gates G2/G3/G6 clear. See azure.yaml."
      )
  ```
* CLI args (`main()`): same shape as sibling (`--endpoint`, `--agent`, `--version`, `--deployment`, `--dataset`, `--output-dir`, `--project-dir`, `--minimum-pass-rate`), but add a top-of-`main()` explicit guard printing the same "author-only, not yet runnable" message and exiting 1 before attempting `capture()`, so a curious/accidental local invocation fails fast with a clear message rather than a raw `RuntimeError` traceback deep in `capture()`.
* Add a module docstring banner matching the repo's existing "AUTHOR-ONLY" convention.

### Step 2.3: Unit tests

* `eval/tests/test_run_judge_evaluation.py`: test `criteria()` produces 3 entries with correct `data_mapping` per metric (task_adherence uses `task_query`/`output_items`, others use `query`/`response`); test `agent_instructions()` correctly extracts `AGENT_TASK_INSTRUCTIONS` from `graph.py` via the real AST parse (integration-style, reads the real file); test `main()`/`capture()` raises the expected guard error without attempting any network call (mock nothing -- the guard must trigger before any import of `azure.ai.projects`).

## Implementation Phase 3: Wire guarded judge step into deploy-and-evaluate.yml

### Step 3.1: Add guarded judge step to the `evaluate` job

* Add after the existing "Deterministic evaluation gate (release quality control)" step:
  ```yaml
      - name: Install judge evaluation SDKs
        run: python -m pip install azure-ai-projects==2.6.0 openai==3.6.0 azure-identity==1.25.3

      - name: LLM-judge evaluation gate (author-only; not yet activated)
        if: false  # Flip once Gates G2/G3/G6 clear and a hosted endpoint exists; see azure.yaml banner.
        env:
          JUDGE_DEPLOYMENT: gpt-4o-mini
        run: |
          python eval/convert_judge_dataset.py eval/judge-dataset.jsonl "$RUNNER_TEMP/judge-dataset.json" --locale en-CA
          python eval/run_judge_evaluation.py \
            --endpoint "$PROJECT_ENDPOINT" --agent quote-preparation-agent \
            --version "$AGENT_VERSION" --deployment "$JUDGE_DEPLOYMENT" \
            --dataset "$RUNNER_TEMP/judge-dataset.json" \
            --output-dir judge-evidence --minimum-pass-rate 1.0
  ```
* `if: false` is the deliberate, explicit no-op guard (GitHub Actions skips the step entirely; it never installs/calls anything at runtime) -- this is the concrete mechanism satisfying "must remain inert until gates clear."
* Do not remove/alter the existing deterministic "Deterministic evaluation gate (release quality control)" step.

### Step 3.2: Update header banner

* Extend the existing "AUTHOR-ONLY / DO NOT DISPATCH UNTIL GATES CLEAR" comment block to add one paragraph: this workflow's `evaluate` job now also contains a guarded (`if: false`) LLM-judge step (`eval/run_judge_evaluation.py`) for future activation once a real hosted endpoint exists; flipping it to `if: true` before that is misconfiguration, not a supported state.

## Implementation Phase 4: Split JUnit output per test suite

### Step 4.1: `continuous-validation.yml`'s `offline` job

* Replace the single `pytest ... --junitxml=evidence/tests.xml` invocation with four separate invocations into `evidence/`:
  ```yaml
      - name: Agent graph unit tests
        run: pytest src/quote-preparation-agent/tests -v --junitxml=evidence/agent.xml
      - name: Deterministic evaluation checks
        run: pytest eval -v --junitxml=evidence/deterministic.xml
      - name: Reporting and contract tests
        run: pytest apps/workshop/tests mcp/application-server/tests mcp/rulebook-server/tests -v --junitxml=evidence/reporting.xml
  ```
* Keep `if: always()` on the artifact-retention step; update its `path:` glob to `evidence/*.xml` (already a glob, no change needed there).
* Verify no test collisions/ordering dependency exists between these three groups (they are independent directories today per the existing single combined invocation).

### Step 4.2: `deploy-and-evaluate.yml`'s `lint` job

* Apply the identical three-way split (same directory groupings) replacing the single `pytest ... --junitxml=offline-evidence/tests.xml` step; write to `offline-evidence/agent.xml`, `offline-evidence/deterministic.xml`, `offline-evidence/reporting.xml`.

## Implementation Phase 5: Port trend-aggregation script (`scripts/ci_results.py`)

### Step 5.1: Core functions

* `junit_totals(directory)`: port sibling's function (Research Section C verbatim excerpt) with an updated `by_type` label map for this repo's filenames:
  ```python
  label = {
      "agent": "Agent graph",
      "deterministic": "Deterministic evaluation",
      "reporting": "Reporting and contract tests",
  }.get(path.stem, "Other JUnit")
  ```
* `deterministic_gate_totals(path=Path("eval/results.json"))` (NEW, replaces sibling's `evaluation_totals` which depends on files this repo doesn't produce): reads `eval/results.json`'s real schema (`dataset_size`, `records[].passed`, `bilingual_parity.passed`, `passed` -- confirmed via this session's direct read of `eval/evaluation_gate.py`'s `evaluate()` return shape). Returns `{"dataset_size": int, "passed_records": int, "failed_records": int, "bilingual_parity": bool, "gate_passed": bool}` or `None` if the file is missing/malformed.
* `judge_totals(directory)` (NEW): looks for `directory/judge-results.json` (the output `run_judge_evaluation.py` would write once activated, per Step 2.2's `--output-dir`). Returns `None` gracefully if absent (this is the expected/normal state until Phase 3's guard is lifted) -- must NOT raise.
* `collect(evidence, run, jobs)`: port sibling's function (Research Section C verbatim) with `record["evaluation"]` populated by `judge_totals()` instead of the sibling's function, and add a new `record["deterministic_gate"]` key populated by `deterministic_gate_totals()`.
* `publish_history(record, wiki)`: port verbatim (Research Section C's exact merge-on-republish behavior, `trend-history/{run_id}-{attempt}.json` naming).
* `render_trends(records)`: port sibling's structure (Research Section C: front-matter, Scope, Recent Runs table, Test Suite Growth table+charts, Test Failures chart, Evaluation Trends [grouped by dataset/evaluator/judge/environment lineage, falls back to "No comparable evaluation lineage has been collected yet." when no judge data exists across all records], Reporting Gaps) but ADD a new "## Deterministic Gate" section (table: run/attempt, dataset size, passed/failed records, bilingual parity) sourced from the new `deterministic_gate` field -- this is real data available today, distinct from judge trends.
* `chart(title, samples, axis)`, `run_label(record)`: port verbatim (Research Section C exact code).

### Step 5.2: CLI surface

* Match sibling's three modes (Research Section C `main()` breakdown): `--context`, `--junit`, and the full `--evidence --run --jobs [--output] [--wiki]` mode. Adjust `--context` mode's allow-listed keys if judge context isn't applicable yet (keep the same key set for forward-compatibility: `environment`, `agent_version`, `agent_content_hash`, `dataset_sha256`, `evaluator_sha256`, `judge_deployment`, `version_after`).

### Step 5.3: Unit tests

* `scripts/tests/test_ci_results.py`: `junit_totals` against a small fixture XML tree; `deterministic_gate_totals` against a fixture `results.json` matching the real schema; `collect`/`publish_history` round-trip (write, re-publish with a partial record, confirm merge-not-overwrite); `render_trends` output contains the "No comparable evaluation lineage has been collected yet." fallback string when no records have judge data.

## Implementation Phase 6: Update publish-test-trends.yml and richer summaries

### Step 6.1: `publish-test-trends.yml`

* Replace the current placeholder body (Research Section F verbatim current content) with the sibling's real structure (Research Section B's `publish-test-trends.yml` full read, adapted):
  1. Verify source run provenance (`gh api .../attempts/<attempt>`, `jq -e` checks matching this repo's own workflow file paths: `continuous-validation.yml`, `deploy-and-evaluate.yml`, `hosted-agent-cd.yml`).
  2. Download only this attempt's known evidence artifacts (`offline-test-evidence-<attempt>`, `evaluation-evidence-<attempt>` if present, no `load-test-evidence` since this repo has no load-test harness -- omit that kind).
  3. `python scripts/ci_results.py --evidence evidence --run source-run.json --jobs source-jobs.json --output ci-report`.
  4. Upload `ci-report/` as an artifact regardless of wiki-push outcome.
  5. Wiki push step gated on `secrets.WIKI_PUSH_TOKEN`: if unset, `::error::` + append a clear message to `$GITHUB_STEP_SUMMARY` and `exit 1` (matches sibling's fail-loud-not-silent behavior, Research Section B verbatim); if set, clone `https://github.com/$GITHUB_REPOSITORY.wiki.git` with the token, re-run `ci_results.py` with `--wiki wiki`, commit only if the diff is non-empty, push, and append a link to `$GITHUB_STEP_SUMMARY`.
* Keep the existing `on:`/`concurrency:`/`permissions:` blocks (already correct); update the header comment to remove the now-stale "Neither the reporting scripts nor a wiki-push requirement exists in this repository" sentence.

### Step 6.2: `continuous-validation.yml` data-driven summary

* Replace the static "Offline test summary" step with:
  ```yaml
      - name: Offline test summary
        if: always()
        run: python scripts/ci_results.py --junit evidence
  ```
  (matches sibling's `--junit` mode, Research Section C: prints a `## Offline Test Results` block with pass/fail/skip counts and a by-type table, appended to `$GITHUB_STEP_SUMMARY` automatically since that mode already checks `os.environ.get("GITHUB_STEP_SUMMARY")`).
* Add a second step after `python eval/evaluation_gate.py` writing the deterministic gate's real numbers, e.g. a small inline step parsing `eval/results.json` (`dataset_size`, `passed`, `bilingual_parity.passed`) into a `## Deterministic Evaluation Gate` block.

### Step 6.3: `deploy-and-evaluate.yml` summaries

* `deploy-staging` job: after the existing deploy steps, add a step writing `## Deployed Candidate` with `agent_version`/`project_endpoint` output values to `$GITHUB_STEP_SUMMARY`.
* `evaluate` job: after "Deterministic evaluation gate (release quality control)", add a step parsing `eval/results.json` into a `## Deterministic Evaluation Gate (Release)` block (same shape as Step 6.2's second bullet, reusable as one small script/step).
* `promote-production` job: add a step writing `## Promoted <previous> -> <new>` using the job's existing version-discovery outputs.

### Step 6.4: `continuous-validation.yml`'s `bicep-lint` job summary

* Add a step after `az bicep build` listing which `.bicep` files were built and confirming zero diagnostics, appended to `$GITHUB_STEP_SUMMARY`.

## Implementation Phase 7: Wiki authoring

### Step 7.1: Seed trend-history and initial Continuous-Test-Trends.md

* Identify the most recent completed `Continuous Validation` run on `main` via `gh api repos/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs?...`.
* Fetch that run's `run`/`jobs` JSON and any available `offline-test-evidence-*`/`evaluation-evidence-*` artifacts (evaluation-evidence will not exist yet -- that's expected/correct, matches the "not yet available" judge fallback).
* Run `python scripts/ci_results.py --evidence <dir> --run run.json --jobs jobs.json --output ci-report --wiki C:\temp\fsi-wiki` locally to produce the first real `trend-history/<run_id>-<attempt>.json` and regenerate `Continuous-Test-Trends.md`.
* If no completed `Continuous Validation` run exists yet to seed from, document this explicitly in the Planning Log as a follow-on ("first real trend-history entry will be created by the next `publish-test-trends.yml` run") rather than fabricating a seed record.

### Step 7.2: Navigation updates

* `C:\temp\fsi-wiki\Home.md`: add `* [Test Trends](Continuous-Test-Trends): CI test and evaluation measurements with immutable source-run links.` to the "Pages" bullet list.
* `C:\temp\fsi-wiki\_Sidebar.md`: add the matching link entry, consistent with its existing list format.
* `C:\temp\fsi-wiki\Workflows.md`: update the sentence "this repository's evaluation gate (`eval/evaluation_gate.py`) is fully deterministic and local -- it does not call an LLM judge or a live agent endpoint" to instead state that an LLM-judge evaluation path now exists in `eval/run_judge_evaluation.py` but is guarded/inert (`if: false` in `deploy-and-evaluate.yml`) pending a real hosted endpoint and Gate clearance; update the "Release path" mermaid diagram to add a `Judge[LLM-judge evaluation gate (guarded, not yet active)]` box.
* Also update `publish-test-trends.yml`'s row in `Workflows.md`'s workflow table to reflect the real wiki-push behavior (remove "Does not push to the wiki" sentence).

### Step 7.3: Commit and push wiki changes

* Live-mutation step: stage `Continuous-Test-Trends.md`, `trend-history/`, `Home.md`, `_Sidebar.md`, `Workflows.md` in the `C:\temp\fsi-wiki` clone; commit with a message following this workspace's commit-message conventions; **confirm with the user before pushing** to `origin/master` (same discipline as the prior plan's Step 4.6/1.1 live-mutation confirmations).

## Implementation Phase 8: Validation

### Step 8.1: Python validation

* `pytest eval scripts/tests -v` (new tests from Phases 1, 2, 5).
* `python eval/evaluation_gate.py` (confirm deterministic gate still passes, unaffected by new files).
* `python -c "import eval.judge_gate"` and `python -c "import eval.run_judge_evaluation"` (confirm both import cleanly with zero side effects/no Azure SDK calls at import time).
* Run `ruff check eval scripts` if `ruff.toml` scope already covers these paths (extend scope if it doesn't, matching existing repo convention).

### Step 8.2: Workflow YAML validation

* Manually review each modified workflow file's YAML structure (or run `actionlint`/`yamllint` if available in the environment) for the four files: `continuous-validation.yml`, `deploy-and-evaluate.yml`, `publish-test-trends.yml`, and confirm `hosted-agent-cd.yml` needs no direct edits.

### Step 8.3: Wiki content validation

* Open the generated `Continuous-Test-Trends.md` and confirm: "Recent Runs"/"Test Suite Growth"/"Test Failures"/"Deterministic Gate" sections show real numbers (not placeholders), "Evaluation Trends" section shows the explicit no-data-yet fallback text, and all internal links (`Home.md`, `_Sidebar.md`) resolve to the new page.
