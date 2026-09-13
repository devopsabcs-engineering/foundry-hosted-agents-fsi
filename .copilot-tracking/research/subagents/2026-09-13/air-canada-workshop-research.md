<!-- markdownlint-disable-file -->
# Air Canada Workshop Research

Status: Research complete; runtime verification and customer-specific design remain out of scope. Research date: 2026-09-13.

## Scope and Questions

Research the sibling Air Canada workshop's actual lab sequence, timing, prerequisites, audience, bilingual parity, runtime and infrastructure dependencies, reusable exercises, scenario-bound materials, instructor conventions, evaluation gates, and cheap validation commands. Resolve conflicting invocation guidance using implementation evidence and current official documentation. Recommend selective adaptation, not a repository copy.

## Constraints and Evidence Standard

Writes are limited to this research artifact. No secrets, authentication, deployments, installations, or application execution. Paths beginning ../foundry-hosted-agents/ refer to the sibling repository. Report source claims separately from runtime verification.

The sibling working tree changed during research. Its observed HEAD was 2e10a60e168bd6707d0f5dae380d6d595430b077. A read-only git status showed uncommitted EN/FR Lab 00/02/03/04 edits, infrastructure parameter edits, an MCP probe edit and a new probe test. Later direct line checks supersede initial reads: both language tracks now include Git Bash/jq/curl setup and isolated Lab 04 invocation. Findings concern the observed working tree, not proof of what is committed or published. No source changes were made by this research.

No AGENTS.md or .github/copilot-instructions.md existed at the sibling root or shared parent. The tracked .github inventory contained workflows, not additional instruction files. The target context already checked ancestors. Supplied HVE research/Markdown conventions apply to this artifact.

## Initial Findings

* Target context read: .copilot-tracking/research/subagents/2026-09-13/workshop-context-research.md.
* The sibling README requires explicit full-history input with store: false and rejects native persistence, but its quick start still recommends default azd invocation. Hypothesis: quick-start guidance is stale relative to the implementation. Discriminating check: inspect the request converter, invocation script, and conversation tests.
* Both required Foundry skills were read in order: vscode-microsoft-foundry, then microsoft-foundry. No dependency setup or execution workflow was entered because setup can install software.
* Tool discovery is unavailable: no callable tool_search is exposed. Deferred Azure AI app best-practices tools cannot be invoked under the discovery prerequisite. Their content remains unverified; no substitute tool response is invented.

## Lab Sequence and Delivery

All nine English labs were read in full. Every lab has prerequisites, learning objectives, numbered exercises, a knowledge check, and next-lab navigation. Their local paths are ../foundry-hosted-agents/docs/labs/ followed by the filenames below; duration evidence is line 13 (line 14 in Labs 04 and 06).

| Lab | Source filename | Minutes | Actual work |
| --- | --- | --- | --- |
| 00 | lab-00-setup.md | 20 | Python/tool setup, clone, approved Azure identity/subscription, local fixture tests |
| 01 | lab-01-architecture.md | 30 | Trace supervisor/specialists, degradation flags, four MCP layers, map portal resources |
| 02 | lab-02-mcp-servers.md | 30 | Read FastMCP servers, create isolated group/registry, remote ACR builds, Bicep preview/deploy, call four tools |
| 03 | lab-03-deploy-agent.md | 35 | Read manifest, provision Foundry/model/connections, deploy Toolbox/agent, grant account-scoped runtime roles |
| 04 | lab-04-invoke-agent.md | 45 | Version-pinned helper, three web-pilot scenarios, correlated traces, missing evidence, recall/isolation/replay |
| 05 | lab-05-evaluations.md | 40 | Eight golden categories, deterministic checks, distinguish executed judges from proposed custom rubrics |
| 06 | lab-06-cicd.md | 35 | Protected release, OIDC, strict SSE and evidence gates, approvals, load/quota and telemetry interpretation |
| 07 | lab-07-troubleshooting-rbac.md | 40 | Historical 401 investigation: roles/dataActions, network/policy/Conditional Access, compare paths and recovery evidence |
| 08 | lab-08-production-readiness.md | 30 | Four experiment tracks, scorecard, conditional-go reasoning, confidence-tagged decision deck |

