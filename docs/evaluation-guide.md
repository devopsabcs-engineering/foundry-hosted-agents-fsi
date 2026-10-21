---
layout: default
title: Evaluating quote agents in Microsoft Foundry
description: A practical evaluation playbook covering deterministic contracts, native model judges, calibration, repeated trials, release gates and operational monitoring.
nav_order: 21
---

[Français](fr/evaluation-guide.md) | [Hands-on Lab 19](labs/lab-19-evaluation-engineering.md) |
[PowerPoint EN](assets/decks/foundry-evaluation-engineering-en.pptx) |
[PowerPoint FR](assets/decks/foundry-evaluation-engineering-fr.pptx)

## Choose the evidence before the evaluator

An evaluation is a measurement against a stated contract, not necessarily an
LLM call. Start with the decision you need to make: is arithmetic correct,
can a preparer approve their own case, does a message invent a price, or did
a model choose a useful tool? These need different oracles.

The deployed quote graph is **deterministic**, not an LLM pricing agent.
`INTAKE`, `REFERENCE_LOOKUP` and `COMPOSITION` use validated fixtures,
read-only MCP, a pure calculator and persisted state. Applicant messages are
bounded bilingual templates. The native **judges** use LLMs; those scores can
vary even when the agent's output does not. Isolated File Search, skills and
memory demonstrations do not become quote-agent dependencies because they
exist in the same Foundry project. See [architecture](architecture.md).

All examples use synthetic, non-binding training data, not actual insurer
rates, customer information, delivery or underwriting decisions.
AI-assisted authoring was used for this training package; learners need no
coding assistant.

| Property | Deterministic contract test | Stochastic evaluation |
| --- | --- | --- |
| Oracle | Exact amount/state, schema, policy predicate | Rubric, human label, model judge or sampled outcome |
| Example | `INCOMPLETE` must have no amount | Does an acknowledgement explain the next step clearly? |
| Repetition | Same controlled inputs/state should reproduce | Samples estimate a distribution; one pass is insufficient |
| Failure meaning | A violated invariant, or a test/infrastructure fault | A measured quality miss, judge disagreement or service fault |
| Appropriate gate | Hard fail for arithmetic, authorization, schema, leakage | Calibrated thresholds, slices, uncertainty and human review |
| Cost | Usually local and fast | Inference, judge calls, latency and retained evidence |

These are not mutually exclusive test frameworks. A unit test can exercise a
stochastic component, and an agent evaluation can use a deterministic code
grader. A live deterministic service can still fail because of RBAC, network,
concurrency or state. Temperature zero and a seed do not guarantee identical
LLM results across model revisions or infrastructure.

## The quote-agent evaluation ladder

| Level | Question and concrete cases | Mechanism | Evidence you must not infer |
| --- | --- | --- | --- |
| 0 | Is data valid? `READY`, `UNSUPPORTED`, `INCOMPLETE`, invalid ID | Fixture/schema and calculator unit tests | A valid schema means an accurate answer |
| 1 | Is the workflow safe? revision/ETag, self-approval, duplicate retry | Store contract and reviewer API tests | An acknowledgement proves persistence or approval |
| 2 | Is the observable response safe? EN/FR, no amount, injection | Deterministic 13-case golden gate and live response checks | Offline mocked transport proves deployment |
| 3 | Is the acknowledgement useful and grounded? five cases per locale | Native coherence, groundedness, task-adherence judges | A high score proves arithmetic or tool correctness |
| 4 | Is the judge trustworthy? wrong approval/price and irrelevant context | Human-labeled positive/negative controls | A fluent answer must be factual |
| 5 | Is quality stable? repeated runs, rare cases, paired baseline/candidate | Frozen data/rubric, per-case scores, uncertainty | Five green cases guarantee no regression |
| 6 | Is the real system safe over time? revision resubmission, role boundaries, traces | Authenticated UI/API, workload probes, telemetry and review | A portal row or requested trace ID proves ingestion |

## Step by step in the Foundry portal

