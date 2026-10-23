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

### Start here if the agent tab says No evaluations found

In the supplied screen, **Build > Agents > quote-preparation-agent >
Evaluation** shows an empty list. The left navigation also has **Optimize >
Evaluations**. These are different entry points: an empty agent-scoped list
does **not** prove that the project has no SDK-created dataset evaluations.
The workshop runner creates a custom dataset evaluation named
`Hosted CI quote-preparation-agent:<version>`, not a new agent deployment.
Do not select **Publish**, **Automatic Evaluation**, or **Create evaluator**
to find a retained run.

Choose one path before continuing:

| Goal | Follow | New inference cost / agent invocation |
| --- | --- | --- |
| Complete Exercise 19.4 by inspecting a real retained run | A below | No new judge or agent calls |
| Learn upload, mapping and judge behavior with supplied examples | B below | Paid judge calls after approval; no agent invocation |
| Test the current deployed agent on all five cases per locale | Exercise 19.5 in [Lab 19](labs/lab-19-evaluation-engineering.md#exercise-195-run-the-minimal-native-enfr-experiment) | Agent calls and paid judges after approval |

### A. Open and inspect an existing real run

![Staging project Evaluations list showing Optimize navigation, completed v6 runs and failed attempts](assets/evidence/lab19-project-evaluations-2026-10-23.png)

Figure 1. Staging **Build > Optimize > Evaluations**, captured on 2026-10-23.
The sidebar entry opens the project's retained runs, not the agent's empty
Evaluation tab. Completed and failed v6 attempts coexist: verify the run ID.

1. At [ai.azure.com](https://ai.azure.com), enable **New Foundry** if needed.
   In the top project selector, choose
   `proj-desjardins-quote-preparation-staging` in account
   `aif-desjardins-quote-preparation-staging`. Confirm your tenant. The `-poc`
   project is production; do not switch there to work around missing access.
2. From the agent screen in the supplied example, select **Evaluations** under
   **Optimize** in the **left sidebar**, not the agent's horizontal
   **Evaluation** tab. Other portal builds label the project entry **Evaluation**.
3. Clear search, date and target filters. Search for
   `Hosted CI quote-preparation-agent`, then select a matching evaluation.
   Open its run named `quote-preparation-agent:<version>` if a separate run
   list appears. Multiple definitions can have the same display name;
   verify the run ID, not only the name or the latest date.
4. For the approved 2026-10-21 release, locate one of these recorded runs.
   They judged staging version **6**, even if a later version is now active.

   | Locale | Native run ID | Expected scored items |
   | --- | --- | --- |
   | `en-CA` | `evalrun_985de95ac8e742be88c6172d8a4098d6` | 5 |
   | `fr-CA` | `evalrun_db159f558fd847668d7bba275ba1a353` | 5 |

5. Expand **Run details**. Record the definition/evaluation ID (`eval_...`),
   run ID (`evalrun_...`), status, dataset, judge deployment and evaluator
   configuration. The three criteria are `coherence`, `groundedness` and
   `task_adherence`. Inspect thresholds and versions where exposed; mark
   unavailable metadata as unavailable rather than guessing. Read IDs from
   the address bar or **Raw JSON** if they are absent from the visible details.
6. Scroll to **Detailed metrics result**. Open a row or its score/reason cell,
   depending on the portal build. Use the horizontal scrollbar to reach
   all metric and reason columns. Record the input `id` if exposed; row index
   `0` is not a stable case identifier.
7. Inspect that row's mapped inputs using the table below. Some portal builds
   expose only scores/reasons. In that case use the matching retained
   `captured.json` and run definition for input inspection, not a fabricated
   portal panel.

   | Criterion | Query input | Response input | Independent facts |
   | --- | --- | --- | --- |
   | Coherence | `evaluation_query`, including acknowledgement instructions | Selected-locale `response` text | Included in evaluation query |
   | Groundedness | `evaluation_query` | Selected-locale `response` text | `context` |
   | Task adherence | `task_query` system/user message array | `output_items` message array | Trusted facts in the task messages |

8. Compare the answer with the trusted facts and read each judge reason.
   For a valid case, pending employee review is not an approval. For an invalid
   ID, the answer must not claim a submitted draft. No applicant answer may
   disclose a price. A coherent answer can still be false.
9. Confirm **five unique scored items and all three metrics per item**, with
   no error or skipped/unscored metric. The recorded successful runs passed
   all three criteria for all five items. A different outcome needs inspection,
   not repeated retries until green. A `Failed` or `Partial` run is not complete
   passing evidence.
10. Export results if your portal offers export, or use the retained SDK
    `results.json`. Preserve the run identity and reasons. Complete the
    worksheet in [Exercise 19.4](labs/lab-19-evaluation-engineering.md#exercise-194-inspect-a-real-run-in-the-portal).

![Completed French v6 run with three 5/5 metric summaries, five result rows and the horizontal scrollbar](assets/evidence/lab19-v6-run-results-2026-10-23.png)

Figure 2. Retained **French staging v6** run
`evalrun_db159f558fd847668d7bba275ba1a353`, definition
`eval_923cb34017c743a59089a36cb55d4e28`, captured on 2026-10-23 without rerunning
it. All three summaries show **5/5**. Run details is collapsed to expose all
five rows and the horizontal scrollbar. These are retained release results,
not results for the authored practice dataset below.

If you cannot find the recorded run, verify the project and filters, then ask
the release custodian for its evaluation ID, available `report_url`, or the
matching artifacts from
[release 39527950931](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39527950931).
An `evalrun_...` ID alone is not a complete portal URL. A custodian can obtain
the link from the retained `results.json` with PowerShell:

```powershell
$result = Get-Content '.local\YOUR-RETAINED-RUN\results.json' -Raw | ConvertFrom-Json
$result.run | Select-Object id, status, report_url
```

Replace the directory with the actual extracted locale artifact. Open a
nonempty `report_url` in the same signed-in tenant/project. If the service
does not provide one, use project navigation or inspect the exported results.
If neither portal nor matching artifacts are accessible, record Exercise 19.4
as **blocked**. Creating a synthetic practice run does not replace real evidence.

### B. Upload a ready-made practice dataset

These files need **no Python, conversion, agent invocation or customer data**:

* [Download English JSONL](assets/datasets/portal-practice-en-CA.jsonl)
* [Download French JSONL](assets/datasets/portal-practice-fr-CA.jsonl)

Each file has **three rows**: `practice-ready`, `practice-invalid` and
`control-false-approval`. The answers are **authored synthetic examples, not
captured agent output**. The last row deliberately invents an approval, a price
and delivery. Human review expects grounding to reject it; coherence can still
pass. If grounding accepts it, report a false accept, not a successful control.
They are learning/calibration data, not a release benchmark or holdout.

From a cloned checkout, copy both files to an ignored working directory
(PowerShell 7, repository root):

```powershell
$portalWork = Join-Path '.local' ('portal-eval-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $portalWork | Out-Null
Copy-Item docs\assets\datasets\portal-practice-*.jsonl $portalWork
Get-ChildItem $portalWork -Filter '*.jsonl' | ForEach-Object {
    $rows = @(Get-Content $_.FullName | ForEach-Object { $_ | ConvertFrom-Json })
    if ($rows.Count -ne 3) { throw "Expected three rows: $($_.Name)" }
    $_.FullName
    $rows | Select-Object id, locale, provenance, expected_groundedness
}
```

For a copy/paste-only alternative, this is a complete **one-row English**
JSONL dataset. Put the single line in a UTF-8 file ending in `.jsonl`;
do not include the code fence or wrap it in a JSON array.

```jsonl
{"id":"practice-ready","locale":"en-CA","provenance":"authored_synthetic_not_agent_capture","query":"Acknowledge CASE-SYN-001 for employee review. State that this is a training simulation, not an insurance quote, with no delivery. Do not disclose a price or claim approval.","context":"CASE-SYN-001 is a valid synthetic case. Its draft is submitted for employee review. The employee decision is pending. This is a training simulation, not an insurance quote, with no delivery.","response":"Training simulation only, not an insurance quote. No delivery. The draft for CASE-SYN-001 has been submitted for employee review. An employee decision is pending.","expected_groundedness":"pass"}
```

The one-row example tests mapping only; it has **no negative control**.
Use a three-row download for the full practice exercise.

1. Follow A.1 and A.2 to open the staging project's **Evaluations** page.
   Select **Create**, then choose target **Dataset**, not **Agent** or **Model**.
   Dataset evaluates supplied responses without invoking or changing the
   quote agent. Select a dataset before continuing to **Scope > Individual turns**.

   ![Dataset target selected with the project file picker and Upload new dataset button](assets/evidence/lab19-dataset-target-2026-10-23.png)

   Figure 3. Choose **Dataset**. The right pane lists existing project assets
   and provides **Upload new dataset**; no evaluation has been submitted.

2. Select **Upload new dataset**, enter a unique name such as
   `lab19-portal-practice-en-CA-v1-<your-initials>`, select **Choose file**, and
   pick the downloaded English JSONL. Select **Upload** to create the data
   asset, not an evaluation run. Do not replace release data. If this button
   is absent, use **Data** in the sidebar, then return to the Dataset picker.
   The staging asset `lab19-portal-practice-en-CA-v1-demo`, version 1, was
   uploaded for these screenshots; select it if you have access, or upload
   your own uniquely named copy.

   ![Upload dialog with a unique practice dataset name and the English JSONL file selected](assets/evidence/lab19-practice-upload-2026-10-23.png)

   Figure 4. **Upload** stores the synthetic file. Paid judging starts only
   after the separate evaluation **Submit** action later.

3. Verify the preview shows **three records**, not one array or one text field.
   `query`, `context` and `response` must each be strings. `locale` must be
   `en-CA` in every row. Do not upload the nested bilingual
   `eval/applicant-message-dataset.jsonl` or the JSON array produced in
   Exercise 19.3 to this flat JSONL flow.

   ![Selected practice dataset and its preview with separate id, locale, query and context columns](assets/evidence/lab19-practice-preview-2026-10-23.png)

   Figure 5. The preview has its own vertical and horizontal scrollbars.
   Scroll inside it to check all three rows, including `control-false-approval`,
   and the `response` column. Its pager reads **1-3 of 3**; **Top 5 rows** is
   the preview limit, not the size of this dataset.

4. Select **Next**, keep **Individual turns**, then select **Next** again.
   With these standard column names, the captured portal build goes directly
   to **Criteria**, without a separate **Field mapping** step. If that step
   appears, check its dropdowns. In either flow, verify the evaluator's
   **Advanced settings** in step 5 against this table:

   | Evaluator input | Dataset column | Why |
   | --- | --- | --- |
   | `query` | `query` | The acknowledgement task, not only a bare case ID |
   | `response` | `response` | The supplied answer being judged |
   | `context` | `context` | Independent facts, never the answer itself |
   | `ground_truth` | Leave unassigned | Not needed by the two selected criteria |

   Keep `id`, `locale`, `provenance` and `expected_groundedness` as metadata.
   **Do not map the human label into the judge's context or query.**
5. In **Criteria**, select the existing **Judge model** deployment
   `gpt-4o-mini`, not the automatically selected showcase model. Select
   **Clear selection** to remove defaults. Search for and select the exact
   **Coherence** checkbox, then search for **Groundedness** and select its
   exact checkbox, not **Groundedness Pro** or the six-metric **Output quality**
   preset. Select **Review selected (2)** and clear the search to see both.
   Use each selected evaluator's gear button to open its configuration.
   Expand **Advanced settings** and check query/response, plus context for
   Groundedness, against the table. Record the effective model version and
   threshold; the captured Groundedness configuration shows threshold **3**.
   Select **Update** if you changed a setting, or **Cancel** to close without
   changes. Leave tool fields unavailable. Do not create a deployment or add
   task/tool evaluators without their required inputs. Use Exercise 19.5 for
   the verified three-criterion SDK experiment.

   ![Groundedness settings with gpt-4o-mini, threshold 3 and separate context, query and response mappings](assets/evidence/lab19-groundedness-mapping-2026-10-23.png)

   Figure 6. Actual mappings for the uploaded practice file under **Criteria >
   Configure Groundedness > Advanced settings**, captured on 2026-10-23.

6. Name the evaluation
   `lab19-staging-synthetic-en-CA-v1-trial1-<your-initials>`.
   Review target **Dataset**, scope **Individual turns**, the exact asset,
   mappings, and exactly **two** criteria. The row count was checked in the
   dataset preview; this summary does not repeat it. Stop here without cost
   approval. Submission requests six
   row/metric judgments; evaluator internals may make additional calls.

   ![Unsubmitted evaluation review with the practice asset and only Coherence and Groundedness selected](assets/evidence/lab19-practice-review-2026-10-23.png)

   Figure 7. Stop before **Submit** without approval. This screenshot records
   configuration only: no practice evaluation or judge calls were submitted.

7. After approval, select **Submit**. Return to the project **Evaluations**
   list and open that exact name. Wait for **Completed**, then inspect each
   row and both metric reasons. Require three scored rows with no errors;
   a terminal status alone is insufficient. Record the deliberate false
   approval's grounding outcome even when the judge gets it wrong.
8. Only with the additional judge budget, repeat with the French file,
   its French asset/run name, and `fr-CA` rows. Keep languages separate.
   Export available results and record dataset hash, thresholds and run IDs.

### Use actual captured responses instead of authored practice answers

After an approved SDK run in Exercise 19.5, export its immutable captures to
flat JSONL for **Dataset** evaluation. This does not call the agent or judges:

```powershell
$capturePath = Join-Path $work 'en-CA-trial1\captured.json'
$captured = @(Get-Content $capturePath -Raw | ConvertFrom-Json)
if ($captured.Count -ne 5) { throw 'Expected five real captured items.' }
$portalPath = Join-Path $work 'portal-captured-en-CA.jsonl'
$captured | Select-Object id, locale, query, evaluation_query, context, response |
    ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 20 } |
    Set-Content $portalPath -Encoding utf8
Get-FileHash $portalPath -Algorithm SHA256
```

Here `$work` is your existing Lab 19 output directory. For retained release
artifacts, use their actual extracted capture path instead. Repeat for French
by changing both input and output names. In B.4 map **query to
`evaluation_query`**, not the bare `query` case ID; keep response/context
mapping unchanged. Select only Coherence/Groundedness. Preserve the original
capture and run identity separately. These new dataset-judge runs reuse
captured answers; they do not prove fresh inference or reproduce the SDK's
message-based task-adherence criterion.

### Portal troubleshooting checklist

| What you see | What to do |
| --- | --- |
| Agent Evaluation tab says **No evaluations found** | Open left-sidebar **Optimize > Evaluations**; clear filters and check run identity as in A |
| Create only offers an Agent target | Use the project-level entry; if Dataset is unavailable, use the verified SDK path, not an invented wizard option |
| Dataset preview is one array or fields are objects | Use the flat practice JSONL, one object per line; Exercise 19.3 output is for the SDK runner |
| A mapping is **Unassigned** | Assign the required column before submission; never substitute response for trusted context |
| No approved judge deployment or permission error | Stop and ask the project owner; do not create resources, grant roles or switch to production |
| Run is **Partial**, **Failed**, or has unscored items | Retain error details and run ID; service failure is not a quality score |
| No download/export or input panel | Use matching retained SDK artifacts; document the portal limitation |

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
2. Read the server-side agent details and endpoint version selector before
   capture, as shown in Lab 19. `azd ai agent show` can select an older version
   from local metadata; do not equate that with current endpoint routing.
   `--version` on
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

{% raw %}

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

{% endraw %}

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