The home pages advertise three-hour and six-hour formats. The index budgets Lab 04 at 30 minutes, but the current lab requires 45. Detailed lab durations total 305 minutes, versus the index's 290. The six-hour schedule also allocates 45 minutes to the nominal 40-minute evaluation lab. Recalculate the agenda rather than copying these numbers. Source: ../foundry-hosted-agents/docs/index.md:65 and ../foundry-hosted-agents/docs/fr/index.md:68.

Audience is explicitly AI/platform engineers, DevOps engineers, solution architects, and support/SRE engineers, not a general business-user hackathon. Initial labs are labeled beginner, Labs 02-05 intermediate, and Labs 06-08 advanced. The content presumes comfort with Python, shell commands, resource identities, and deployment troubleshooting even though Lab 00 says prerequisites "None". Source: ../foundry-hosted-agents/docs/index.md:45-79.

Published prerequisites: VS Code, Python 3.13, azd, Azure CLI, approved subscription and gpt-4o-mini quota; GitHub/Copilot is listed as optional. Practical access requirements include repository access, resource creation, ACR Tasks, account-scoped role assignments, and optional pilot-group membership for the separate chat. Docker Desktop is not required because MCP images use remote ACR builds. GitHub workflow authors and instructors need separate environment/OIDC/reviewer configuration; ordinary learners should not receive production or tenant-wide policy-administration access. Sources: ../foundry-hosted-agents/docs/labs/lab-00-setup.md:50-105; ../foundry-hosted-agents/docs/labs/lab-02-mcp-servers.md:42-118; ../foundry-hosted-agents/docs/labs/lab-03-deploy-agent.md:100-120; ../foundry-hosted-agents/docs/labs/lab-06-cicd.md:116-130.

## Confirmed Documentation Drift

* The home-page predeployed-resource tip conflicts with current Labs 02-03's isolated learner-resource path. Initial English Lab 04 selected original staging, but concurrent source edits corrected that: ../foundry-hosted-agents/docs/labs/lab-04-invoke-agent.md:31-59 and ../foundry-hosted-agents/docs/fr/labs/lab-04-invoke-agent.md:32-61 now retain the learner environment and make separately deployed chat optional. Do not report the initial mismatch as an unresolved current-file defect.
* Initial English Lab 00 lacked shell prerequisites. Concurrent edits added PowerShell 7.3+, Git Bash, jq, curl, PATH verification, and MSYS_NO_PATHCONV in both languages: ../foundry-hosted-agents/docs/labs/lab-00-setup.md:50-71 and ../foundry-hosted-agents/docs/fr/labs/lab-00-setup.md:51-72. Lab 02 still adds ACR Tasks and role-assignment privileges beyond the top-level prerequisite list.
* Lab 01 describes MCP implementations as separate azd services; Lab 02 correctly says they are Bicep-deployed, not root azure.yaml services. The actual manifest confirms Lab 02.
* Lab 05's fixed expected count of 12 passed contradicts Lab 00's instruction to use exit status and current skips rather than historical counts. This research did not execute tests.
* ../foundry-hosted-agents/deliverables/deck-outline.md:10-14 says 31 decision slides; read-only ZIP inspection found 36. The outline is not parsed by the generator (lines 3-6), so it can drift independently.
* ../foundry-hosted-agents/src/threat-assessment-agent/graph.py:10-12 and ../foundry-hosted-agents/src/threat-assessment-agent/state.py:3-7 still describe Foundry-managed history as the baseline. The converter and clients below establish the actual full-history contract. The old main.py degradation-adapter comments in graph.py are also not the current main.py implementation.
* ../foundry-hosted-agents/eval/check_conversation.py:45-48 rejects endpoints whose hostname lacks -staging. This does not fit the isolated fha-learn-* lab names. Current Lab 04 prose mentions a live history verifier, while the inspected Lab 05 is primarily fixture tests and runner discussion. Do not promise a complete learner live-evaluation/history path until commands and target guards are reconciled.

## Invocation Resolution

The default supported implementation rejects native persistence: ../foundry-hosted-agents/src/threat-assessment-agent/runtime_evidence.py:30-37 rejects a conversation ID, previous_response_id, and explicit store:true. ../foundry-hosted-agents/src/threat-assessment-agent/main.py:18-26 supplies that converter to LangGraphAdapter. Its ImportError fallback does not explicitly supply the converter; it is not evidence of equivalent behavior.

