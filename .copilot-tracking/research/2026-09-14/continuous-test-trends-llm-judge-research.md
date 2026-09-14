---
title: Continuous Test Trends and LLM-Judge Evaluation — Sibling-Repo Research
description: Verbatim findings from foundry-hosted-agents (sibling) to inform porting real Azure AI Evaluation SDK judge metrics and Continuous-Test-Trends.md wiki reporting into foundry-hosted-agents-fsi.
---

## Scope and repos referenced

- Target: `c:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents-fsi` (AUTHOR-ONLY, never deployed, gated behind G2/G3/G6).
- Sibling source repo: `c:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents` (deployed, threat-assessment-agent domain).
- Sibling wiki clone: `c:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents-wiki` (has `Continuous-Test-Trends.md` + `trend-history/`).
- Target wiki clone: `C:\temp\fsi-wiki` (no `Continuous-Test-Trends.md` yet).

All line numbers below refer to the file state at research time (2026-09-14).

## A. `eval/run_hosted_evaluation.py` (sibling) — full contract

File: `foundry-hosted-agents/eval/run_hosted_evaluation.py` (382 lines). Imports `METRICS, validate_results` from `evaluation_gate` (line 17).

### `criteria(deployment)` — lines 251-265

```python
def criteria(deployment: str) -> list[dict]:
    return [
        {
            "type": "azure_ai_evaluator",
            "name": metric,
            "evaluator_name": f"builtin.{metric}",
            "initialization_parameters": {"deployment_name": deployment},
            "data_mapping": {
                "query": "{{item.task_query}}" if metric == "task_adherence" else "{{item.query}}",
                "context": "{{item.context}}",
                "response": "{{item.output_items}}" if metric == "task_adherence" else "{{item.response}}",
            },
        }
        for metric in METRICS
    ]
```

`METRICS = ("coherence", "groundedness", "task_adherence")` (sibling `eval/evaluation_gate.py` line 6). Each metric becomes one `azure_ai_evaluator` testing criterion registered against the Azure AI Evaluation SDK's **builtin evaluator catalog** (`builtin.coherence`, `builtin.groundedness`, `builtin.task_adherence`), all pointed at the same judge model deployment.

### `agent_instructions()` — lines 238-249 (AST-extraction of the system prompt)

```python
def agent_instructions() -> str:
    source = Path(__file__).parents[1] / "src" / "threat-assessment-agent" / "graph.py"
    names = {"REPORT_COMPOSER_PROMPT"}
    prompts = {}
    for statement in ast.parse(source.read_text(encoding="utf-8")).body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    prompts[target.id] = ast.literal_eval(statement.value)
    if prompts.keys() != names or any(not isinstance(value, str) or not value for value in prompts.values()):
        raise ValueError("Cannot resolve agent instructions for task-adherence evaluation")
    return "\n\n".join(prompts.values())
```

This parses `graph.py`'s module-level `REPORT_COMPOSER_PROMPT` string constant via `ast.parse`/`ast.literal_eval` (no import/exec of the module — avoids needing the agent's runtime deps just to read its prompt text). It **fails closed** (raises `ValueError`) if the constant is missing, renamed, or not a nonempty string.

### `evaluate()` — how `client.evals.runs.create` is called and awaited — lines 267-339

```python
def evaluate(captured: list[dict], args) -> None:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    instructions = agent_instructions()
    evaluation_records = [
        {**record, "task_query": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": record["query"]},
        ]}
        for record in captured
    ]
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=args.endpoint, credential=credential) as project,
        project.get_openai_client() as client,
    ):
        evaluation = client.evals.create(
            name=f"Hosted CI {args.agent}:{args.version}",
            data_source_config={
                "type": "custom",
                "include_sample_schema": False,
                "item_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "task_query": {"type": "array"},
                        "context": {"type": "string"},
                        "response": {"type": "string"},
                        "output_items": {"type": "array"},
                    },
                    "required": ["query", "task_query", "context", "response", "output_items"],
                },
            },
            testing_criteria=criteria(args.deployment),
        )
        run = client.evals.runs.create(
            eval_id=evaluation.id,
            name=f"{args.agent}:{args.version}",
            data_source={
                "type": "jsonl",
                "source": {
                    "type": "file_content",
                    "content": [{"item": record} for record in evaluation_records],
                },
            },
        )
        ...
        print(f"Evaluation {evaluation.id}, run {run.id}", flush=True)
        deadline = time.monotonic() + 1200
        while run.status not in ("completed", "failed", "canceled", "cancelled"):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Evaluation exceeded 20 minutes: {run.id}")
            time.sleep(10)
            run = client.evals.runs.retrieve(eval_id=evaluation.id, run_id=run.id)
        items = collect_output_items(client, evaluation.id, run.id, len(captured))
        result = {"run": run.model_dump(mode="json"), "items": items}
        (args.output_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        ...
        try:
            validate_results(result["run"], items, len(captured), args.minimum_pass_rate)
        except ValueError as error:
            summary.extend(["", f"**FAIL:** {error}"])
            raise
        else:
            summary.extend(["", "**PASS:** model-judged responses satisfy quality policy; "
                            "the release also requires capture and deterministic policy checks."])
        finally:
            text = "\n".join(summary) + "\n"
            (args.output_dir / "summary.md").write_text(text, encoding="utf-8")
            if os.environ.get("GITHUB_STEP_SUMMARY"):
                with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
                    handle.write(text)
            print(text)
```

Key mechanics:
- Uses `AIProjectClient(endpoint=..., credential=DefaultAzureCredential())` then `project.get_openai_client()` — evaluation is driven through the **OpenAI-compatible `evals` surface** exposed by the Foundry project client, not a bespoke evaluation SDK object.
- `client.evals.create(...)` registers the evaluation (testing criteria + a `custom` JSON-schema item shape). `client.evals.runs.create(...)` supplies the actual data via an inline `jsonl`/`file_content` data source (no file upload step — the captured records are embedded directly).
- Poll loop: `time.sleep(10)` up to a **20-minute (1200s) deadline**, calling `client.evals.runs.retrieve(...)` until `run.status` is terminal (`completed`/`failed`/`canceled`/`cancelled`); raises `TimeoutError` past the deadline.
- `collect_output_items()` (lines 227-236) retries up to 7 times (10s apart) via `client.evals.runs.output_items.list(...)` until `len(items) >= expected_count`.
- Writes `results.json` (the full run + items payload) unconditionally, then calls `validate_results` — a `ValueError` here re-raises after writing `summary.md` and appending to `$GITHUB_STEP_SUMMARY` (fail-closed, but always leaves an audit trail).
- `task_adherence`'s `query` mapping is the two-message `task_query` array (`system` = extracted prompt, `user` = original query); `response` for `task_adherence` is the **full `output_items`** array (not just the final text) — the other two metrics (`coherence`, `groundedness`) use the plain `query`/`response` strings.
- **`context` is mapped straight from `record["context"]`**, and (per Section J below) the sibling's own `convert_for_ai_agent_evals.py` sets `context` = the same value as `query` — i.e. even the sibling does not have a separate ground-truth "context" document; groundedness here is being judged against the *user's own input restated*, not external retrieved evidence. This is an important nuance for any port: "groundedness" is not being scored against a knowledge base, it's checking that the report doesn't fabricate claims beyond what the input already asserted.

### `capture()` — lines 96-145 (how hosted responses are obtained, not requested to be repeated in full but relevant for gating)

Invokes `bash scripts/invoke-agent.sh` as a subprocess per dataset record (up to 3 attempts, 180s timeout each), setting `AGENT_NAME`/`AGENT_VERSION`/`AGENT_TEST_PROMPT` env vars, and parses the SSE stream via `completed_response()`. This is the sibling's live-hosted-agent capture step and **has no equivalent script in the target repo** (no `scripts/invoke-agent.sh`; `main.py` is local-only — see target's own gating-comment banner in `deploy-and-evaluate.yml`).