The **new Foundry** portal and the classic experience differ. Exact labels,
available evaluators and preview support depend on project, region and role.
The [official portal guide](https://learn.microsoft.com/azure/foundry/how-to/evaluate-generative-ai-app)
is the navigation authority; do not mix instructions from the two experiences.

1. Open the retained **staging** project at [ai.azure.com](https://ai.azure.com).
   Confirm account/project names and tenant. The `-poc` project is production.
   Do not create resources or grant broad roles to make a lab work.
2. Open the quote agent and inspect the current version and running status.
   Its **Evaluation** tab is visible in the current retained agent UI.
   The documented project-level **Evaluate** flow can also start an evaluation.
3. Choose the right target. An agent target invokes the agent; an uploaded
   response dataset evaluates captured answers. Use captured answers when
   isolating judge variability. Availability of an agent-target flow for a
   hosted/custom agent is a capability check, not a promise.
4. Prepare a small synthetic JSONL or CSV with stable IDs, query, response and
   independent facts/reference fields. The repository's bilingual JSONL is a
   **source format**; convert it before using this repository's SDK runner.
   A portal upload may instead require a flattened response dataset.
5. Map each field explicitly. For groundedness, map trusted `context`, not the
   candidate answer as its own truth. For task adherence, supply task messages
   and compatible response-message content. Select one locale per sample.
6. Select supported evaluators and an existing approved judge-model deployment.
   Inspect the catalog/version and score-to-pass threshold. Not every evaluator
   uses the same scale or the same required fields.
7. Name the run with environment, observed agent version, locale, dataset
   revision and trial number. Save the exact definition/configuration and
   approved cost cap before submitting.
8. Run the small pilot. Wait for a terminal state, then check expected row
   count, errors, skipped rows and every metric. A failed service run is not
   a quality score of zero and is not acceptable missing evidence.
9. Open individual results. Compare low and high scores with human labels,
   inspect reasons, and check deliberately wrong controls. Export results and
   save evaluation/run IDs, source/data hashes and judge configuration.
10. Compare only compatible experiments. If the portal cannot express the
    required mapping, export or repeated-trial design, use the verified SDK
    path below; do not fabricate a portal button or weaken the experiment.

Do not copy tokens, private case details, raw environment settings or connection
strings into uploads, screenshots or source control. Keep evaluation artifacts
under ignored `.local`, with an explicit retention policy.

## Step by step with the repository's native SDK path

Use [Lab 19](labs/lab-19-evaluation-engineering.md) for runnable PowerShell
commands and expected results. The tested release uses `azure-ai-projects`
**2.6.0**, `openai` **3.6.0** and `azure-identity` **1.25.3**. Check the
current [cloud SDK documentation](https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation)
before upgrading; preview contracts can change.

1. Validate and convert `eval/applicant-message-dataset.jsonl` with
   `eval/convert_judge_dataset.py`, once for `en-CA` and once for `fr-CA`.
2. Verify the deployed version before capture. `--version` on
   `eval/run_judge_evaluation.py` is an **observed label, not a routing pin**:
   the native URL invokes the current deployment. Reserve a stable window
   and recheck after capture; reject contaminated runs.
3. Capture real Responses output. The runner rejects HTTP-success error bodies,
   missing answers and missing locale text before invoking a judge.
4. Build independent `evaluation_query` and `task_query` from trusted facts.
   Keep untrusted injection text distinct from trusted instructions.
5. Create an evaluation definition with `AIProjectClient.get_openai_client()`
   and `client.evals.create`. Start a native run with `client.evals.runs.create`.
6. Poll with a bounded timeout, retrieve all output pages and retain the
   complete run/item result. The runner also saves selected-locale captures,
   summary and `run-identity.json`.
7. Validate completeness separately from score thresholds. Inspect service
   error details and correlations before any approved bounded retry.

The actual built-in mapping from the working runner is:

```python
criterion = {
    "type": "azure_ai_evaluator",
    "name": "groundedness",
    "evaluator_name": "builtin.groundedness",
    "initialization_parameters": {"deployment_name": "gpt-4o-mini"},
    "data_mapping": {
        "query": "{{item.evaluation_query}}",
        "context": "{{item.context}}",
        "response": "{{item.response}}",
    },
}
```

This is a configuration excerpt, not a complete standalone submission script.
Do not invent types such as `azure_ai_groundedness`. The working pinned runner
uses `deployment_name`; newer documentation may show `model` or typed wrappers.
Check the installed SDK and the selected evaluator's catalog rather than
combining samples from different versions. Task adherence uses `task_query`
messages and locale-normalized `output_items`, not this text-only mapping.

The run's inline source has this nesting:

```python
data_source = {
    "type": "jsonl",
    "source": {
        "type": "file_content",
        "content": [{"item": {"query": "example", "response": "captured answer"}}],
    },
}
```

Supply the full schema and fields required by your definition; this minimal
shape only explains the envelope. For larger data, follow the supported dataset
upload/file-reference path in the
[dataset guide](https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-datasets).
Do not change `file_content` to `file_id` without creating a valid compatible
project dataset/file reference first.

### Related APIs are not interchangeable

| Surface | Appropriate use | Boundary |
| --- | --- | --- |
| Foundry portal | Exploration, field mapping, human result inspection | Preview capabilities and labels vary |
| Projects SDK + native Evals | Reproducible cloud definitions/runs, CI artifacts | This repository's verified automation path |
| `azure-ai-evaluation` | Local/custom `evaluate()` and evaluator classes | A separate supported API shape; not imported by this runner |
| Code/string graders | Schemas, exact predicates, simple match | Exact text is often a poor semantic metric |
| Prompt/rubric judges | Meaning, grounding, task adherence | Must be calibrated against humans and negative controls |
| Agent/process evaluators | Tool choice, arguments, trajectory and task outcome | Need real compatible trajectory/tool evidence, not only final text |

See [built-in evaluators](https://learn.microsoft.com/azure/foundry/concepts/built-in-evaluators),
[agent evaluators](https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/agent-evaluators)
and [custom evaluators](https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/custom-evaluators).
Registration or a fluent acknowledgement alone is not a process-evaluation pass.

## Build a dataset that can detect a regression

Use a coverage matrix: locale × workflow/calculation status × invalid input ×
injection × lifecycle/revision state × authorization role. Start with the five
applicant cases, then add reviewed edge cases and a separate holdout.

For each row retain stable ID, intended slice, query, independent facts,
expected observable outcome, prohibited behavior, human label and source version.
For workflow tests also retain initial state, actor role, revision and expected
state transition. A synthetic generator proposes test cases; a subject-matter
reviewer must validate their truth and coverage before using them as an oracle.

* Keep development/calibration and holdout sets separate. Do not repeatedly tune
  prompts, thresholds or fixtures against a supposedly unseen release set.
* Add incidents and boundary cases, not only paraphrases of happy paths.
* Test EN and FR separately; an overall mean can hide a French-only regression.
* Keep pricing/schema/authorization checks deterministic even when using an LLM
  to propose new tests.
* Isolate persistent state. Replaying a case can exercise duplicate/lifecycle
  guards rather than first-time intake. Never clear the retained demo queue to
  make evaluation easy. Use an owner-approved disposable test store for stateful
  experiments; record the snapshot or setup/reset procedure.

## Calibrate judges before trusting them

Human-label a small challenge set containing valid acknowledgements, false
approvals, premium leakage, unsupported invented facts, missing disclaimers,
wrong locale and polished but false answers. Define expected outcomes **per
metric**: a fluent false answer may legitimately pass coherence while failing
groundedness and task adherence.

Measure false accepts, false rejects and agreement with reviewers for each
metric/slice. Inspect disagreements and rubric ambiguity. Keep judge identity,
version, thresholds and all failed controls. Avoid giving the judge the
candidate's own output as reference, revealing baseline/candidate labels or
letting an instruction inside the candidate answer redefine the rubric.

The [recorded grounding controls](labs/lab-18-native-evaluation-traces.md)
include a real bad answer accepted by two grounding evaluators. That is a
known false positive, not an evaluation success. Combine explicit policy
predicates with human review; do not silently relabel controls to get green.

## Repeated trials and fair comparisons

Separate two experiments:

1. **Generation variance:** capture the candidate repeatedly on the same frozen
   inputs and controlled initial state. Save each raw answer/response ID.
2. **Judge variance:** judge the **same saved answers** repeatedly. A rerun of the
   full hosted runner changes captures too, so it does not isolate the judge.

Use a small approved pilot first (for example three trials per locale), then
choose sample size from the tolerated risk, observed variation and budget.
Predeclare stopping rules; do not stop at the first green run. Report per-case,
per-slice and per-run distributions, not just one global average.

For illustration, 5/5 independent Bernoulli passes gives a two-sided 95% Wilson
interval of approximately **0.57 to 1.00**, not proof of perfection.
Repeated grades for the same case or the same judge are correlated: treating
every grade as a new independent customer overstates confidence.
For realistic comparisons use a case-level paired analysis or cluster bootstrap,
preserving all trials/locales within each case, and expert review of rare harms.
No statistical aggregate overrides a violated hard safety invariant.

Compare baseline and candidate on the same frozen case IDs, fixtures/state,
locale, trusted facts, rubric, evaluator version, judge-model version and
sampling configuration. Blind/randomize order when feasible. Retain full
distributions, pass/fail transitions and practical effect sizes. A changed
dataset, evaluator or judge version requires rebaselining, not an improvement claim.

## Efficient execution and release policy

Run the cheapest reliable evidence first:

1. Local schema/calculator/store/API checks on every relevant change.
2. Small deterministic golden gate before any paid judge.
3. Targeted changed-feature slices and calibrated negative controls.
4. Native EN/FR smoke judges with explicit cost/time caps.
5. Broader holdout/repeated/trajectory evaluation on scheduled or high-risk changes.
6. Staging business-flow acceptance, identity controls and protected promotion.

Reuse **captured answers** when experimenting with judges. Cache only when
input, state, model, rubric and evaluator identities match; clearly label reused
captures as non-fresh inference. Bound concurrency to avoid quota noise.
Estimate nominal work as cases × locales × trials × evaluators, but account for
token length, retries and evaluator-internal requests before approving cost.

The current repository release policy is deliberately specific:

| Condition | Existing behavior |
| --- | --- |
| Deterministic gate failure | Blocks production |
| Native invocation error, incomplete/unscored/errored judge evidence | Blocks production |
| Complete native judge scores below CLI's requested pass rate | CLI fails; workflow retains advisory scores |
| Missing complete EN/FR evidence | Separate workflow completeness gate blocks |
| Protected production approval missing | Production job waits |
| Reviewer invocation200/memory403 readiness failure | Deployment stage fails |

`--minimum-pass-rate 1.0` is a fraction of passed items, **not** a metric score
threshold of 1/5. Do not mistake `continue-on-error` on the advisory step for
permission to ignore service failures. A proposed stricter quality gate needs
calibration, an explicit policy change and release approval; this lab changes
neither production policy nor application behavior.

In [release 39527950931](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39527950931),
native service errors produced no scored items. The gate blocked. The authorized
operator retried only the failed job at the same source; complete successful
EN/FR evidence preceded promotion. Preserve failed attempts; do not keep rerunning
quality failures until one happens to pass.

## Diagnose and monitor

| Observation | Investigation | Incorrect conclusion |
| --- | --- | --- |
| 401/403 | Caller, token audience, project scope, least-privilege role, propagation | Grant broad roles or delete auth |
| 429/timeout | Quota, approved concurrency, backoff, service health | Model quality is zero |
| Native `SystemError`, no items | Run/correlation IDs, service error, bounded approved retry | Ignore the incomplete-evidence gate |
| High score, bad answer | Independent context, rubric, leakage and calibration controls | The answer is safe because a judge passed |
| Lower candidate score | Per-case paired results and uncertainty; frozen configuration | Every small delta is a regression |
| Missing trajectory/spans | Supported input schema and actual telemetry ingestion | A response ID proves all internal stages |
| Repeated case differs | Persisted revision/actor/state and reset isolation | Every variation is stochastic LLM behavior |

In operation, monitor service errors separately from quality: latency,
availability, cost/usage, drift in inputs, locale/status slices, human overrides,
policy violations and revision failures. Promote reviewed incidents into versioned
test sets. Sample sensitive production data only under approved privacy/retention
controls; this workshop remains synthetic.

## Completion checklist

Deliver a versioned dataset/coverage matrix, human-labeled calibration and
holdout splits, exact source/deployment/model/evaluator/rubric identities,
raw captures and native run IDs, completeness/quality results, uncertainty and
per-case deltas, cost/latency, triaged failures and an owner-approved release
decision. Use the [Lab 19 worksheet](labs/lab-19-evaluation-engineering.md#exercise-1910-write-the-release-recommendation)
and [PowerPoint](assets/decks/foundry-evaluation-engineering-en.pptx) to explain
what the evidence establishes and what it does not.