The guard rejects explicit true, rather than proving that omission of store is safe. All approved callers should continue to send false explicitly. Local SDK regression source verifies rejection without historical lookup and full user/assistant history reaching every specialist without cross-request state: ../foundry-hosted-agents/src/threat-assessment-agent/tests/test_runtime_evidence.py:27-103. These tests were read, not executed.

../foundry-hosted-agents/scripts/invoke-agent.sh:4-18 creates a session with version_indicator/version_ref, then calls the dedicated agent Responses endpoint with agent_session_id, one user input, stream:true and store:false. The helper is single-request, not itself a full-history chat client. Lab 04's web pilot is the documented multi-turn client.

Current official Microsoft Learn pages fetched on 2026-09-13 support both platform-managed history and nonpersistent requests. The restriction above is application-specific, not a blanket Foundry limitation:

* [Hosted agents](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents), updated 2026-09-10: dedicated agent Responses endpoint, sessions distinct from conversations, platform-managed history capability, immutable versions, per-session compute.
* [Runtime components](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/runtime-components), updated 2026-08-27: store:false requires client-carried prior input/output; previous_response_id refers to stored responses. Its general project-client examples do not override this repository's converter.

Use the helper plus SSE contract checks for this source snapshot. Do not reuse the README quick-start default invocation or Lab 07's historical --new-conversation command as current instructions. Native-history migration requires a separately validated SDK/client/identity change, not removal of the guard alone.

The web client posts complete backend-owned history with stream:true/store:false to its configured dedicated endpoint; it does not create the helper's version-pinned session on each turn. The live conversation checker likewise uses its supplied routed endpoint. Avoid describing every client as version-pinned. Sources: ../foundry-hosted-agents/apps/web-chat/app.py:94-142; ../foundry-hosted-agents/eval/check_conversation.py:51-67; ../foundry-hosted-agents/scripts/tests/test_workflow_contracts.py:34-46.

The official pages verify the conceptual protocol and dedicated endpoint, not the exact compatibility of this installed SDK/azd combination or every field of the helper's version_indicator request. Those remain version-sensitive until an authorized smoke test. The currently retrieved hosted-agent page lists Canada Central and Canada East and a 2-60 minute idle range; the older decision outline says 5-60. Do not reuse historical limits, infer available quota, or infer Canadian data residency from a region choice. The source uses GlobalStandard model deployment. Sources: official hosted-agent page above; ../foundry-hosted-agents/deliverables/deck-outline.md:135-147; ../foundry-hosted-agents/azure.yaml:8-15.

## Bilingual Structure and Parity

* Both tracks have a home page, continuous-validation page, and all nine same-named labs: ../foundry-hosted-agents/docs/index.md:1-9; ../foundry-hosted-agents/docs/fr/index.md:1-10. French labs declare lang: fr and /fr/labs/... permalinks; reciprocal language links target the same lab.
* Structural checks found matching exercise counts in order: 5, 4, 4, 4, 5, 4, 8, 8, 4. Current French metadata confirms the same per-lab durations, including 45 minutes for Lab 04. Evidence anchors: ../foundry-hosted-agents/docs/fr/labs/lab-00-setup.md:14; ../foundry-hosted-agents/docs/fr/labs/lab-04-invoke-agent.md:15; ../foundry-hosted-agents/docs/fr/labs/lab-06-cicd.md:15. Count parity does not prove semantic equivalence or runnable commands.
* A read-only fenced-block comparison found differences in the translated Mermaid labels and historical RBAC placeholders. Concurrent edits explain initial Lab 00/04 disparities; final checks show matching learner-environment policy. French prose preserves English CLI identifiers and UI control names. It explicitly retains reviewed English fixture prompts: ../foundry-hosted-agents/docs/fr/labs/lab-04-invoke-agent.md:63-67.
* The site is Jekyll with Just the Docs remote theme, github-pages/webrick gems, Mermaid 10.9.1, and a customer-specific Pages URL. Language filtering relies on /fr path prefixes in CSS :has and a JavaScript fallback, not independent language builds. A nonempty baseurl needs review because filters assume root-relative /fr links. Sources: ../foundry-hosted-agents/docs/_config.yml:1-24; ../foundry-hosted-agents/docs/Gemfile:1-3; ../foundry-hosted-agents/docs/_includes/head_custom.html:1-26.
* This is bilingual teaching content, not verified bilingual agent execution. Prompts, sampleQueries, golden queries, fixed refusal text, and output checks are English. The deterministic planner recognizes device ID and account/user ID plus exact metric names; it does not implement French aliases. Source: ../foundry-hosted-agents/src/threat-assessment-agent/graph.py:41-115 and 203-230; ../foundry-hosted-agents/apps/web-chat/frontend/src/samples.js:1-20; ../foundry-hosted-agents/eval/golden-dataset.jsonl:1-8.
* Adaptation needs paired EN/FR scenarios with identical expected evidence, tool plans and decisions, plus terminology review. Retaining canonical identifiers is sensible; silently translating parser labels or forbidden phrases is not. French refusal and uncertainty behavior require explicit tests, not an assumption based on a translated deck.