### CLI args / `main()` — lines 342-382

```python
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--minimum-pass-rate", type=float, default=1.0)
    args = parser.parse_args()
    if not 0 < args.minimum_pass_rate <= 1:
        parser.error("minimum-pass-rate must be in (0, 1]")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = json.loads(args.dataset.read_text(encoding="utf-8"))["data"]
    if not records:
        raise ValueError("Evaluation dataset is empty")
    environment = subprocess.run(
        [shutil.which("azd") or "azd", "env", "get-values", "--output", "json"],
        cwd=args.project_dir, capture_output=True, text=True, encoding="utf-8", timeout=60, check=True,
    )
    if json.loads(environment.stdout).get("FOUNDRY_PROJECT_ENDPOINT", "").rstrip("/") != args.endpoint.rstrip("/"):
        raise ValueError("Selected azd environment does not match the evaluation endpoint")
    captured = capture(records, args)
    failures = capture_summary(captured, args)
    # (failures are not shown gating evaluate() in the excerpt captured here, but
    #  the CI caller only proceeds to run_hosted_evaluation.py for the judge stage
    #  after capture + the deterministic policy check both hold; see Section B.)
```

- `--dataset` is **not** the raw `golden-dataset.jsonl` — it is the JSON envelope produced by `eval/convert_for_ai_agent_evals.py` (`{"data": [...]}`), confirmed by the `json.loads(...)["data"]` read and by the CI step name "Convert golden dataset without dropping cases" (Section B).
- `--deployment` is the **judge model deployment name**, passed through unchanged into `criteria()`'s `initialization_parameters.deployment_name` for every metric — one judge deployment scores all three metrics.
- Safety check: refuses to run if the currently-selected `azd` environment's `FOUNDRY_PROJECT_ENDPOINT` doesn't match `--endpoint`, preventing an accidental cross-environment evaluation run.

## B. `.github/workflows/deploy-and-evaluate.yml` (sibling) — evaluation job wiring

File: `foundry-hosted-agents/.github/workflows/deploy-and-evaluate.yml`.

### The `evaluate` job (Stage 5, "Offline evaluation quality gate")

Relevant steps (in order):

1. **Install evaluation SDKs**: `pip install azure-ai-projects==2.6.0 openai==3.6.0 azure-identity==1.25.3` — this is the exact SDK pin used for the judge pipeline.
2. **Verify full-history follow-up and conversation isolation**: runs `python eval/check_conversation.py --endpoint "$PROJECT_ENDPOINT/agents/$AGENT_NAME/endpoint/protocols/openai/responses?api-version=v1" --output-dir ...` (a separate live conversation-continuity regression, not judge scoring — see Section J).
3. **Convert golden dataset without dropping cases**: `python3 eval/convert_for_ai_agent_evals.py "$GOLDEN_DATASET_PATH" "${{ runner.temp }}/golden_dataset_for_ai_agent_evals.json"`.
4. **Capture hosted responses and enforce evaluation policy** (the main step; 90-minute job timeout):
   ```yaml
   env:
     PROJECT_ENDPOINT: ${{ needs.deploy-staging.outputs.project_endpoint }}
     AGENT_VERSION: ${{ needs.deploy-staging.outputs.agent_version }}
     JUDGE_DEPLOYMENT: ${{ vars.FOUNDRY_MODEL_NAME }}
     AZURE_DEV_USER_AGENT: microsoft_foundry_skill
   run: |
     python scripts/ci_results.py \
       --context "${{ runner.temp }}/evaluation-evidence/context.json" \
       --dataset "$GOLDEN_DATASET_PATH" --agent-version "$AGENT_VERSION"
     python eval/run_hosted_evaluation.py \
       --endpoint "$PROJECT_ENDPOINT" --agent "$AGENT_NAME" \
       --version "$AGENT_VERSION" --deployment "$JUDGE_DEPLOYMENT" \
       --dataset "${{ runner.temp }}/golden_dataset_for_ai_agent_evals.json" \
       --output-dir "${{ runner.temp }}/evaluation-evidence" \
       --minimum-pass-rate 1.0
   ```
5. **Upload evaluation evidence even on failure**: `evaluation-evidence-${{ github.run_attempt }}` artifact, `if: always()`.

**Critical fact — judge model deployment identity**: `JUDGE_DEPLOYMENT: ${{ vars.FOUNDRY_MODEL_NAME }}`. `FOUNDRY_MODEL_NAME` is a **repository/environment variable** (not found anywhere in `infra/*.bicep` via grep — it is only referenced through `vars.FOUNDRY_MODEL_NAME` in workflow YAML and set into the `azd` environment during `deploy-staging`: `azd env set FOUNDRY_MODEL_NAME "${{ vars.FOUNDRY_MODEL_NAME }}"`). This is the **same** model deployment name used to configure the *agent's own* chat model (it is set into the azd environment alongside `FOUNDRY_PROJECT_ENDPOINT`/`AZURE_AI_PROJECT_ID` before `azd deploy`, i.e. it is the agent runtime's model too) — **the sibling reuses one model deployment as both the agent's own completion model and the judge model.** There is no dedicated second/"judge-only" deployment declared anywhere in the sibling's Bicep or `azure.yaml`.

Authentication/permissions for the whole workflow: `permissions: id-token: write, contents: read` (top of file) — secretless OIDC via `azure/login@v3` with `vars.AZURE_CLIENT_ID`/`AZURE_TENANT_ID`/`AZURE_SUBSCRIPTION_ID`, same pattern reused in every job including `evaluate`.

### No `WIKI_PUSH_TOKEN` / wiki-push step in `deploy-and-evaluate.yml` itself

Grep and full read of this file found **no** `git push`, no wiki checkout, and no `WIKI_PUSH_TOKEN`/similar secret anywhere in `deploy-and-evaluate.yml`. Trend/wiki publication is **not** part of the release workflow — it happens in a separate, `workflow_run`-triggered workflow (the sibling's `publish-test-trends.yml`, not fully re-read verbatim in this session, but its target-repo *simplified derivative* was read in full — see Section F below — and its header comment explicitly states the sibling's version "pushes an aggregate history to the repository wiki via a `WIKI_PUSH_TOKEN` secret"). The wiki-push mechanics live in that separate workflow, not in `deploy-and-evaluate.yml`.

### Which job runs `scripts/ci_results.py`