## Runtime and Infrastructure Dependencies

| Surface | Verified source and dependencies | Adaptation implication |
| --- | --- | --- |
| Agent host | ../foundry-hosted-agents/azure.yaml:38-71: Python 3.13 remote build, main.py, Responses 2.0.0, 0.5 CPU/1 GiB, Toolbox version 1, gpt-4o-mini | Keep deployment contract only after resolving/pinning toolchain versions; do not inherit customer identifiers or quota choices |
| Agent libraries | ../foundry-hosted-agents/src/threat-assessment-agent/requirements.txt:20-30: LangGraph >=1.2.11,<2, LangChain/LangChain OpenAI >=1.0.3,<2, langchain-azure-ai >=0.1, unpinned azure-ai-agentserver-langgraph, OpenAI >=1.40, identity >=1.17; MCP 1.29.1 and adapters 0.3.2 fixed | No reproducible full runtime lock; remote builds can differ despite identical source. This is LangGraph, not Microsoft Agent Framework |
| Graph and tools | ../foundry-hosted-agents/src/threat-assessment-agent/graph.py:519-564; ../foundry-hosted-agents/src/threat-assessment-agent/toolbox.py:18-80 | Deterministic sequential supervisor; two role-specific allowlists; mandatory lookups execute before tool-free summarization; Composer has no tools |
| MCP services | ../foundry-hosted-agents/mcp/defender-server/Dockerfile:1-13; ../foundry-hosted-agents/mcp/defender-server/requirements.txt:1; both server main.py files:13-17 | Separate FastMCP streamable-HTTP processes, port 8000; Defender container uses Python 3.11-slim and mcp >=1.6,<2, unlike agent's exact MCP version. Validate both transports together |
| Core Bicep | ../foundry-hosted-agents/infra/main.bicep:1-123; ../foundry-hosted-agents/infra/main.parameters.json:5-22 | Composes monitoring, AIServices/project/model/connections, RBAC and MCP apps. Does not include optional Cosmos in baseline. MCP image inputs must be real built images; defaults are non-MCP quickstart placeholders |
| Identity/network | ../foundry-hosted-agents/infra/modules/ai-foundry.bicep:48-64 and 145-165; ../foundry-hosted-agents/infra/modules/mcp-container-apps.bicep:33-51 and 95-124 | Public Foundry account, local auth not disabled, RemoteTool connections with authType None, public MCP ingress; isolated prefixes get registry-scoped AcrPull identity. Not an FSI production security template |
| Capacity | ../foundry-hosted-agents/infra/main.bicep:27-31; ../foundry-hosted-agents/infra/modules/mcp-container-apps.bicep:114-124 | Staging suffix chooses 50k TPM, otherwise 10k; MCP replicas 0-1. Naming affects capacity and isolation; learner concurrency requires a budgeted check |
| Evaluation runtime | ../foundry-hosted-agents/.github/workflows/deploy-and-evaluate.yml:362-365 | CI separately installs azure-ai-projects 2.6.0, OpenAI 3.6.0, identity 1.25.3. requirements-dev contains only pytest; do not equate base test setup with complete live-evaluation setup |
| Optional web pilot | ../foundry-hosted-agents/apps/web-chat/requirements.txt:1-7; ../foundry-hosted-agents/apps/web-chat/frontend/package.json:7-24; ../foundry-hosted-agents/.github/workflows/web-chat-build.yml:25-49 | FastAPI, httpx/SSE, PyJWT, Azure identity; React 19/Vite 7/MSAL 4, Node 22 build. Additional app registration and deployment, not part of base nine-lab provisioning |
| Optional persistence | ../foundry-hosted-agents/src/threat-assessment-agent/state.py:46-75 | Cosmos imports and checkpointer are feature-flagged and off by default. Do not present this as working durable history or baseline dependency |

Important architecture nuance: the supervisor is a pass-through node plus a fixed completion-state routing function. Evidence completes before risk; risk receives the original request and evidence summary. Each specialist has context/permissions, but there is no parallel graph fan-out or independent deployment per specialist. Toolbox performs exact allowlisted lookups, then creates a LangChain agent with tools=[] to summarize supplied results. Sources: ../foundry-hosted-agents/src/threat-assessment-agent/graph.py:375-440 and 519-564; ../foundry-hosted-agents/src/threat-assessment-agent/toolbox.py:63-80.

## Reusable Architecture and Exercises

| Reuse selectively | Evidence | Change required |
| --- | --- | --- |
| Four tool layers: implementation, hosting, registration, consumption | ../foundry-hosted-agents/docs/labs/lab-01-architecture.md:73-92 | Replace the incorrect separate-azd-service wording and airline tool labels |
| Gather evidence, assess it, compose with no tools | ../foundry-hosted-agents/src/threat-assessment-agent/graph.py:41-115 and 519-564 | New domain prompts, state names and decision boundaries; do not merely rename crew/device examples |
| Exact tool permissions and observable receipts | ../foundry-hosted-agents/src/threat-assessment-agent/toolbox.py:18-54; ../foundry-hosted-agents/src/threat-assessment-agent/graph.py:364-373 | New read-only tool contracts and verified missing/unknown results |
| Diagnose direct-MCP success separately from hosted identity/toolbox success | ../foundry-hosted-agents/docs/labs/lab-02-mcp-servers.md:122-166 | Use only approved learner endpoints; preserve distinction between transport, data availability and evidence quality |
| Recall, independent request isolation and retry boundaries | ../foundry-hosted-agents/eval/check_conversation.py:13-36; ../foundry-hosted-agents/apps/web-chat/app.py:60-87 and 216-230 | Resolve staging-only guard and optional-client prerequisites; add bilingual corrections and unauthorized cross-session tests |
| Deliberately invalid SSE and false-green evaluation exercises | ../foundry-hosted-agents/scripts/test-agent-response.sh:7-48; ../foundry-hosted-agents/eval/evaluation_gate.py:8-42 | Preserve fail-closed cases; use domain-specific output quality checks |
| Evidence-based readiness scorecard | ../foundry-hosted-agents/deliverables/production-decision-gate-scorecard.md:28-48 | Reset every status/owner/evidence pointer for the new customer. An Air Canada pass cannot transfer |

## Scenario-Bound Materials

Replace, do not transplant:

* All three airline-security system prompts, English field-label regexes, synthetic provenance text, user-reference fallback headings and fixed refusal in ../foundry-hosted-agents/src/threat-assessment-agent/graph.py:41-115, 203-230, 341-360, and 450-513.
* Device/account fixtures, crew scheduling, airport kiosk names, sample vulnerability/CVE records, login baselines and traffic thresholds in ../foundry-hosted-agents/mcp/defender-server/main.py:19-74 and ../foundry-hosted-agents/mcp/anomaly-server/main.py:19-60. These are not Defender API integrations. Device-001 has synthetic vulnerability rows; most scenario devices deliberately return unavailable vulnerability telemetry. Missing data is not an empty finding set.
* Eight golden cases and their candidate-output fixtures, English prohibited phrases, expected citations and reviewer/version labels. Category coverage is reusable; those case approvals and thresholds are not customer approvals. Source: ../foundry-hosted-agents/eval/golden-dataset.jsonl:1-8; ../foundry-hosted-agents/eval/deterministic-tests/checks.py:22-29 and 86-184.
* The three exact UI prompts in ../foundry-hosted-agents/apps/web-chat/frontend/src/samples.js:1-20 and their imported deck notes in ../foundry-hosted-agents/scripts/release-slides.js:1-5 and 25-36. Updating the fixture alone would leave the demo/deck stale.
* Original tenant/group/identity references, staging/production resource names, shared URLs, support-ticket identifiers, run/version/commit evidence, screenshots, branding, quota suffix logic, and original business comparison. Preserve historical assets only in an explicitly attributed optional case study, never as new customer evidence.