Two distinct invocation shapes exist in the sibling, confirmed from source:
- `deploy-and-evaluate.yml`'s `evaluate` job calls `ci_results.py --context ... --dataset ... --agent-version ...` (the **context-recording** mode — writes `evaluation-evidence/context.json` with dataset/evaluator SHA-256 hashes, judge deployment name, agent version — see Section C's `main()` `--context` branch).
- The **CI-report/trend-aggregation** mode (`--evidence/--run/--jobs/--wiki`) is invoked from a *different* job/workflow not captured verbatim in this pass (the `lint` job in `deploy-and-evaluate.yml` calls `python scripts/ci_results.py --junit offline-evidence` for the **JUnit-summary** mode instead — see the `lint` job's "Publish offline test summary" step). The full record-collection-and-wiki-publish invocation (`--evidence/--run/--jobs/--wiki`) is what the sibling's `publish-test-trends.yml` (a separate `workflow_run`-triggered workflow, not re-read verbatim here) must call after the run completes, since `collect()`/`publish_history()` need the **completed** run's `run`/`jobs` API payloads (via `gh api .../actions/runs/<id>` and `.../jobs`), which are only obtainable once the source run has finished — consistent with the target repo's already-adapted `publish-test-trends.yml` being a `workflow_run: types: [completed]` listener (Section F).

### `build-release-evidence.js` invocation

Not called from `deploy-and-evaluate.yml` at all (grep/read found no reference). It is a standalone script invoked manually/out-of-band (see its own `--capture` CLI branch in Section D) — it is **not part of the automated CI/CD wiring**.

## C. `scripts/ci_results.py` (sibling) — full function inventory

File: `foundry-hosted-agents/scripts/ci_results.py` (full read, ~400 lines).

### Inputs it reads

| Function | Reads |
| --- | --- |
| `junit_totals(directory)` | `*.xml` JUnit files in `directory` (e.g. `offline-test-evidence/agent.xml`, `deterministic.xml`, `reporting.xml`, `backend.xml`, `frontend.xml`) |
| `evaluation_totals(directory)` | `directory/captured.json`, `directory/candidate-policy.json`, `directory/results.json`, `directory/run-identity.json` (the exact artifact names `run_hosted_evaluation.py` writes) |
| `load_totals(directory)` | `directory/concurrent-sessions.json` (a load-test harness output not otherwise covered in this research pass) |
| `collect(evidence, run, jobs)` | the three folders above under `evidence/`, plus the GitHub Actions **run** and **jobs** API JSON payloads (passed in as already-parsed dicts, sourced from `gh api repos/.../actions/runs/<id>` and `.../jobs`) |

### `junit_totals` — lines ~30-53 (verbatim)

```python
def junit_totals(directory):
    files = sorted(directory.glob("*.xml"))
    if not files:
        return None
    totals = dict(tests=0, failed=0, skipped=0, seconds=0.0)
    by_type = {}
    for path in files:
        root = ET.parse(path).getroot()
        label = {
            "agent": "Agent graph",
            "deterministic": "Deterministic evaluation",
            "reporting": "Reporting and load contracts",
            "backend": "Web chat backend",
            "frontend": "Web chat frontend",
        }.get(path.stem, "Other JUnit")
        by_type.setdefault(label, 0)
        for case in root.iter("testcase"):
            by_type[label] += 1
            totals["tests"] += 1
            totals["failed"] += int(case.find("failure") is not None or case.find("error") is not None)
            totals["skipped"] += int(case.find("skipped") is not None)
            duration = float(case.get("time", "0"))
            if not math.isfinite(duration) or duration < 0:
                raise ValueError("Invalid JUnit duration")
            totals["seconds"] += duration
    totals["passed"] = totals["tests"] - totals["failed"] - totals["skipped"]
    totals["seconds"] = round(totals["seconds"], 3)
    totals["by_type"] = by_type
    return totals
```

The `by_type` label mapping is keyed on the **JUnit filename stem** (`agent.xml` -> "Agent graph", `deterministic.xml` -> "Deterministic evaluation", `reporting.xml` -> "Reporting and load contracts", `backend.xml`/`frontend.xml` -> web-chat labels, anything else -> "Other JUnit"). This is sibling-domain-specific naming that a target-repo port must rename (target's JUnit output is `offline-evidence/tests.xml`, a single combined file, not per-suite files — see Section F).

### `evaluation_totals` — lines ~56-95 (verbatim, judge-rate aggregation)

```python
def evaluation_totals(directory):
    captures = read_json(directory / "captured.json")
    policy = read_json(directory / "candidate-policy.json")
    results = read_json(directory / "results.json")
    identity = read_json(directory / "run-identity.json") or {}
    if captures is None and results is None:
        return None
    totals = {
        "captured": len(captures) if captures is not None else None,
        "capture_errors": sum(bool(item.get("capture_error")) for item in captures) if captures is not None else None,
        "policy_failures": len(policy) if policy is not None else None,
        "tool_receipts": sum(len(item.get("runtime_state", {}).get("tool_calls", [])) for item in captures) if captures is not None else None,
        "agent_version": identity.get("version"),
        "eval_run": identity.get("run_id"),
        "judge_rates": None,
    }
    if results is not None:
        items = results.get("items", [])
        try:
            totals["judge_rates"] = validate_results(results.get("run", {}), items, len(items), 0.000001)
        except ValueError:
            complete = True
            rates = {}
            for metric in METRICS:
                judged = [result for item in items for result in item.get("results", []) if result.get("name") == metric]
                if (not judged or len(judged) != len(items)
                    or any(type(result.get("passed")) is not bool or result.get("error")
                           or result.get("status") == "error" for result in judged)):
                    complete = False
                else:
                    rates[metric] = sum(result["passed"] for result in judged) / len(judged)
            if complete:
                try:
                    validation_copy = json.loads(json.dumps(results))
                    for item in validation_copy["items"]:
                        for result in item["results"]:
                            result["passed"] = True
                    validate_results(validation_copy["run"], validation_copy["items"], len(items))
                    totals["judge_rates"] = rates
                except ValueError:
                    pass
        totals["judged"] = len(items)
    return totals
```

Notably it calls `validate_results(..., minimum_pass_rate=0.000001)` first (i.e. "did the run *complete* cleanly at all", almost any nonzero rate passes), and only if that raises does it fall back to manually computing raw per-metric pass rates from `item["results"]` — but even then it double-checks structural completeness (one result per metric per item, boolean `passed`, no `error`) by re-validating a copy with all `passed` forced `True` before trusting the rates. This means **judge rates are only reported if the evaluation SDK payload is structurally sound**, even when the underlying policy failed — reporting infrastructure never fabricates a rate from malformed/incomplete data.

### Outputs — `trend-history/<run_id>-<attempt>.json` schema (via `collect()`, lines ~155-222)

```python
def collect(evidence, run, jobs):
    repository = run["repository"]["full_name"]
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("Invalid repository")
    run_id = int(run["id"])
    attempt = int(run.get("run_attempt", 1))
    record: dict[str, Any] = {
        "schema": 1,
        "repository": repository,
        "run_id": run_id,
        "attempt": attempt,
        "run_number": run.get("run_number"),
        "workflow": run["name"],
        "sha": run["head_sha"],
        "url": f"https://github.com/{repository}/actions/runs/{run_id}/attempts/{attempt}",
        "date": run["created_at"],
        "conclusion": run.get("conclusion") or "in_progress",
        "jobs": [
            {
                "name": job["name"],
                "conclusion": job.get("conclusion") or job.get("status"),
                "steps": [
                    {"name": step["name"], "conclusion": step.get("conclusion") or step.get("status")}
                    for step in job.get("steps", [])
                ],
            }
            for job in jobs["jobs"]
        ],
        "tests": None,
        "evaluation": None,
        "load": None,
        "context": {},
        "data_issues": [],
    }
    for key, loader, folder in [
        ("tests", junit_totals, "offline-test-evidence"),
        ("evaluation", evaluation_totals, "evaluation-evidence"),
        ("load", load_totals, "load-test-evidence"),
    ]:
        try:
            record[key] = loader(evidence / folder)
        except (ValueError, KeyError, TypeError, AttributeError, ET.ParseError):
            record["data_issues"].append(f"Invalid {key} evidence; measurement withheld")
    # context (dataset/evaluator SHA-256, judge_deployment, environment, agent_version, version_after)
    # is read from evaluation-evidence/context.json or load-test-evidence/context.json, restricted to
    # a fixed allow-list of keys (see full excerpt below).
    ...
```

Exact allow-listed `context` keys (lines ~207-215): `environment`, `agent_version`, `agent_content_hash`, `dataset_sha256`, `evaluator_sha256`, `judge_deployment`, `version_after`.

Load-timing withholding rule (lines ~217-222): if `context.agent_version` is falsy, or `context.version_after != context.agent_version` (i.e. the routed staging version changed between capture and the load probe), **latency numbers are nulled out** even though the raw load record still exists — "Staging route was not stable or could not be verified; load timings withheld" is appended to `data_issues`.

### Outputs — the exact `Continuous-Test-Trends.md` sections `render_trends()` produces

`render_trends(records)` (lines ~245-345) builds, in order: front-matter (`title`, `description`), "## Scope" (prose caveats — always-present, static), "## Recent Runs" (table, latest 50 attempts, columns: Run/attempt, UTC, Workflow outcome, Test SHA, Agent version, Tests pass/fail/skip, Captures/policy failures, Load success/errors, p50/p95), "## Test Suite Growth" (a table of `test_counts()` per run, plus one `chart()` mermaid block per count-type), "## Test Failures" (one `chart()` of JUnit failures), "## Evaluation Trends" (grouped by `(dataset_sha256, evaluator_sha256, judge_deployment, environment)` tuple — a new "### Dataset <hash> / evaluator <hash>" subsection per unique lineage group, with one `chart()` per metric in `METRICS`), "## Load Latency" (p50/p95 charts, restricted to `requested_count == 5`, `contract == "completed-text-v2"`, `environment == "staging"`), "## Reporting Gaps" (bullet list of every `data_issues` entry across all shown records, or a reassuring "No malformed-evidence..." line if empty).

`chart(title, samples, axis)` (lines ~226-235) — the exact mermaid block shape:

```python
def chart(title, samples, axis):
    if not samples:
        return f"No valid measurements yet for {title}.\n"
    samples = samples[-12:]
    labels = ", ".join(f'"{run_label(record)}"' for record, _ in samples)
    values = ", ".join(str(round(value, 3)) for _, value in samples)
    maximum = 100 if axis == "pass percent" else max(1, math.ceil(max(value for _, value in samples)))
    return (
        f'```mermaid\nxychart-beta\n  title "{title}"\n  x-axis [{labels}]\n'
        f'  y-axis "{axis}" 0 --> {maximum}\n  bar [{values}]\n```\n'
    )
```

Uses `xychart-beta` with a **bar** chart (not a line chart), auto-scaled y-axis (0-100 for percent axes, `ceil(max(value))` for count/seconds axes), always limited to the last 12 available (non-missing) samples, x-axis labels from `run_label()` (`"R<run_number>.<attempt>"` for release/CD workflows, `"V<run_number>.<attempt>"` for validation workflows — prefix chosen by `record["workflow"].startswith("Deploy") or record["workflow"] == "Hosted Agent CI/CD"`).

### `publish_history(record, wiki)` — lines ~347-361 (verbatim — the actual file-write contract)

```python
def publish_history(record, wiki):
    directory = wiki / "trend-history"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{record['run_id']}-{record['attempt']}.json"
    previous = read_json(target)
    if previous:
        record = dict(record)
        for key in ("tests", "evaluation", "load"):
            if record.get(key) is None:
                record[key] = previous.get(key)
        record["context"] = {
            key: record["context"].get(key) or value for key, value in previous["context"].items()
        } | {key: value for key, value in record["context"].items() if value is not None}
    target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    records = [read_json(path) for path in sorted(directory.glob("*.json"))]
    (wiki / "Continuous-Test-Trends.md").write_text(render_trends(records), encoding="utf-8")
```

Two important behaviors: (1) the per-run JSON file is **named `{run_id}-{attempt}.json`** — matches the example file `34424741660-1.json` read in Section E; (2) re-publishing the **same** `(run_id, attempt)` **merges** rather than overwrites — any `None` field in the new record is backfilled from the previous file's value for that same key, and `context` is merged key-by-key preferring the new non-null value. This lets a later job in the same run (e.g. a load-test job that finishes after the trend-publish workflow already ran once) patch in data without clobbering fields collected earlier. `Continuous-Test-Trends.md` itself is **fully regenerated** from **all** JSON files in `trend-history/` every time (not incrementally appended).

### `main()` CLI surface — lines ~363-400 (three distinct modes)

- `--context [--version-after VALUE | --agent-state PATH | --agent-version VALUE] --dataset PATH`: writes/patches `context.json` (dataset/evaluator SHA-256 + `judge_deployment` from `JUDGE_DEPLOYMENT` env var).
- `--load PATH`: prints a `## Load Probe Measurements` step-summary snippet from `load_totals`.
- `--junit PATH`: prints a `## Offline Test Results` step-summary snippet (bullet list + a by-type table) from `junit_totals`.
- else (`--evidence --run --jobs [--output] [--wiki]`): the full `collect()` -> `record.json`/`summary.md` -> (if `--wiki` given) `publish_history()` path — this is the mode a `publish-test-trends.yml`-equivalent workflow must call, supplying `--run`/`--jobs` as **files** containing the `gh api .../actions/runs/<id>` and `.../actions/runs/<id>/jobs` JSON responses, `--evidence` as the directory the downloaded artifacts were extracted into, and `--wiki` as the checked-out wiki clone's local path.
- Every mode's `text` output is both `print()`-ed and appended to `$GITHUB_STEP_SUMMARY` if that env var is set.

## D. `scripts/build-release-evidence.js` (sibling) — full read, purpose confirmed one-off

File: `foundry-hosted-agents/scripts/build-release-evidence.js` (~45 lines, full read).

- **Hard-codes** a specific historical run: `const runId = '34178081808'` and asserts exact values throughout (`workflow.head_sha === 'f3da486497450d24d540c994839db2876936d22a'`, `production.version === '34'`, `previous.version === '33'`, `identity.version === '6'`, `jobs.length === 8`, `captured.length === 8`, `results.items.length === 7`, specific case IDs `['tp-001','fp-001','amb-001','miss-001','conflict-001','unauth-001','unsup-001']`, an exact refusal message string for `inject-001`, `receipts.length === 28`, etc.).
- Purpose: renders a **static, styled HTML "verified release" evidence page** (`assets/release-evidence/index.html`) from a fixed set of captured artifacts (`captured.json`, `results.json`, `candidate-policy.json`, `run-identity.json`, `prod-agent-show(.before).json`) plus live `gh api`/`gh run view --log` calls (only under its own `--capture` CLI branch) to fetch the workflow/jobs metadata and a specific monitoring-log line for that one run. It also emits a `manifest.json` with SHA-256 hashes of every captured evidence file.
- **Not invoked anywhere in `deploy-and-evaluate.yml`** (confirmed by grep/read — no reference to `build-release-evidence.js` or `build-deck.js`/`release-slides.js` in that workflow). It is a manual, human-run reporting tool for producing a one-off polished HTML artifact for a specific past release, hard-asserting metric names (`coherence`, `groundedness`, `task_adherence`) and case counts that are **specific to that historical run**, not a generic templating engine.
- Confirms the target repo's Planning Log characterization ("reference only, not a direct port") is accurate: it is neither parametrized nor wired into any workflow, and every assertion would need to be rewritten per-run if reused, which defeats the purpose of an automated trend page. It is unrelated to `Continuous-Test-Trends.md`/`trend-history/` (those are produced by `ci_results.py`, not this script).

## E. `trend-history/34424741660-1.json` (sibling wiki) — exact schema

File: `foundry-hosted-agents-wiki/trend-history/34424741660-1.json` (full read). This is the literal on-disk shape `ci_results.py`'s `collect()`/`publish_history()` produce (Section C), for a real `"Deploy and Evaluate (Staging -> Production)"` run.

Top-level keys, in file order: `schema` (int, `1`), `repository` (string, `"devopsabcs-engineering/foundry-hosted-agents"`), `run_id` (int), `attempt` (int), `run_number` (int), `workflow` (string, e.g. `"Deploy and Evaluate (Staging -> Production)"`), `sha` (full 40-char git SHA string), `url` (string, `https://github.com/<repo>/actions/runs/<run_id>/attempts/<attempt>`), `date` (ISO-8601 UTC string, e.g. `"2026-09-10T01:15:30Z"`), `conclusion` (string, e.g. `"success"`), `jobs` (array — see below), and (not visible in the first 400 lines read, but per Section C's `collect()` source, present later in the same file) `tests`, `evaluation`, `load`, `context`, `data_issues`.

`jobs` array shape (verbatim from the file, one job shown fully):

```json
{
  "name": "Lint, unit tests, dependency scan",
  "conclusion": "success",
  "steps": [
    { "name": "Set up job", "conclusion": "success" },
    { "name": "Checkout repository", "conclusion": "success" },
    { "name": "Set up Python", "conclusion": "success" },
    { "name": "Install lint and test tooling (CI-only; not part of the runtime image)", "conclusion": "success" },
    { "name": "Ruff check (evaluation suite; see ruff.toml for scope rationale)", "conclusion": "success" },
    { "name": "Agent graph unit tests", "conclusion": "success" },
    { "name": "Deterministic evaluation checks (must fail on the injected bad example)", "conclusion": "success" },
    { "name": "Reporting and workflow contract tests", "conclusion": "success" },
    { "name": "Responses contract validator regression tests", "conclusion": "success" },
    { "name": "Runtime role assignment regression tests", "conclusion": "success" },
    { "name": "Production version discovery regression tests", "conclusion": "success" },
    { "name": "Publish offline test summary", "conclusion": "success" },
    { "name": "Retain offline test measurements", "conclusion": "success" },
    { "name": "Post Set up Python", "conclusion": "success" },
    { "name": "Post Checkout repository", "conclusion": "success" },
    { "name": "Complete job", "conclusion": "success" }
  ]
}
```

The file contains one such object per job in the run (`Lint, unit tests, dependency scan`; `Bicep validate and what-if`; `Deploy immutable candidate to staging`; `Smoke, contract, and streaming tests`; `Offline evaluation quality gate`; `Promote to production`; `Post-deploy monitoring check`) — matching `collect()`'s literal `job["name"]`/`job.get("conclusion") or job.get("status")` mapping straight from the GitHub Jobs API, including every auto-generated `Post <step>`/`Set up job`/`Complete job` bookkeeping step GitHub Actions itself adds. Per Section C's `collect()` code, the remaining top-level fields (not shown in the first 400 lines read but structurally guaranteed by the source) are: `tests` (object or `null`, shape per `junit_totals()`), `evaluation` (object or `null`, shape per `evaluation_totals()`), `load` (object or `null`, shape per `load_totals()`), `context` (object, allow-listed keys: `environment`, `agent_version`, `agent_content_hash`, `dataset_sha256`, `evaluator_sha256`, `judge_deployment`, `version_after`), `data_issues` (array of strings).

## F. Target repo's own workflows (`continuous-validation.yml`, `hosted-agent-cd.yml`, `deploy-and-evaluate.yml`, `publish-test-trends.yml`) — current state

### `continuous-validation.yml` (full read, 2 jobs: `offline`, `bicep-lint`)

- Header comment explicitly states: "No Azure credentials are used anywhere in this file... while Gates G2, G3, and G6 remain open."
- `offline` job: installs deps, runs `pytest apps/workshop/tests mcp/application-server/tests mcp/rulebook-server/tests src/quote-preparation-agent/tests eval -v --junitxml=evidence/tests.xml` (**one combined JUnit file**, not per-suite files like the sibling), then `python eval/evaluation_gate.py`, then a step named **"Offline test summary"** that writes a static (non-data-driven) block to `$GITHUB_STEP_SUMMARY`:
  ```yaml
  - name: Offline test summary
    if: always()
    run: |
      {
        echo '## Continuous Validation (offline)'
        echo ''
        echo 'Full pytest sweep and deterministic evaluation gate results are above.'
        echo 'No staging deployment or Azure credential is used in this workflow.'
      } >> "$GITHUB_STEP_SUMMARY"
  ```
  This is the **only** `$GITHUB_STEP_SUMMARY` write in this workflow — it does not surface pass/fail counts, timing, or the evaluation-gate's actual JSON results (`eval/results.json`) even though that file is uploaded as an artifact in the very next step.
- `bicep-lint` job: `az bicep install` then `az bicep build` on every `infra/*.bicep`/`infra/modules/*.bicep` file (compile-only, no login, no apply) — no step summary at all.

### `hosted-agent-cd.yml` (full read, trivial)

Entirely a `workflow_dispatch`-only banner + `uses: ./.github/workflows/deploy-and-evaluate.yml` with `secrets: inherit`. No steps of its own, hence **no** `$GITHUB_STEP_SUMMARY` content originates here (whatever `deploy-and-evaluate.yml` writes flows through as the called workflow's own summary).

### `deploy-and-evaluate.yml` (target; full read — not explicitly requested in task F but essential context for Section 1 of Consolidated Findings)

- Carries the same "AUTHOR-ONLY / DO NOT DISPATCH UNTIL GATES CLEAR" banner as `hosted-agent-cd.yml`, plus an explicit comment block stating this repo's `evaluation_gate.py` "is fully deterministic and local — it does not call an LLM judge or a live agent endpoint, unlike the sibling's `run_hosted_evaluation.py` / `check_conversation.py`," and that there is "no live-invocation smoke-test harness... no `scripts/invoke-agent.sh` or equivalent."
- 5 jobs: `lint` (pytest + `eval/evaluation_gate.py`), `bicep-validate` (what-if only), `deploy-staging` (`azd provision`/`azd deploy`, no MCP-image-digest what-if step for a live smoke test), `evaluate` (**literally just re-runs** `python eval/evaluation_gate.py` a second time and calls it "Deterministic evaluation gate (release quality control)" — no endpoint/judge/deployment involvement at all), `promote-production` (manual-approval-gated via the `production` GitHub Environment, then `azd deploy`).
- **Zero** `$GITHUB_STEP_SUMMARY` writes anywhere in this file (confirmed by full read — no `GITHUB_STEP_SUMMARY` string appears).
- No rollback/`post-deploy-monitoring`/`recovery-required` jobs exist yet in the target (unlike the sibling's Stages 7-8) — promotion ends at `promote-production` with no automated post-deploy health check.

### `publish-test-trends.yml` (target; full read — already exists, already adapted, already documents the gap)

This file **already exists** in the target repo (contrary to an assumption that it must be created from scratch) and its own header comment is unusually candid about the current gap:

```yaml
# Adapted from the sibling repository's publish-test-trends.yml, but
# significantly simplified (Implementation Phase 11, Step 11.4). The
# sibling's version depends on two custom reporting scripts
# (scripts/ci_results.py, scripts/deployment_summary.py) and pushes an
# aggregate history to the repository wiki via a WIKI_PUSH_TOKEN secret.
# Neither the reporting scripts nor a wiki-push requirement exists in this
# repository; inventing them was out of scope for this phase. This version
# instead downloads whatever evidence artifacts the source run produced and
# writes a plain job summary via $GITHUB_STEP_SUMMARY, retaining the
# collected evidence as a single consolidated artifact.
```

Current behavior: triggers on `workflow_run` completion of `[Continuous Validation, 'Deploy and Evaluate (Staging -> Production)', Hosted Agent CI/CD]` on `main`, or manual dispatch with a `run_id` input; downloads **every** artifact from the source run by name (via `gh api .../artifacts` + `gh run download`) into `evidence/<name>/`; writes a generic 4-line `## Test Trends` block naming the source run and stating "This repository has no aggregate trend-history script or wiki publication step"; re-uploads everything as one `test-trends-evidence-<run>` artifact. **No `trend-history/` folder, no wiki checkout/push, no `Continuous-Test-Trends.md` generation, and no parsing of `eval/results.json` or JUnit XML content** happens today — it is a pure artifact-passthrough placeholder.

## G. Target `eval/golden-dataset.jsonl` — no LLM-judge-shaped fields today

First 10 records read in full (`biz-001-calc-compact-ready` through `fault-004-forged-actor-approve-before-submit`). Every record's schema is: `id`, `category`, `check_type` (`calculator` | `agent` | `approval_repository`), `dataset_version`, `reviewed_by`, one of `fixture_id`/`case_id`/`scenario`-specific keys, `description` (`{"en-CA": ..., "fr-CA": ...}` bilingual pair), and `expected` (a **structured dict** whose shape varies by `check_type` — e.g. `{"status": "READY", "amountCents": 100000, "issues": []}` for `calculator`, `{"raises": "SelfApprovalError", "final_state": "PENDING_REVIEW", ...}` for `approval_repository`).

**There is no `query`, `response`, `context`, or `input.messages` field anywhere in this dataset** — it is a pure deterministic fixture/expectation table for direct function-level testing (calculator math, approval-repository state machine, and the agent graph's structured output), consumed by `eval/deterministic-tests/checks.py` (per `evaluation_gate.py`'s own docstring, Section F). This is structurally incompatible, as-is, with the sibling's `run_hosted_evaluation.py --dataset` contract, which expects `{"data": [{"id", "query", "context", ...}]}` records with a natural-language `query` string (compare to the sibling's own `eval/golden-dataset.jsonl` record shape confirmed in Section J: `{"id": "tp-001", ..., "input": {"messages": [{"role": "user", "content": "<free text>"}]}, "expected": {...}}` — the sibling's `convert_for_ai_agent_evals.py` derives `query` from the last `role: user` message in `input.messages`, and sets `context` to the **same string as `query`**, not a separate ground-truth document).

**Implication**: adding LLM-judge evaluation to the target repo requires either (a) a **new, separate** natural-language dataset (distinct from `golden-dataset.jsonl`, which must stay deterministic-only since `deterministic-tests/checks.py` depends on its exact current shape), or (b) extending each golden-dataset record with additive `query`/`context` fields the deterministic checks simply ignore. Given the target dataset is also bilingual (`en-CA`/`fr-CA` `description`), a judge-ready dataset would plausibly need a `query` per locale too, which the sibling's dataset does not need to handle (sibling is English-only).

## H. Target `src/quote-preparation-agent` — no system-prompt constant exists yet

Full read of `graph.py` (through the `composition_node` body) plus targeted `grep` for `PROMPT|instructions =|SYSTEM_PROMPT` across the whole `src/quote-preparation-agent` tree: **zero matches** for any prompt-like constant. The only match at all was `default_model`'s own docstring text ("Deterministic, network-free fallback model callable...").

Confirmed from `graph.py`'s module docstring and `default_model()`'s docstring (verbatim):

```python
def default_model(prompt: str) -> str:
    """Deterministic, network-free fallback model callable.

    Returns a fixed acknowledgement derived only from `prompt`'s own text
    (no external call), so building the graph with no injected `model`
    never requires network access, credentials, or a live LLM deployment.
    This is the seam the sibling fills with an Azure OpenAI/LangChain chat
    model; tests inject a stub callable here to prove it is swappable
    without ever making a network call in this phase.
    """
    return f"[offline-default-model] {prompt}"
```

`build_graph(*, repository=None, model=None)` accepts an injectable `model: ModelCallable` (a plain `Callable[[str], str]`), defaulting to `default_model` — **there is no real LLM call anywhere in this phase's code path**, and consequently **no system-prompt string exists to extract** via an `agent_instructions()`-style AST parse (unlike the sibling's `REPORT_COMPOSER_PROMPT` constant in its `graph.py`). `state.py`'s module docstring corroborates: "this project has no Foundry Responses protocol and no hosted session... the compiled graph in `graph.py` always runs without a checkpointer." `main.py`'s module docstring: "No Azure/Foundry SDK calls and no hosted-agent deployment code exist in this module... Hosted deployment... is out of scope until Gates G2/G3/G6 are cleared in a later phase."

`azure.yaml` (target) **does** declare a model deployment for the *hosted* agent (once deployed): `deployments: [{name: gpt-4o-mini, model: {name: gpt-4o-mini, format: OpenAI, version: "2024-07-18"}, sku: {name: GlobalStandard, capacity: 10}}]` under the `ai-project` service, and the `quote-preparation-agent` service's `environmentVariables` set `AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini` / `AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini`. **This is the same single deployment name the sibling's pattern would reuse as the judge deployment** (see Section B's `JUDGE_DEPLOYMENT: ${{ vars.FOUNDRY_MODEL_NAME }}` finding) — i.e. a target-repo port would plausibly set a repo variable `FOUNDRY_MODEL_NAME=gpt-4o-mini` (or reuse an equivalent) rather than provisioning a second, judge-only deployment, **once the agent is actually hosted**. Until then, there is no endpoint to evaluate against at all.

**Consequence for `task_adherence`**: a real judge pipeline needs *some* system-prompt-equivalent text to feed as `task_query`'s system message. Since none currently exists in code, any port must either (a) add a real instructions string to the agent once one exists (post-hosting), or (b) synthesize a placeholder task description from `graph.py`'s own module docstring/`decide_next_step` routing description for now, clearly labeled as a stand-in, not a verified system prompt.

## I. Target wiki (`C:\temp\fsi-wiki`) — existing content that references test trends today

### `Workflows.md` (full read)

Already documents `publish-test-trends.yml` in its workflow table: *"Downloads evidence artifacts from a completed run and writes a job-summary trend report. Does not push to the wiki (unlike the sibling repository's version)."* Also has an explicit note: *"Unlike the sibling `foundry-hosted-agents` repository, this repository's evaluation gate (`eval/evaluation_gate.py`) is fully deterministic and local — it does not call an LLM judge or a live agent endpoint..."* — this sentence would need to be **updated/removed** once real judge evaluation code is added (even if still gated/non-executing), to avoid the wiki becoming stale/inaccurate. The "Release path" mermaid diagram currently shows only `Eval[Deterministic evaluation gate]` as one box — a judge stage would need to be reflected there too (or explicitly marked "gated, not yet executable").

### `Home.md` (full read)

No direct mention of test trends or a `Continuous-Test-Trends.md` link in the "Pages" bullet list (`Workflows`, `Architecture`, `Operations`, `Release-Evidence` only — no "Test Trends" entry exists yet). Adding the new page requires **both**: (1) creating `Continuous-Test-Trends.md`, and (2) adding a `* [Test Trends](Continuous-Test-Trends): ...` bullet to `Home.md`'s "Pages" list, and (3) per the repo's own convention (`_Sidebar.md` was previously updated in this same effort per session memory), adding the equivalent entry to `_Sidebar.md` too (not read in this pass, but its existence and prior-update pattern is established in session memory: "`_Sidebar.md`/`Workflows.md`" were both updated together in Phase 4).

## J. Sibling `check_conversation.py`, `convert_for_ai_agent_evals.py`, `rubrics/` — purpose summary

### `eval/check_conversation.py` (full read)

A **separate, non-judge** live regression check: verifies conversation-history behavior against the deployed hosted endpoint directly via `urllib` (not through the Evaluation SDK at all) — three assertions: (1) a fresh conversation retains a synthetic reference string in the first response, (2) a **follow-up message reusing the same history** still recalls that reference, (3) an **independent** (fresh) conversation does **not** leak the reference from the prior one. Validates the endpoint URL shape strictly (`https://*.services.ai.azure.com`, optionally pinned to a `aif-fha-learn-*` workshop account, else must contain `-staging`). Reuses `run_hosted_evaluation.completed_response()` to parse the SSE stream. Writes a step-summary block itself (`## Conversation Regression`) independent of `ci_results.py`. **Not relevant to judge-metric wiring** — it is a conversation-isolation/session-safety regression test, not an LLM-as-judge evaluator. Would only be portable to the target repo once the target has an actual hosted Responses-protocol endpoint (it does not today).

### `eval/convert_for_ai_agent_evals.py` (full read)

A **read-only, additive** format-conversion shim: turns `eval/golden-dataset.jsonl` (one JSON object per line, sibling's real shape confirmed: `{"id", "category", ..., "input": {"messages": [{"role": "user", "content": "<text>"}]}, "expected": {...}}`) into the JSON envelope the (external) `microsoft/ai-agent-evals` GitHub Action / `run_hosted_evaluation.py --dataset` argument expects: `{"name": ..., "evaluators": ["builtin.coherence", "builtin.groundedness", "builtin.task_adherence"], "data": [{"id", "query", "context", "expected"}, ...]}`. Its own module docstring explicitly flags that **`context` is set to the same value as `query`** (`data.append({"id": identifier, "query": query, "context": query, "expected": record["expected"]})`) — confirming the Section A note that "groundedness" here checks against the user's own restated input, not an independent knowledge source. Also explicitly notes the richer per-category rubric overrides in `evaluator-mapping.yaml` are **not yet wired in** ("tracked as follow-on work") — only the flat `default_evaluators.built_in` list is used by this converter today.

### `eval/rubrics/` folder (4 files, `evaluator-mapping.yaml`/`README.md` read in full, `conflict-handling.rubric.yaml`/`evidence-citation.rubric.yaml`/`triage-correctness.rubric.yaml` not opened but referenced by name)

`README.md` frames the whole directory as **"built-in evaluators first, custom rubrics only where needed"** — a mapping table showing which of the sibling's gating criteria (schema validity, citation presence, tool-call policy = deterministic; coherence/groundedness/task_adherence/tool_call_accuracy = **built-in** Foundry evaluators; triage correctness / evidence-citation quality / conflict-handling = **custom rubric files**). Its own "Status" section is explicit that this is **aspirational/unverified**: *"These rubric definitions describe the intended evaluator configuration. The exact `azure-ai-projects` evaluator registration call and the precise `microsoft/ai-agent-evals@v3-beta` action inputs for wiring custom rubrics alongside built-in evaluators are not yet independently verified in this repository... Treat these files as the authored specification to validate against a live Foundry project in Phase 7, not as an already-proven pipeline."*

`evaluator-mapping.yaml` structure: `schema_version`, `default_evaluators.built_in` (3 built-ins) + `default_evaluators.custom_rubrics` (list of rubric filenames), `category_overrides.<category>` (per golden-dataset `category` value, override `built_in`/`custom_rubrics` — e.g. `prompt_injection` category **drops `groundedness`** entirely with an inline comment explaining why: "Groundedness is less meaningful for an injection attempt with no real incident evidence"), and a top-level `tool_call_accuracy` block (`builtin.tool_call_accuracy`, gated by an `applies_when` expression referencing per-specialist `tool_unavailable` flags).

**Relevance to the port**: `convert_for_ai_agent_evals.py` is directly relevant/portable in spirit (same conversion problem exists for a target-repo natural-language judge dataset, once one exists) but **not directly runnable as-is** — it hard-codes the envelope's `"name"` to `"threat-assessment-agent-golden-dataset"` and assumes `input.messages`, neither of which match the target's current `golden-dataset.jsonl` shape (Section G). `check_conversation.py` is not needed until the target has a real hosted endpoint. The `rubrics/` folder's **pattern** (per-category evaluator selection driven by a mapping file, explicit "not yet verified" status marker) is a good template to imitate for the target repo's own future rubric mapping, but the target has no equivalent categories defined yet and its own dataset does not carry a `category` value shaped for this (target categories are `business_ready`/`business_incomplete`/`business_invalid_reference`/`fault_unsupported_input`/`fault_self_approval`/`fault_forged_actor`, not the sibling's triage categories) — a fresh mapping would need to be authored, not copied.

## Consolidated Findings

### 1. Net-new code/config for real LLM-judge evaluation, AUTHOR-ONLY/gated

To reach parity with the sibling's `coherence`/`groundedness`/`task_adherence` judge pipeline while staying consistent with this repo's existing gating convention (banner comments + `workflow_dispatch`-only + Gate G2/G3/G6 sign-off), the following would be net-new:

- **A judge-ready natural-language dataset.** `eval/golden-dataset.jsonl` cannot be repurposed as-is (Section G) — it has no `query`/`context`/`input.messages` shape and is load-bearing for `deterministic-tests/checks.py`. A new file (e.g. `eval/judge-dataset.jsonl`, bilingual `query`/`expected` pairs) would be required, or additive `query_en`/`query_fr` fields bolted onto existing records with a converter that the deterministic checks continue to ignore.
- **A real system-prompt/instructions constant** in `src/quote-preparation-agent/graph.py` (Section H) — today there is none; `task_adherence` has nothing to AST-extract. This is itself a prerequisite feature (giving the agent an actual LLM-driven `model` instead of `default_model`), which is presumably still pending Gate clearance and/or a later implementation phase, not just an eval-pipeline change.
- **`eval/run_hosted_evaluation.py`-equivalent script**, adapted: swap `agent_instructions()`'s hard-coded sibling path/constant name for the target's real prompt constant (once it exists); swap `capture()`'s dependency on `scripts/invoke-agent.sh` for whatever this repo's hosted-invocation mechanism ends up being (none exists today — no Responses-protocol smoke harness); keep `criteria()`/`validate_results()`/the `evals.create`/`evals.runs.create` polling loop essentially as-is (it is domain-agnostic).
- **`eval/evaluation_gate.py` changes are NOT required** — the target's gate is intentionally kept deterministic-only per its own docstring; the judge script should import `METRICS`/`validate_results` the same way the sibling does, or (cleaner) define its own small `judge_gate.py` sibling module so the deterministic gate's docstring claim ("there are no quality judges in this deterministic gate at all") stays true and auditable.
- **Dependency additions**: `azure-ai-projects==2.6.0`, `openai==3.6.0`, `azure-identity==1.25.3` (exact sibling pins, Section B) added to a CI-only install step (not the runtime `requirements.txt`, matching the sibling's pattern of installing eval SDKs only inside the `evaluate` job).
- **A judge model deployment reference** — reuse the existing `gpt-4o-mini` deployment name already declared in `azure.yaml` (Section H) as both the agent's model and the judge's `--deployment` argument, mirroring the sibling's single-deployment reuse (Section B) — no second Foundry model deployment is structurally required.
- **Workflow wiring**: a new step (or new job) in `deploy-and-evaluate.yml`'s `evaluate` stage, but it can only ever *execute* once (a) the agent is actually hosted with a real project endpoint and (b) a live-invocation harness exists — so this step must itself carry a runtime guard/no-op path (e.g. `if: false` or an explicit "not yet available" early-exit with a clear message) until those prerequisites land, consistent with the whole file's existing "AUTHOR-ONLY / DO NOT DISPATCH" banner. It should not be wired to actually run against Azure until Gates G2/G3/G6 clear **and** the hosting/instructions prerequisites above are independently satisfied.

### 2. `Continuous-Test-Trends.md` + `trend-history/` + updated `publish-test-trends.yml` that works TODAY with only deterministic data

This is achievable now, without fabrication, because the target already has real, executing signal: `eval/results.json` (from `evaluation_gate.py`, Section F), one combined JUnit file (`evidence/tests.xml` in `continuous-validation.yml`, `offline-evidence/tests.xml` in `deploy-and-evaluate.yml`), and real GitHub Actions run/job metadata via `gh api`.

- **Port a trimmed `ci_results.py`** (new script, e.g. `scripts/ci_results.py` in the target) implementing only: `junit_totals()` (adapted `by_type` mapping — target has one combined `tests.xml`, so `by_type` collapses to a single "Offline tests" bucket unless/until the target splits JUnit output per suite the way the sibling does), a **deterministic-gate totals function** (new; reads `eval/results.json`'s actual schema — `dataset_size`, `records[].passed`, `bilingual_parity.passed`, `passed` — Section F's `evaluation_gate.py` excerpt — not the sibling's `evaluation_totals()`, which expects `captured.json`/`results.json`/`run-identity.json` that don't exist in this repo), `collect()`/`publish_history()`/`render_trends()`/`chart()` largely as-is (they are domain-agnostic given the right input shape), with a `judge` section per run that is **always `null`/omitted with an explicit "not yet available (pending deployment gate clearance)" note** rather than invented data, until Section 1's judge pipeline exists and actually executes.
- **`trend-history/` folder**: create it under `C:\temp\fsi-wiki\trend-history\` (mirroring the sibling's `<run_id>-<attempt>.json` naming and schema — Section E), seeded by real completed runs of `continuous-validation.yml` (the only workflow that currently runs unattended/automatically and produces real evidence — `deploy-and-evaluate.yml`/`hosted-agent-cd.yml` cannot run for real yet since they're gated).
- **`Continuous-Test-Trends.md`**: generate via the ported `render_trends()`, but the "## Evaluation Trends" section (judge pass-rate charts) should render its existing "No comparable evaluation lineage has been collected yet." fallback (Section C already has this exact fallback string built in) until judge data exists — no code change needed there beyond ensuring `judge_rates`/`evaluation` stay `null` for every real run today. The "## Recent Runs" / "## Test Suite Growth" / "## Test Failures" sections work today from `continuous-validation.yml`'s JUnit output and `evaluation_gate.py`'s deterministic pass/fail record counts alone.
- **Updated `publish-test-trends.yml`**: replace the current placeholder (Section F) with a real invocation of the ported `ci_results.py --evidence ... --run ... --jobs ... --wiki ...` after downloading the source run's `offline-test-evidence-*`/`evaluation-evidence-*` artifacts and fetching `gh api .../actions/runs/<id>` + `.../jobs` payloads, then a wiki checkout/commit/push step gated behind a **new** `WIKI_PUSH_TOKEN`-equivalent secret (this secret does not exist yet in the target repo and must be provisioned — see Open Questions below) — this part is safe to wire and run for real today (it only touches the wiki repo, not Azure), independent of the Gate G2/G3/G6 Azure-deployment gate.

### 3. "Richer GitHub workflow summaries" per existing target workflow

- **`continuous-validation.yml`**: replace the static "Offline test summary" block (Section F) with a data-driven one — parse `evidence/tests.xml` (pass/fail/skip counts, total duration) and `eval/results.json` (`dataset_size`, per-category pass counts, `bilingual_parity.passed`) directly in a small step (or the ported `ci_results.py --junit`/a new `--gate-results` mode) and write real numbers plus a link to the uploaded artifacts, instead of the current placeholder sentence. Add a summary step to the `bicep-lint` job too (currently has none) — e.g. which `.bicep` files were built and confirmation of zero diagnostics.
- **`hosted-agent-cd.yml`**: no changes needed to its own summary (it has no steps of its own); ensure the *called* `deploy-and-evaluate.yml`'s summaries (below) are rich enough that this thin wrapper's run page is still informative.
- **`deploy-and-evaluate.yml`**: currently has **zero** `$GITHUB_STEP_SUMMARY` writes (Section F) despite being the highest-stakes workflow in the repo. Add per-job summaries mirroring the sibling's pattern (Section A's `capture_summary()`/`evaluate()` `summary.md` blocks): a "Deployed candidate version" line in `deploy-staging`, a "Deterministic evaluation gate (release quality control)" results table in `evaluate` (dataset size / passed / failed categories, linking `eval/results.json`), and a "Promoted `<previous> -> <new>` agent version" line in `promote-production`. Since this workflow cannot actually be dispatched until gates clear, these summary improvements are code that can be written and reviewed now but will only produce real output the first time the workflow is actually run post-gate-clearance — the PR/commit adding them should be explicit that they are untested against a live run.
- **`publish-test-trends.yml`**: once updated per Consolidated Finding 2, its summary should report exactly what real trend data was published (run/attempt, whether judge data was available or marked pending, links to the updated wiki page) rather than the current generic "This repository has no aggregate trend-history script..." placeholder text, which will become stale/inaccurate the moment the port lands and must be removed as part of the same change.

## Critical blockers / open questions before an implementation plan can be written

1. **No hosted endpoint exists.** All of Section 1's judge-wiring work is necessarily inert (author-only) until the agent is actually deployed — there is no `scripts/invoke-agent.sh` equivalent, no Responses-protocol server, and `main.py` is explicitly local-only. Any judge-pipeline PR must be reviewed as "correct but untested against a live endpoint," which is a meaningfully different review bar than the sibling's proven code.
2. **No system prompt exists for `task_adherence`.** Wiring `task_adherence` specifically requires a decision: either add a real LLM-driven prompt to `graph.py` first (a functional change beyond eval tooling, and itself presumably gated/out of scope for now), or explicitly scope the initial judge port to `coherence`+`groundedness` only and defer `task_adherence` with a documented reason, diverging from the sibling's three-metric `METRICS` tuple. **This needs a decision from you before planning.**
3. **`golden-dataset.jsonl` cannot be dual-purposed.** A separate judge dataset (or additive fields) must be designed — need to decide: one bilingual dataset with `query_en`/`query_fr`, or two parallel datasets, or reuse `description.en-CA`/`description.fr-CA` text as the query (risk: those are *test-case descriptions*, not applicant-facing conversational input, so may not be representative of what a judge should actually score). **This needs a design decision, not just an engineering port.**
4. **No `WIKI_PUSH_TOKEN`-equivalent secret exists yet** for the target repo (confirmed no such secret referenced anywhere in the four target workflows read). Needs to be provisioned (a PAT or fine-grained token with wiki write access to `foundry-hosted-agents-fsi.wiki.git`) before `publish-test-trends.yml` can actually push — this is independent of the Azure gates and could be done immediately if you want live trend publishing before the agent is hosted.
5. **JUnit output shape mismatch.** The target currently produces **one combined** `tests.xml` per workflow run (`continuous-validation.yml`'s `offline` job, `deploy-and-evaluate.yml`'s `lint`/`evaluate` jobs), not the sibling's five separately-named files (`agent.xml`/`deterministic.xml`/`reporting.xml`/etc.) that `junit_totals()`'s `by_type` mapping depends on for its "Test Suite Growth" breakdown table. Decide whether to (a) split `pytest --junitxml` invocations per test directory to get a meaningful by-type breakdown in the trend page, or (b) accept a single "Offline tests" bucket for now and revisit later.
6. **`deploy-and-evaluate.yml`/`hosted-agent-cd.yml` currently never produce real evidence to trend**, since they're gated and have never run for real — the initial `trend-history/` seeding can only come from `continuous-validation.yml`'s automatic runs (which do execute today on every push/PR to `main`). Confirm this is acceptable as the initial data source, or whether you want `deploy-and-evaluate.yml`'s summary/trend wiring deferred entirely until post-gate-clearance to avoid maintaining dead code paths.

## Recommended next research (not completed this session)

- [ ] Read the sibling's actual `publish-test-trends.yml` verbatim (only its target-repo-adapted derivative and its own header-comment description of the sibling were captured here) to confirm the exact `WIKS_PUSH_TOKEN`-equivalent secret name, the wiki-clone/push step shape, and whether it also calls `scripts/deployment_summary.py` (referenced in `deploy-and-evaluate.yml`'s `lint` job but not opened in this session).
- [ ] Read `scripts/deployment_summary.py` (sibling) — referenced alongside `ci_results.py --junit` in the `lint` job's "Publish offline test summary" step but not opened; may contain additional step-summary conventions worth porting.
- [ ] Read `eval/deterministic-tests/checks.py` (target) in full to confirm the exact `Any`-typed check-result contract `evaluation_gate.py` depends on, in case the judge-dataset design in Open Question 3 needs to add a new check type without disturbing existing ones.
- [ ] Confirm whether GitHub Environment protection (required reviewers) is configured for the target's `production` environment — session memory notes this was still an open item for a *different* concern (promote-production approval gate) but is directly relevant to how "manual production approval" is verified once judge evaluation is wired into the same job.