## Instructor and Deck Conventions

The teaching structure is consistent: overview table, objectives, numbered exercises, expected result/cautions, knowledge check, and next lab. Labs 05/08 include discussion and decision interpretation, not only copy-paste commands. Lab 07's tenant Conditional Access/policy queries require appropriate permissions and should become an instructor-led evidence-reading case, not an expectation that every learner enumerate customer tenant policy. Source: ../foundry-hosted-agents/docs/labs/lab-07-troubleshooting-rbac.md:97-157.

../foundry-hosted-agents/scripts/build-workshop-deck.js:66-274 stores shared EN/FR slide definitions. It generates wide 13.33 x 7.5 inch slides with Segoe UI, consistent headers/footers, slide numbering and speaker notes. ../foundry-hosted-agents/scripts/release-slides.js inserts five current-context/demo/operations slides and four explicitly historical artifact slides. Existing ZIP structures contained 19 slides and 19 notes parts in each workshop deck; the decision deck had 36 slides/notes at inspection. These counts are observations of existing binaries, not proof that they match the changing generator source. Slide layout and visual clipping were not rendered or verified.

Speaker notes carry source URLs, limits, demo sequencing, and exact reviewed English prompts in both language tracks. Not all notes and evidence-image text are localized. The shared model is worth reusing; historical customer evidence and current-run labels must be replaced. The confidence legend confirmed/preview/inferred/requires-validation is useful for decision material, not a claim that every compiled slide was re-audited here. Sources: ../foundry-hosted-agents/scripts/build-workshop-deck.js:276-307; ../foundry-hosted-agents/scripts/release-slides.js; ../foundry-hosted-agents/deliverables/deck-outline.md:26-37.

Build dependencies are not standalone: ../foundry-hosted-agents/package.json:7-29 uses PptxGenJS 4.0.1 via a local tarball plus local vendor overrides; release-slides imports image-size, web sampleQueries and images under assets/release-evidence. Do not copy just the generator or drag the entire vendored dependency tree into the FSI repository. Re-author a small shared-language deck model with deliberately selected assets/dependencies when implementation is authorized.

## Evaluations and Safety Gates

* Eight categories cover true/false positive, ambiguity, missing data, conflicting evidence, prompt injection, unauthorized action claims and unsupported certainty. Keep the coverage pattern, but domain-review every new case: ../foundry-hosted-agents/eval/golden-dataset.jsonl:1-8.
* Six deterministic functions check required-field presence, citation substring presence, forbidden phrases, allowed connections, degraded-output policy, and conflict keywords. They are not a complete typed schema, citation validity checker, semantic refusal proof, or universal injection defense. triage_label/min_risk_level fields in the fixture are not directly enforced by those six checks. Source: ../foundry-hosted-agents/eval/deterministic-tests/checks.py:72-196.
* Hosted evidence is server-authored graph metadata, compressed/base64 encoded into bounded chunks, not trusted model-written JSON. Inputs are excluded from the metadata field list, but report text can still contain user information; no PII redaction guarantee follows. Oversized/missing evidence blocks the evidence gate. Sources: ../foundry-hosted-agents/src/threat-assessment-agent/runtime_evidence.py:9-27; ../foundry-hosted-agents/eval/run_hosted_evaluation.py:71-93 and 184-226.
* Coherence, groundedness and task_adherence are the executed judges. All required results must be present, finite, error-free, and meet the per-metric pass-rate threshold (default and release command: 1.0). A completed API job is insufficient. Task adherence extracts the actual Composer prompt through AST parsing. Sources: ../foundry-hosted-agents/eval/evaluation_gate.py:5-42; ../foundry-hosted-agents/eval/run_hosted_evaluation.py:229-260; ../foundry-hosted-agents/.github/workflows/deploy-and-evaluate.yml:419-424.
* Custom triage/citation-quality/conflict rubrics and builtin.tool_call_accuracy are proposed/catalog options, not executed release coverage. Source: ../foundry-hosted-agents/docs/labs/lab-05-evaluations.md:72-92.
* A content_filter error terminates further graph processing with a fixed refusal. Only the approved injection-case alternative accepts exact matching server-confirmed refusal text, no tool receipts, and no completed investigation flags. The runner does not retry content-filter failures to obtain a pass. This is not a general promise that no tools can ever run before any later-node refusal. Sources: ../foundry-hosted-agents/src/threat-assessment-agent/graph.py:339-362 and 533-542; ../foundry-hosted-agents/eval/run_hosted_evaluation.py:131-141 and 168-181.
* Release workflow sequence is lint/offline tests, Bicep validation, isolated staging MCP/agent deployment, SSE contract/conversation checks, candidate captures and judges, production reviewer approval, promotion, monitoring approval/check, manual recovery. OIDC, shared environment concurrency, environment selection, digest-pinned MCP images and prior-route discovery are reusable controls. Source: ../foundry-hosted-agents/.github/workflows/deploy-and-evaluate.yml:37-89, 205-208, 365-424, and 446-642.
* Production promotion rebuilds hosted code from evaluated source, not an identical agent binary. Required-reviewer settings are external to YAML and were not inspected. Monitoring requires response-correlated AppTraces before zero AppExceptions can count as healthy. No canary, automatic rollback, sustained-load guarantee, current SLA, or customer compliance certification was established here. Source: ../foundry-hosted-agents/docs/labs/lab-06-cicd.md:116-130 and 225-260; ../foundry-hosted-agents/scripts/tests/test_workflow_contracts.py:74-105.

## Cheap Validation Commands

Recommendations for a later authorized validation pass, not commands executed in this research. Use an already configured isolated Python 3.13 environment and explicit non-live settings; verify skip reasons. No dependency installation, application start, cloud invocation or build was performed here.

| Check | Command or method | Evidence and limits |
| --- | --- | --- |
| Request conversion/history/evidence | python -m pytest src/threat-assessment-agent/tests/test_runtime_evidence.py -q -p no:cacheprovider | Reads mocked SDK/graph boundaries; ../foundry-hosted-agents/src/threat-assessment-agent/tests/test_runtime_evidence.py:27-103 |
| Exact tool isolation | python -m pytest src/threat-assessment-agent/tests/test_toolbox.py -q -p no:cacheprovider | Adjacent tool adapter tests; inspect resolved dependencies first |
| Deterministic/evaluation failures | python -m pytest eval/deterministic-tests/ -q -rs -p no:cacheprovider | Release's offline suite, ../foundry-hosted-agents/.github/workflows/deploy-and-evaluate.yml:76-77 |
| SSE failures | bash scripts/test-agent-response.sh | Synthetic LF/CRLF and 12 invalid cases, no live call; requires jq/sed/Bash; ../foundry-hosted-agents/scripts/test-agent-response.sh:7-48 |
| Workflow contracts | python -m pytest scripts/tests/test_workflow_contracts.py -q -p no:cacheprovider | Stubs external commands; requires Bash and PyYAML; ../foundry-hosted-agents/scripts/tests/test_workflow_contracts.py:74-105 |
| Evaluation lint | ruff check eval | Existing CI scope, not a whole-repo lint guarantee; ../foundry-hosted-agents/.github/workflows/deploy-and-evaluate.yml:68-69 |
| IaC syntax | az bicep build --file infra/main.bicep --stdout | Only with a preinstalled Bicep executable; compile is not what-if, deployment, permissions or network proof. CI's existing build anchor: ../foundry-hosted-agents/.github/workflows/deploy-and-evaluate.yml:124-125 |
| Workflow syntax | actionlint -shellcheck= .github/workflows/deploy-and-evaluate.yml | Documented check; only if already installed; ../foundry-hosted-agents/docs/labs/lab-06-cicd.md:104-109 |
| Optional web contracts | python -m pytest apps/web-chat/tests -q -p no:cacheprovider; npm --prefix apps/web-chat/frontend test | Separate optional surface; ../foundry-hosted-agents/.github/workflows/web-chat-build.yml:31-49 and ../foundry-hosted-agents/apps/web-chat/frontend/package.json:7-9 |
| Bilingual docs/decks | Compare paired filenames, exercise IDs, durations, code blocks and links; inspect PPTX ZIP slide/notes counts | Read-only structural checks completed here; no Jekyll build, deck render or linguistic review |

Keep RUN_LIVE_STAGING_RISK unset and Cosmos disabled during offline checks. Live tests explicitly require opt-in and staging endpoints: ../foundry-hosted-agents/src/threat-assessment-agent/tests/test_live_risk.py:8-19. The full hosted evaluator expects converted JSON with a data array, not the raw golden JSONL; it validates the selected azd endpoint, invokes Azure, writes artifacts and incurs cost. It is not a cheap/offline validation command. Source: ../foundry-hosted-agents/eval/run_hosted_evaluation.py:368-405.

## Selective Adaptation Map

Recommended approach: retain the learning progression and small architecture, re-author the domain contract, and start with one reviewed vertical slice. This is preferable to wholesale copying the mature PoC or building all nine labs before the customer scope is known.

| Decision | Exact candidate scope |
| --- | --- |
| Keep conceptually | Lab 01's four-layer architecture; Lab 02's independent-tool smoke distinction; Lab 04's completion/history/isolation checks; Lab 05's deterministic-versus-judge split; Lab 08's evidence-status legend |
| Rewrite for the customer | Read-only use case, synthetic fixtures, prompts, parser/structured input contract, expected evidence, EN/FR examples and refusal tests, ownership/approval language, README and lab navigation |
| Adapt after technical validation | Minimal agent host/converter, two tool service contracts, versioned Toolbox connection, candidate metadata, SSE validator, isolated Bicep/environment parameter flow |
| Instructor-only or advanced | Lab 06 protected release walkthrough and false-green case; Lab 07 sanitized historical diagnostic reasoning; quota/throttling and positive-telemetry exercises |
| Defer unless required | Web chat/Entra pilot, Cosmos checkpoints, Agent 365, continuous production EvaluationRule, A2A, full production release pipeline, 36-slide executive comparison |
| Exclude from new baseline | Original tenant/project/group IDs, shared staging/production endpoints, credentials or environment files, support case data, original run evidence relabeled as new evidence, stale default invocation commands, vendor/cache trees |

Exact recommended next scope: produce a design-only EN/FR adaptation contract for one customer-approved synthetic, read-only scenario and two candidate tool contracts. Cover prework plus the 01-05 learning arc with a short readiness debrief; determine the actual duration from customer evidence before assigning times. Define matching EN/FR acceptance cases for ordinary evidence, missing data, conflicting signals, unsafe instructions, user corrections, and session isolation. Select one invocation/history contract and one learner deployment path. Only after approval and toolchain validation should implementation begin. No final FSI use case is selected by this research.

## Gaps and Next Research

* [ ] Confirm customer PDF-derived duration, skill profile, coaching model, language expectations and use case with the parent research track; the PDF was not read here.
* [ ] Freeze/review the final sibling working-tree changes before importing any source; verify committed and published parity independently.
* [ ] Discover and invoke the required Azure AI app best-practices tool when tool_search becomes available. No best-practices response was obtained here.
* [ ] Authorize a non-production compatibility check of exact azd/hosting SDK versions, session request schema, agent converter, tool transport and evaluator packages. Do not change persistence policy based on general documentation alone.
* [ ] Reconcile live evaluation/history commands with isolated learner names, then test both language tracks with the same expected evidence.
* [ ] Review FSI data classification, regional model SKU/residency, retention/deletion, logs and evidence redaction, private connectivity, tool auth, budget and reviewer ownership. Current public synthetic infrastructure is not approval for customer data.
* [ ] Render and review localized slides/site, verify image rights and redact customer-specific screenshots before reuse. ZIP counts and prose inspection do not certify layout, accessibility or translation quality.

Clarifying questions for the parent: What delivery time and participant roles does the customer evidence establish? Must agent interaction itself be French, or are bilingual instructions sufficient? Are learners permitted isolated Azure deployments, or must instructors provision a sandbox? Which read-only scenario and synthetic data are approved? What remains permitted as an attributed Air Canada case study?

## Validation

Progressive editor diagnostics passed. Read-only checks verified source instruction absence, tracked file inventory, working-tree status/HEAD, paired exercise counts, French metadata, and PowerPoint slide/notes counts. The first document validation caught out-of-range citations; those references were corrected and the changing deck source rechecked. Final validation checks the research marker, single H1, ASCII text, final newline, source path existence, and explicit citation bounds. It does not certify semantic accuracy of every line anchor in a concurrently changing tree. No application tests, live agent calls, installs, auth, deployments, or customer-resource inspection were executed.
