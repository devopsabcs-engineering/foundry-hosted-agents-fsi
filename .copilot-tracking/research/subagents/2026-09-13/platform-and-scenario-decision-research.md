<!-- markdownlint-disable-file -->
# Platform and Scenario Decision Research

Status: Complete for Phase 2 research. Research date: 2026-09-13. Implementation, runtime verification and owner approvals remain gated.

## Questions and Boundaries

Evaluate synthetic Ontario auto-insurance quote preparation with mandatory employee approval against claims intake and card disputes. Compare nine adapted bilingual labs, a short workshop, and wholesale renaming. Verify current documented hosted-agent maturity, protocols, history, regions, networking, and security. Define an illustrative synthetic data contract and approval boundary, acceptance examples, and implementation gates.

Writes are restricted to this research report. No cloud operations, installations, application runs, secrets, or implementation changes are authorized. No callable tool_search is exposed; required deferred Azure tools cannot be loaded and were not invoked. Public Microsoft documentation retrieval is available independently.

## Evidence and Initial Decision

Both completed reports were read in full: .copilot-tracking/research/subagents/2026-09-13/air-canada-workshop-research.md and .copilot-tracking/research/subagents/2026-09-13/desjardins-customer-evidence-research.md. The context report and HVE Markdown/writing-style instructions were read. The research lint marker permits the existing tracking-document format without frontmatter.

Recommendation: reuse the nine-lab teaching arc, but introduce a deterministic synthetic calculator and application-owned approval store rather than treating narrative text or conversation history as approval. Customer PDF pages 8-9 directly support quotation preparation and pre-send employee approval. The sibling report establishes read-only tools, a tool-free composer, explicit store:false, and no baseline durable approval store.

The discriminating documentation check supports that separation: native history is documented, but does not itself satisfy employee authorization, revision binding, or replay protection. Illustrative JSON and negative structural examples were checked independently of prose; application controls remain unimplemented.

## Current Official Documentation

Retrieved directly with fetch_webpage on 2026-09-13. Page updated_at metadata is recorded separately from retrieval date. These are documentation claims, not observed tenant capabilities, quotas, deployments, security controls, or availability.

| ID | Official source and update date | Relevant sections and findings |
| --- | --- | --- |
| D1 | [Hosted agents](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents), updated 2026-09-10 | Protocols, identity, sessions/conversations/state store, versioning, private networking, region availability. Lists Canada Central and Canada East; per-session VM isolation, immutable versions, no traffic splitting. |
| D2 | [Runtime components](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/runtime-components), updated 2026-08-27 | Generate a response without storing; conversations and conversation items; security/data handling. Responses stored by default; store:false requires client-carried history. |
| D3 | [Agent Service overview](https://learn.microsoft.com/en-us/azure/foundry/agents/overview), updated 2026-08-27 | Agent types and enterprise capabilities: hosted custom code, tools, identity and BYO VNet. The retrieved overview does not provide a blanket hosted-agent GA/SLA assertion. |
| D4 | [Private networking](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/virtual-networks), updated 2026-08-27 | Template and Azure Developer CLI paths have materially different endpoint-privacy wording. Hosted injection must be configured at account creation; private ACR support depends on project creation date. |
| D5 | [Durable state store](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-state-store), updated 2026-09-10 | Explicit public preview, no SLA, not recommended for production. JSON items, ETags/If-Match, caller-derived user isolation; local runs cannot enforce that platform user isolation. |
| D6 | [Deploy a hosted agent](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent), updated 2026-09-11 | Container requirements: linux/amd64, protocol libraries, /readiness, local port 8088. Dedicated hosted endpoint, runtime agent identity distinct from project image-pull identity. SDK examples differ from sibling adapter. |
| D7 | [Hosted agent runtime contract](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agent-contract), updated 2026-08-27 | HTTP/1.1, readiness, protocol routes, graceful shutdown, verified platform headers and caller-supplied header forwarding. Resilient execution is labeled preview. |
| D8 | [Hosted agent quickstart](https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/quickstart-hosted-agent), updated 2026-08-27 | Multiple SDK/CLI paths; source deployment includes prerelease .NET APIs. Does not establish a blanket GA status or customer-environment support. |

### Maturity Finding

Do not label the entire September 2026 platform either GA or preview solely from a historical sibling slide. D1/D3/D8 omit a blanket hosted-agent preview banner but do not establish GA, an SLA, or production suitability. D5 explicitly labels the durable state store public preview without SLA; D7 labels resilient execution preview; D1 labels A2A preview; D4 retains preview-specific endpoint limitations. The defensible conclusion is documented hosted capability with feature-specific preview dependencies and unresolved overall maturity/terms for the intended deployment. Obtain the applicable service terms and platform-owner confirmation before implementation claims.

D6's example protocol declaration uses 1.0.0 while D7 explains identity propagation on container protocol 2.0.0 and D8's source deployment examples use 2.0.0. Those are protocol versions, not guessed package pins. The workshop must validate one exact adapter/protocol/client combination; do not combine snippets or inherit the sibling's unpinned hosting package. No runnable deployment commands or dependency versions are prescribed here.

### Protocol and History Decision

Select Responses for the conversational teaching path. D1/D6 document the dedicated gateway route `{project_endpoint}/agents/{name}/endpoint/protocols/openai/responses`; D6 REST examples use `api-version=v1`. Inside the container the route is `/responses`, not that gateway path. D2's general project route `/openai/v1/responses` with an agent reference is not interchangeable evidence for every hosted adapter/client combination.

D1/D6 also document `/invocations` for arbitrary JSON and raw SSE and `/invocations_ws` for duplex WebSocket. The corresponding gateway paths are `/agents/{name}/endpoint/protocols/invocations` and `/agents/{name}/endpoint/protocols/invocations_ws`. Activity bridges Responses to Microsoft 365 channels; A2A is explicitly preview. None is needed for this workshop's baseline. Port 8000 in the sibling MCP servers is not the hosted-agent protocol port.

D1 documents durable conversation history independent of compute; a session identifies isolated compute and persisted $HOME/files. Idle timeout is 2-60 minutes, default 15; sessions are permanently deleted after 30 days of inactivity. Do not treat session persistence as an indefinite approval ledger. D5 state-store items default to a 30-day idle window renewed by writes, not reads; never-expire is a creation option. Each item is limited to 1 MB.

Retain the sibling's explicit store:false plus application-carried history for the initial adaptation, subject to later compatibility testing. Its converter rejects conversation IDs, previous_response_id, and explicit store:true; that is an application restriction, not a current platform limitation. Sources relayed by the completed sibling report: ../foundry-hosted-agents/src/threat-assessment-agent/runtime_evidence.py:30-37 and ../foundry-hosted-agents/src/threat-assessment-agent/main.py:18-26. Native history requires a separately tested adapter migration, not removal of one guard. Neither history mode grants employee approval authority. store:false is not proof of zero retention across logs, application storage, sessions, or downstream services.

D7 confirms `POST /responses` returns JSON or `text/event-stream`, and `GET /readiness` returns 200 when ready. Default bind is 0.0.0.0:8088 with platform TLS termination; SIGTERM requires graceful shutdown. Do not invent /health or /liveness endpoints. D7's inner model-call store:false example coexists with platform-managed outer history; outer agent persistence and inner model response storage are different settings.

For container protocol 2.0.0, D7 documents platform-verified x-agent-user-id and opaque x-agent-foundry-call-id; SDKs forward the latter to Foundry services. They are not guaranteed locally. Caller-supplied x-client-* headers are forwarded but are not verified identity or reviewer roles. No approver may be authorized from chat, a JSON actorId, or an x-client-role header.

### Network and Security Decision

D1 lists Canadian hosted-agent regions, but neither D1 nor the customer PDF verifies deployment capacity, model/SKU availability, customer authorization, or end-to-end Canadian residency. The sibling uses GlobalStandard; do not infer Canadian-only processing from its Foundry resource region. The PDF's model names on page 10 are dated event inventory, not a selected or currently deployed model.

D4 requires network injection at Foundry account creation for hosted agents. The Foundry resource and VNet must share a region; use a dedicated delegated subnet for each Foundry resource, delegated to Microsoft.App/environments. Its portal path specifies /27 or larger and recommends /24 in limitations. DNS, private endpoints, image pulls, model/tool paths, Entra authentication egress, NSGs/firewalls, and a network-reachable runner all need later verification. Do not translate a generic Standard Setup's BYO Cosmos/Search/Storage prerequisites into a mandatory baseline dependency for this synthetic workshop.

D1/D4/D6 say projects created after June 25, 2026 support private ACR, while projects created before that date require public registry reachability. The exact boundary date and any actual project's capability need owner confirmation. Do not weaken registry policy to make the workshop work.

D4's template path describes denied public access and private inbound endpoints, while its Azure Developer CLI path says the agent endpoint itself stays publicly addressable in this preview. D1 describes network-isolated resources and BYO outbound networking without resolving that path-specific discrepancy. End-to-end private hosted ingress is therefore unverified for the selected toolchain/topology. Treat it as an implementation gate, not a feature promise or a claim that all hosted agents lack networking support.

D1/D6 distinguish platform-created runtime agent identity from project managed identity used for image pulls. External-resource permissions still require explicit RBAC. D4 notes recently renamed Foundry roles; confirm role IDs/dataActions and registry authorization mode rather than copying historical display names. The sibling's public MCP ingress and authType None are not an approved FSI security pattern. Use authenticated service access for any shared lab; local fixture-only mocks may have an explicit local-only exception.

Exclude secrets from prompts, images, fixtures, logs and authored configuration; use approved identities/connections. Treat tool text as untrusted input. Collect tool receipts and state transitions, not hidden chain of thought. Telemetry may contain customer content (D6); synthetic-only inputs, minimization, access controls and retention apply even to a teaching system. Positive correlated trace evidence is required before declaring observability healthy.

## Scenario Decision

Select synthetic Ontario auto-insurance quote preparation, with mandatory employee review before any simulated applicant-facing preview. This directly matches assets/Hackathon - Rencontre prep des coachs.pdf, physical pages 8-9, as established by the completed customer evidence report. Approval is mandatory before sending in the original challenge; this adaptation intentionally stops at a training preview and never sends anything. Business benefit is a hypothesis to measure with preparation-time proxies, not a claim of improved sales.

| Candidate | Evidence fit | Teaching value and bounded action | Decision |
| --- | --- | --- | --- |
| Ontario quote preparation | Explicit PDF challenge, pages 8-9 | Structured intake, deterministic synthetic amounts, cited training rules, persisted pre-preview employee gate, EN/FR parity | Recommended; clearly mark every offer as simulated and nonbinding |
| Claims intake | Insurance adjacency only; no claim challenge in PDF | Completeness checklist, conflicting evidence, adjuster packet; no coverage, liability, settlement or payment decisions | Alternate only if scope is deliberately changed; loses direct quotation/efficiency alignment |
| Card dispute packet | General FSI relevance only; no dispute challenge in PDF | Synthetic ledger/timeline and evidence gaps; no refund, account block, fraud determination or chargeback | Third choice; more domain setup and weaker evidence fit |

The calculator is an invented training mapping, not underwriting. Do not use real applicant/member data, VINs, addresses, licence/card numbers, real premiums, proprietary rate tables or real policies. Do not claim FSRA approval, statutory compliance, actuarial validity, Desjardins product equivalence, quote validity periods or binding authority. Ontario is scenario context, not evidence that toy rules implement Ontario insurance law. Unknown cases are unsupported training inputs, not declined insurance applications.

## Delivery Format Decision

| Option | Advantages | Costs and limits | Recommendation |
| --- | --- | --- | --- |
| Adapt all nine labs | Preserves setup-to-readiness arc and technical depth; gives engineering learners reusable offline and hosted evidence gates | Requires new fixtures, calculator, approval persistence and runtime bilingual tests; not all nine fit a short live session | Canonical deliverable: nine mirrored EN/FR labs, developed from one validated vertical slice |
| Short 150-180 minute workshop | Fits mixed-role facilitated learning using preverified starters; foregrounds employee approval and evidence | Cannot also teach provisioning, CI/CD, RBAC diagnosis and readiness in depth; timing is unpiloted | Optional route through the same nine-lab assets, not a competing implementation or claim of all-lab completion |
| Wholesale rename | Lowest apparent authoring effort | Transfers airline concepts, English parsers, historical endpoints/security posture, stale commands, and unearned readiness evidence; no durable employee gate | Reject |

The sibling report lists detailed lab times totaling 305 minutes versus a 290-minute index; advertised three/six-hour formats are not verified throughput. The customer's PDF describes two competition days, not a nine-lab workshop duration. Budget the full curriculum provisionally as a technical day or split sessions with prework, coaching and breaks; pilot before publishing a timed agenda. The shorter customer report estimate is a delivery subset, not evidence that nine labs can be completed in three hours.

### Nine Bilingual Labs

Each lab needs matching EN/FR objectives, exercise IDs, prerequisites, executable steps, expected outputs, failure explanations, knowledge checks and navigation. Retain canonical API identifiers in both languages. Use one shared deck model with localized content and speaker notes, and review rendered EN/FR decks and site separately. Runtime bilingual parity is an additional gate, not a consequence of translated prose.

| Lab | Reused teaching step | New exercise and acceptance evidence |
| --- | --- | --- |
| 00 | Setup and fixtures | Approved synthetic boundaries, language selection, preverified tools/access; parse fixtures and calculate expected amounts without any LLM |
| 01 | Architecture | Trace intake, evidence, calculator, composer and separate approval backend; identify which component can read, calculate, persist or approve |
| 02 | MCP implementation/hosting/registration/consumption | Two read-only MCP services, fixed allowlists, direct versus Toolbox access, unknown/timeout/schema-failure cases; no write tools |
| 03 | Hosted deployment | Instructor-approved isolated environment and validated Responses contract; record adapter/protocol/model/identity/image evidence without embedding credentials |
| 04 | Invocation and state | Paired EN/FR intake and correction; create draft, persist review, approve/reject/revise, reload after backend restart, deny cross-case access; approved preview only |
| 05 | Evaluations | Exact calculator/state/citation/permission tests plus language quality review; injection, stale approval, missing data and fabricated-authority failures |
| 06 | CI/CD | GitHub checks and reviewer-protected promotion as teaching artifacts; fail on missing EN/FR evidence or skipped required tests; a CI approval is not business quote approval |
| 07 | Troubleshooting and RBAC | Diagnose transport versus authorization versus missing fixture evidence, store outage and concurrency conflicts; use sanitized historical incidents, not tenant-admin exercises |
| 08 | Readiness decision | Demonstrate success and blocked paths, retain evidence limits, assemble README/one-pager/slides/demo with source attribution and owner-gated next steps |

Short route after prework: 20 minutes boundaries/fixtures (00-01), 35 tools/calculation (02 and prepared 03), 35 approval paths (04), 30 EN/FR evaluation (05), and 30-60 evidence/demo (08). Labs 06-07 remain follow-on/instructor walkthroughs. These estimates reproduce the 150-180 minute proposal transparently; no timing has been piloted.

### What Is Reused and Replaced

Reuse the sibling's deterministic orchestration and tool-free composition concept, not a claim of autonomous parallel specialists. Its fixed graph executes evidence before assessment: ../foundry-hosted-agents/src/threat-assessment-agent/graph.py:519-564. Its toolbox performs allowlisted retrieval before tool-free summarization: ../foundry-hosted-agents/src/threat-assessment-agent/toolbox.py:18-80. These source citations are relayed from the completed sibling report, not a new inspection of its changing worktree.

Retain the four-layer MCP explanation, evidence receipts, strict terminal SSE checks, deterministic-versus-judge distinction, isolated environments and conditional readiness decisions. Replace all airline prompts, regex labels, fixtures, UI samples, golden outputs, branding, screenshots, run/version evidence and identity references. Freeze the sibling source before importing selected code; its report observed uncommitted changes at HEAD 2e10a60e168bd6707d0f5dae380d6d595430b077.

Do not inherit English-only runtime tests as bilingual coverage. The sibling's paired docs explicitly retain English test prompts; its graph parser and golden cases remain English (../foundry-hosted-agents/src/threat-assessment-agent/graph.py:41-115; ../foundry-hosted-agents/eval/golden-dataset.jsonl:1-8). Replace substring citation checks with exact fixture/rule references and structured result equality. Resolve its staging-only live-check guard before designing learner commands.

## Historical Brief and Workflow Reconciliation

The cover is May 2026. Hackathon May 19-20, technical evaluations May 27-28, and final June 8, 2026 are past as of September 13, 2026 (PDF pages 1, 3-4, 13). Present this as a reuse brief derived from a past planned event, not a future invitation, confirmed event outcome, or new booking. Do not assign replacement dates. Listed models/resources and LIDIA access on pages 3 and 10 are historical planned inventory, not a current entitlement.

PDF page 12 prohibits GitHub Copilot for the competition and requires attribution of assistance. That does not establish a ban on GitHub source control or GitHub Actions. The user's GitHub repository/workflow can remain the adaptation authoring path; this research is not a competition submission or a waiver of that rule. Provide a Copilot-free learner path using reviewed starter code and ordinary editing. Any preparatory or later-event use of Copilot needs organizer policy confirmation; disclose authoring assistance rather than hide it.

The original submission channels remain DevOps for code/README and SharePoint for slides/one-pager/video (PDF pages 12-13). A GitHub workflow alone does not satisfy those submission rules. For any actual reuse under competition conditions, export or mirror approved deliverables through the required channels after permission, without assuming access. Do not add a GitHub Copilot SDK dependency merely because current Foundry docs list it as a framework option.

PDF pages 3-4 give 30-minute technical evaluations; page 13 gives 25 minutes. No source resolves which governed the event. For the reusable demo, design a 25-minute envelope: 3 context, 5 architecture/control boundaries, 7 happy and blocked demonstrations, 5 evaluation/evidence, 5 questions. If a 30-minute slot is confirmed, use the extra 5 for questions. This is a planning convention, not a correction to the PDF. Keep the separate May 20 16:00 submission deadline historical; do not confuse it with 16:30 day-end activities. Coaching durations also conflict (10 versus 15 minutes, pages 5-6) and are not copied into a new agenda.

## Proposed Application Boundary

One hosted Python orchestrator contains logical intake and rules/evidence specialists plus a tool-free composer. Retain LangGraph conceptually to reduce adaptation churn; do not introduce a framework migration without a demonstrated need. A separate workshop backend owns draft construction, calculator validation, approval persistence and the reviewer view. This is a proposal, not implemented code or an approved deployment architecture.

| Component | Permitted behavior | Forbidden behavior |
| --- | --- | --- |
| Synthetic intake MCP | get_application(fixtureId) reads an allowlisted fixture by opaque ID | SQL passthrough, arbitrary file paths, writes, identity assignment, approval |
| Synthetic reference MCP | get_rulebook(rulebookId) reads immutable training rules and lookup tables | Real policy/rating queries, dynamic rule creation, arbitrary URLs, writes, approval |
| Deterministic calculator | Pure validation and integer-cent lookup/addition over approved inputs and pinned rulebook; backend recomputes before saving draft | LLM arithmetic, inferred missing fields, guessed discounts/taxes/risk factors, production pricing |
| Narrative agent | Ask for clarification, propose normalized inputs, summarize supplied evidence in EN/FR | Authorize reviewer, mutate workflow state, change calculator output, issue or send a quote |
| Workshop backend | Validate confirmed inputs, recompute draft, persist transitions, gate training preview | Trust model-written state/amount/identity; emit email, webhook, insurer transaction or binding offer |
| Employee simulation | Explicit reviewer action on the exact stored draft through a separate control | Approval through applicant chat, model self-approval, implied enterprise identity assurance |

MCP read-only annotations are descriptive, not enforcement. Expose only the two named operations, authorize service access and case ownership at the backend, disable write handlers and use immutable fixture files. Tool arguments and returns need strict schemas and size/time limits. Unknown ID, missing fixture, timeout, malformed response and inconsistent rulebook version must remain distinct errors; none means an empty successful result or permission to invent an amount. No prompt can change connection names or the tool allowlist.

Natural-language intake may propose normalized fields, but the applicant must confirm changes through structured application controls. Only confirmed canonical input is passed to calculation. Enforce ownership before resolving a fixture/case ID; synthetic identifiers and conversation IDs are not secrets or proof of access. The model can receive a sanitized authoritative state summary, but subsequent commands must reread stored state.

### Minimal Persisted Approval Store

Add an ApprovalRepository abstraction implemented for the workshop by a small SQLite-backed store in the separate, single-instance workshop backend on its own retained teaching volume. Use database transactions, unique command keys, monotonically increasing recordVersion and immutable draft revisions. Reopening the same database after process restart must recover pending and approved records; deleting the volume intentionally resets the lab. A test-only in-memory double is not the acceptance implementation.

Do not put this shared approval database in an agent session's $HOME: the applicant and reviewer may have different sessions; session expiry and identity partitioning are not a shared business workflow. Do not expose ApprovalRepository as a third MCP service or give the agent a review credential. Backend persistence adds a small stateful application dependency to the sibling's read-only baseline; it does not activate its optional Cosmos checkpointer or change its conversation converter. The overall application is no longer read-only, even though both MCP services remain read-only.

The SQLite design is intended to demonstrate sequential and concurrent-command correctness within one backend and one database after implementation and testing, not HA, multi-replica storage, tamper-proof audit, disaster recovery, regulatory retention or production security. A process with database-write access could alter it. Cloud hosting of that backend/volume, backup and recovery remain a separate authorized design gate. Do not claim a managed Foundry sandbox or ephemeral Container Apps filesystem provides that guarantee automatically.

D5's Foundry state store is a documented optional future adapter: ETags help avoid lost updates, but its preview status, caller-derived user partitioning, hosted-only access and local-isolation limits require design/testing for an applicant-to-employee workflow. Do not assume an employee can read another user's isolated store or assume multi-item transactions. An application-owned database remains the baseline recommendation for a visibly separate human authority boundary.

### State Machine and Atomic Commands

| Current state | Command and actor | Next state | Mandatory precondition |
| --- | --- | --- | --- |
| INCOMPLETE | Confirm complete inputs, application controller | DRAFT | Schema-valid supported fixture inputs and recomputed amount; otherwise remain INCOMPLETE or UNSUPPORTED |
| DRAFT | Submit for review, application controller | PENDING_REVIEW | Immutable draft revision created; all cited rule/fixture versions resolved |
| PENDING_REVIEW | Approve, simulated employee | APPROVED | Server-authorized reviewer, exact draftRevision and expected recordVersion; record actor/time/command key |
| PENDING_REVIEW | Reject, simulated employee | REJECTED | Same concurrency/identity checks; bounded reason code required |
| DRAFT, PENDING_REVIEW, APPROVED, REJECTED | Revise confirmed business input, application controller | DRAFT, INCOMPLETE or UNSUPPORTED | New immutable draft revision; clear effective approval/preview, preserve prior audit; recompute |
| APPROVED | Open training preview, application controller | APPROVED | Atomically recheck same current approved revision and active rulebook, add one preview receipt |
| Any | New active rulebook supersedes bound rules | DRAFT or UNSUPPORTED after recomputation | Prior approval cannot authorize a new calculation; new revision/review needed |

UNSUPPORTED means outside the toy dataset, never an underwriting denial. Only revise can recover from UNSUPPORTED into supported draft preparation. Missing evidence leaves the workflow INCOMPLETE with its specific calculation issue, not approved or implicitly rejected. No state named SENT, ISSUED, BOUND or DELIVERED exists. A preview receipt records a mock action, not applicant delivery. Intake prompts/status can be shown before approval, but draft amounts and offer narratives remain employee-facing until an approved training preview. Generate that preview from authoritative structured fields and reviewed localized templates, not uncontrolled agent text. The applicant channel exposes bounded intake/status templates, never the raw employee-facing composer stream.

Each command transaction first checks trusted actor/ownership and an actor-scoped idempotency key. Same key and same request returns the original receipt without a second event, even if its expectedRecordVersion is now old; same key with different request is a conflict. A replayed receipt is historical evidence, not permission to display a superseded preview. For new commands, check expected recordVersion, current state, exact draft revision and current rulebook version; write state, audit event and receipt together, then commit. Stale version or draft revision is a conflict; never silently retry an approval on a newer draft. Two simultaneous approve/reject commands yield one success and one conflict. Store unavailable or commit uncertain means no preview until durable state/receipt is recovered. Preview reads always recheck current effective approval.

The mock reviewer uses a clearly labeled server-controlled workshop actor context in a separate review interaction. Client-supplied actorId is never sufficient; persisted actorId is server-authored. This teaches the approval boundary, not verified employment. Any shared remote version requires real authentication, case-level authorization, protected review endpoints and anti-forgery controls before exposure; a role-switch widget alone is not security.

Switching display locale preserves canonical business fields and approval state. Changing any business fact, calculated amount, rule version or approved free-text content invalidates approval. Baseline preview uses versioned reviewed templates, so mere formatting does not create a new offer. Reject stale previews and do not reuse an old preview receipt after revision.

## Illustrative JSON Contract

The following is a complete training-fixture envelope and its JSON Schema draft-07, not a deployed API or a real insurance contract. No ellipses or external schema references are needed. The rulebook and expected calculation are test data, not model output. The calculator consumes input plus the pinned rulebook; it must not read expectedCalculation to produce its answer. Workflow and nextCommand are test seeds for the separate approval backend, never trusted client authorization.

The immutable business snapshot is (fixtureId, draftRevision, jurisdiction, vehicleClass, plan, rulebook, calculation). The fixture's expectedCalculation is the oracle for the backend's recomputed calculation. input.locale is a presentation preference, excluded from business revision comparison; original audit entries remain immutable when the display language changes. Revisions append new snapshots under the same case ID. Overwriting an existing revision with different business content fails. workflow.recordVersion controls mutable concurrency independently of draftRevision. rulebook.version is immutable; the backend maintains its active version in the approval transaction's database, after validating fetched content.

Do not return this entire test envelope through MCP. get_application returns only the requested synthetic input record (fixtureId and input); get_rulebook returns the immutable rulebook. The definitions below supply their field constraints; narrow request/response wrappers must also reject extra fields. expectedCalculation, workflow, nextCommand and expectedDisplay are test-only expectations and never evidence obtained from an applicant or a tool. Define explicit typed transport-error wrappers during implementation, preserving the distinct error categories above.

Synthetic arithmetic: select baseCents by vehicleClass and add planAddOnCents by plan. COMPACT plus TRAINING_EXTENDED is 80000 + 20000 = 100000 CAD cents per fictional training year. All values are pedagogical constants; no taxes, instalment fees, risk assessment or real policy coverage is represented. Only ON is supported by this exercise. Missing fields take precedence over unsupported values; evidence retrieval failure takes precedence over calculation; all non-READY outcomes have null amounts. No coercion of strings, fractions or negative cents is permitted.

French labels below use JSON Unicode escapes to retain ASCII research formatting; a JSON parser decodes real French accents. Published French materials must use natural reviewed French, not literal escape sequences. The timestamp is a fixed synthetic test clock, not a workshop date or real approval event.

### Fixture

```json
{
	"contractVersion": "training-1",
	"dataClass": "SYNTHETIC_ONLY",
	"fixtureId": "CASE-SYN-001",
	"input": {
		"locale": "fr-CA",
		"jurisdiction": "ON",
		"vehicleClass": "COMPACT",
		"plan": "TRAINING_EXTENDED"
	},
	"rulebook": {
		"id": "RULEBOOK-SYN-ON",
		"version": "training-1",
		"authority": "WORKSHOP_AUTHORS_ONLY",
		"notice": {
			"en-CA": "Training simulation only. Not an insurance quote. No delivery.",
			"fr-CA": "Simulation de formation uniquement. Ceci n'est pas une soumission d'assurance. Aucun envoi."
		},
		"currency": "CAD",
		"period": "TRAINING_YEAR",
		"baseCents": { "COMPACT": 80000, "SEDAN": 90000 },
		"planAddOnCents": { "TRAINING_BASIC": 0, "TRAINING_EXTENDED": 20000 },
		"rules": [
			{ "id": "RULE-SYN-BASE", "kind": "BASE_LOOKUP" },
			{ "id": "RULE-SYN-PLAN", "kind": "PLAN_LOOKUP" },
			{ "id": "RULE-SYN-REVIEW", "kind": "EMPLOYEE_GATE" }
		]
	},
	"expectedCalculation": {
		"status": "READY",
		"amountCents": 100000,
		"currency": "CAD",
		"period": "TRAINING_YEAR",
		"ruleIds": ["RULE-SYN-BASE", "RULE-SYN-PLAN", "RULE-SYN-REVIEW"],
		"issues": []
	},
	"workflow": {
		"caseId": "CASE-SYN-001",
		"draftId": "DRAFT-SYN-001",
		"draftRevision": 1,
		"recordVersion": 2,
		"state": "PENDING_REVIEW",
		"approvedRevision": null,
		"previewRevision": null,
		"audit": [
			{
				"sequence": 1,
				"commandId": "CMD-CREATE-001",
				"action": "CREATE_DRAFT",
				"fromState": "INCOMPLETE",
				"toState": "DRAFT",
				"draftRevision": 1,
				"actorId": "MOCK-CONTROLLER-001",
				"actorRole": "APPLICATION_CONTROLLER",
				"at": "2026-01-01T12:00:00Z"
			},
			{
				"sequence": 2,
				"commandId": "CMD-SUBMIT-001",
				"action": "SUBMIT",
				"fromState": "DRAFT",
				"toState": "PENDING_REVIEW",
				"draftRevision": 1,
				"actorId": "MOCK-CONTROLLER-001",
				"actorRole": "APPLICATION_CONTROLLER",
				"at": "2026-01-01T12:01:00Z"
			}
		]
	},
	"nextCommand": {
		"commandId": "CMD-REVIEW-001",
		"caseId": "CASE-SYN-001",
		"draftRevision": 1,
		"expectedRecordVersion": 2,
		"action": "APPROVE",
		"reasonCode": "REVIEWED"
	},
	"expectedDisplay": {
		"en-CA": "Employee approval required",
		"fr-CA": "Approbation d'un employ\u00e9 requise"
	}
}
```

### Schema

All objects reject additional properties. Null input values represent missing facts explicitly. UNKNOWN enum values and non-ON two-letter jurisdictions allow out-of-scope acceptance fixtures without pretending those inputs are valid for calculation. The schema is structural: reference equality, arithmetic, identity, audit continuity, state transitions and concurrency require the semantic tests below.

```json
{
	"$schema": "http://json-schema.org/draft-07/schema#",
	"title": "Synthetic quote preparation training fixture",
	"type": "object",
	"additionalProperties": false,
	"required": ["contractVersion", "dataClass", "fixtureId", "input", "rulebook", "expectedCalculation", "workflow", "nextCommand", "expectedDisplay"],
	"properties": {
		"contractVersion": { "const": "training-1" },
		"dataClass": { "const": "SYNTHETIC_ONLY" },
		"fixtureId": { "$ref": "#/definitions/caseId" },
		"input": { "$ref": "#/definitions/input" },
		"rulebook": { "$ref": "#/definitions/rulebook" },
		"expectedCalculation": { "$ref": "#/definitions/calculation" },
		"workflow": { "$ref": "#/definitions/workflow" },
		"nextCommand": { "$ref": "#/definitions/command" },
		"expectedDisplay": { "$ref": "#/definitions/localized" }
	},
	"definitions": {
		"caseId": { "type": "string", "pattern": "^CASE-SYN-[0-9]{3}$" },
		"revision": { "type": "integer", "minimum": 1, "maximum": 1000000 },
		"nullableRevision": { "anyOf": [{ "$ref": "#/definitions/revision" }, { "type": "null" }] },
		"cents": { "type": "integer", "minimum": 0, "maximum": 10000000 },
		"commandId": { "type": "string", "pattern": "^CMD-[A-Z0-9-]{1,48}$" },
		"state": { "enum": ["INCOMPLETE", "UNSUPPORTED", "DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED"] },
		"localized": {
			"type": "object", "additionalProperties": false,
			"required": ["en-CA", "fr-CA"],
			"properties": {
				"en-CA": { "type": "string", "minLength": 1, "maxLength": 500 },
				"fr-CA": { "type": "string", "minLength": 1, "maxLength": 500 }
			}
		},
		"input": {
			"type": "object", "additionalProperties": false,
			"required": ["locale", "jurisdiction", "vehicleClass", "plan"],
			"properties": {
				"locale": { "enum": ["en-CA", "fr-CA"] },
				"jurisdiction": { "type": ["string", "null"], "pattern": "^[A-Z]{2}$" },
				"vehicleClass": { "enum": ["COMPACT", "SEDAN", "UNKNOWN", null] },
				"plan": { "enum": ["TRAINING_BASIC", "TRAINING_EXTENDED", "UNKNOWN", null] }
			}
		},
		"rulebook": {
			"type": "object", "additionalProperties": false,
			"required": ["id", "version", "authority", "notice", "currency", "period", "baseCents", "planAddOnCents", "rules"],
			"properties": {
				"id": { "const": "RULEBOOK-SYN-ON" },
				"version": { "type": "string", "pattern": "^training-[1-9][0-9]*$" },
				"authority": { "const": "WORKSHOP_AUTHORS_ONLY" },
				"notice": { "$ref": "#/definitions/localized" },
				"currency": { "const": "CAD" },
				"period": { "const": "TRAINING_YEAR" },
				"baseCents": {
					"type": "object", "additionalProperties": false,
					"required": ["COMPACT", "SEDAN"],
					"properties": { "COMPACT": { "$ref": "#/definitions/cents" }, "SEDAN": { "$ref": "#/definitions/cents" } }
				},
				"planAddOnCents": {
					"type": "object", "additionalProperties": false,
					"required": ["TRAINING_BASIC", "TRAINING_EXTENDED"],
					"properties": { "TRAINING_BASIC": { "$ref": "#/definitions/cents" }, "TRAINING_EXTENDED": { "$ref": "#/definitions/cents" } }
				},
				"rules": {
					"type": "array", "minItems": 3, "maxItems": 3, "uniqueItems": true,
					"items": {
						"type": "object", "additionalProperties": false,
						"required": ["id", "kind"],
						"properties": {
							"id": { "enum": ["RULE-SYN-BASE", "RULE-SYN-PLAN", "RULE-SYN-REVIEW"] },
							"kind": { "enum": ["BASE_LOOKUP", "PLAN_LOOKUP", "EMPLOYEE_GATE"] }
						}
					}
				}
			}
		},
		"calculation": {
			"type": "object", "additionalProperties": false,
			"required": ["status", "amountCents", "currency", "period", "ruleIds", "issues"],
			"properties": {
				"status": { "enum": ["READY", "INCOMPLETE", "UNSUPPORTED", "EVIDENCE_UNAVAILABLE"] },
				"amountCents": { "anyOf": [{ "$ref": "#/definitions/cents" }, { "type": "null" }] },
				"currency": { "const": "CAD" },
				"period": { "const": "TRAINING_YEAR" },
				"ruleIds": {
					"type": "array", "uniqueItems": true, "maxItems": 3,
					"items": { "enum": ["RULE-SYN-BASE", "RULE-SYN-PLAN", "RULE-SYN-REVIEW"] }
				},
				"issues": {
					"type": "array", "uniqueItems": true, "maxItems": 6,
					"items": { "enum": ["MISSING_JURISDICTION", "MISSING_VEHICLE_CLASS", "MISSING_PLAN", "UNSUPPORTED_INPUT", "EVIDENCE_UNAVAILABLE", "RULE_VERSION_MISMATCH"] }
				}
			},
			"if": { "properties": { "status": { "const": "READY" } } },
			"then": { "properties": { "amountCents": { "$ref": "#/definitions/cents" }, "ruleIds": { "minItems": 3 }, "issues": { "maxItems": 0 } } },
			"else": { "properties": { "amountCents": { "type": "null" }, "issues": { "minItems": 1 } } }
		},
		"workflow": {
			"type": "object", "additionalProperties": false,
			"required": ["caseId", "draftId", "draftRevision", "recordVersion", "state", "approvedRevision", "previewRevision", "audit"],
			"properties": {
				"caseId": { "$ref": "#/definitions/caseId" },
				"draftId": { "type": "string", "pattern": "^DRAFT-SYN-[0-9]{3}$" },
				"draftRevision": { "$ref": "#/definitions/revision" },
				"recordVersion": { "$ref": "#/definitions/revision" },
				"state": { "$ref": "#/definitions/state" },
				"approvedRevision": { "$ref": "#/definitions/nullableRevision" },
				"previewRevision": { "$ref": "#/definitions/nullableRevision" },
				"audit": { "type": "array", "minItems": 1, "maxItems": 100, "items": { "$ref": "#/definitions/event" } }
			},
			"if": { "properties": { "state": { "const": "APPROVED" } } },
			"then": { "properties": { "approvedRevision": { "$ref": "#/definitions/revision" } } },
			"else": { "properties": { "approvedRevision": { "type": "null" }, "previewRevision": { "type": "null" } } }
		},
		"event": {
			"type": "object", "additionalProperties": false,
			"required": ["sequence", "commandId", "action", "fromState", "toState", "draftRevision", "actorId", "actorRole", "at"],
			"properties": {
				"sequence": { "$ref": "#/definitions/revision" },
				"commandId": { "$ref": "#/definitions/commandId" },
				"action": { "enum": ["CREATE_DRAFT", "SUBMIT", "APPROVE", "REJECT", "REVISE", "OPEN_PREVIEW", "RULES_CHANGED"] },
				"fromState": { "$ref": "#/definitions/state" },
				"toState": { "$ref": "#/definitions/state" },
				"draftRevision": { "$ref": "#/definitions/revision" },
				"actorId": { "type": "string", "pattern": "^MOCK-[A-Z0-9-]{1,48}$" },
				"actorRole": { "enum": ["APPLICATION_CONTROLLER", "EMPLOYEE_SIMULATION"] },
				"at": { "type": "string", "format": "date-time" }
			}
		},
		"command": {
			"type": "object", "additionalProperties": false,
			"required": ["commandId", "caseId", "draftRevision", "expectedRecordVersion", "action", "reasonCode"],
			"properties": {
				"commandId": { "$ref": "#/definitions/commandId" },
				"caseId": { "$ref": "#/definitions/caseId" },
				"draftRevision": { "$ref": "#/definitions/revision" },
				"expectedRecordVersion": { "$ref": "#/definitions/revision" },
				"action": { "enum": ["APPROVE", "REJECT", "OPEN_PREVIEW"] },
				"reasonCode": { "enum": ["REVIEWED", "REQUIRES_REVISION", "TRAINING_PREVIEW"] }
			},
			"oneOf": [
				{ "properties": { "action": { "const": "APPROVE" }, "reasonCode": { "const": "REVIEWED" } } },
				{ "properties": { "action": { "const": "REJECT" }, "reasonCode": { "const": "REQUIRES_REVISION" } } },
				{ "properties": { "action": { "const": "OPEN_PREVIEW" }, "reasonCode": { "const": "TRAINING_PREVIEW" } } }
			]
		}
	}
}
```

Review command payloads deliberately contain no actor/role fields. The trusted server context supplies them when creating audit events and command receipts. Receipts retain the complete normalized command including reasonCode, prior/result recordVersion and result status in the same transaction as the event. The bounded audit array is a fixture representation, not a recommendation to truncate a real audit trail at 100 events. Case ownership and authorized reviewer assignments live in backend access control, not this public fixture.

### Validation Acceptance Examples

| ID | Given or mutation | Required result and verification layer |
| --- | --- | --- |
| V01 | Complete fixture above | Schema passes; exact rule IDs/kinds resolve once each; integer arithmetic equals 100000; state pending, no approval/preview |
| V02 | Amount is "100000", -1, or 100000.5; extra premiumOverride or actorId in nextCommand | Schema rejects; no coercion and no write |
| V03 | READY has null amount, or INCOMPLETE has non-null amount | Schema rejects conditional inconsistency |
| V04 | Missing plan (null), supported jurisdiction/class | Input schema passes; calculator returns INCOMPLETE, null amount, MISSING_PLAN; no submit/approve/preview |
| V05 | QC jurisdiction or UNKNOWN class | Input schema passes; calculator returns UNSUPPORTED, null amount, UNSUPPORTED_INPUT; no insurance-denial language |
| V06 | Structured amount is 99999, all other fields unchanged | Schema may pass; semantic calculator equality fails and blocks draft save |
| V07 | Rule IDs resolve to wrong kinds, duplicate IDs with different kinds, stale rule version, or unknown fixture | Semantic provenance check fails; no narrative claim of retrieved evidence |
| V08 | Timeout, invalid MCP schema or unavailable rulebook | EVIDENCE_UNAVAILABLE with null amount; no fallback rates, no approval; distinguish transport versus unsupported input |
| V09 | Trusted employee context executes nextCommand on the pending fixture | One durable APPROVE event: recordVersion 3, approvedRevision 1, state APPROVED; server-authored actor and receipt |
| V10 | Same approval command replayed; then same key with valid REJECT/REQUIRES_REVISION payload | Identical replay returns original receipt without another event; changed payload conflicts |
| V11 | Applicant or agent asks "approve me" / "approuve ma demande"; or forges client role/header | No review transaction or approval event; unauthorized access denied regardless of narrative |
| V12 | Pending/rejected/incomplete draft requests OPEN_PREVIEW | State gate denies; no amount-bearing applicant output or preview receipt |
| V13 | Revision changes after approval, then stale OPEN_PREVIEW or APPROVE arrives | New revision clears effective approval; stale commands conflict; new review required |
| V14 | Concurrent approve and reject both use recordVersion 2 | Exactly one commits; loser conflicts; audit, state and receipts agree after reload |
| V15 | Backend restarts with retained database, then reads current case | Same pending/approved state, immutable draft and receipts; lost conversation history cannot erase approval or invent it |
| V16 | Store down or transaction result uncertain | No preview; recover/reconcile receipt before retry; an exception is not success |
| V17 | Another workshop user guesses caseId/draftId/sessionId | Authorization denies before lookup exposure; no case contents in response or logs |
| V18 | Correct approved revision and authorized OPEN_PREVIEW | One mock preview receipt; state remains APPROVED; deterministic bilingual template, no outbound delivery integration |
| V19 | EN/FR paired run or switch display language mid-review | Same canonical inputs, tool plan, rule/fixture refs, amount and state; only localized display changes |
| V20 | User/tool text claims FSRA authority, asks for real quote/send, embeds instruction to override price | Refuse unsupported authority/action in both languages; no amount/state/tool-permission changes; evidence text is untrusted |
| V21 | Incomplete SSE, missing terminal success, missing evaluator result, skipped required EN/FR case | Fail completion/release gate; partial text or a completed job is insufficient evidence |

V04/V05/V08 are calculator-boundary tests, not merely edits to an otherwise READY envelope. Regenerate their expected workflow seeds consistently. Once a case has an unresolved issue, it cannot be PENDING_REVIEW or APPROVED. Failure results must use issue codes consistent with status. The semantic validator checks these cross-object invariants, case ID equality across the envelope, matching draft/command revisions, sequential audit continuity and approvedRevision == current draftRevision. JSON Schema alone cannot establish any of those dynamic guarantees.

All future business-path tests run as EN/FR pairs with independent case stores and normalized trace comparison. Use at least six synthetic cases: ordinary, missing input, unsupported input, conflicting correction, malicious instruction, and reject/revise/reapprove. Add timeout/retry/isolation/concurrency cases as reusable faults rather than manufacturing more business datasets. French normalization and terminology must be explicitly reviewed; do not use English regex labels as the only parser. Refusals, uncertainty, error messages and no-authority notices require both automated assertions and bilingual human review.

LLM judging is supplementary for groundedness, clarity and language quality. Deterministic arithmetic, authorization and approval-state tests are non-negotiable gates; a high judge score cannot override a failed control. Require every mandatory paired case to execute and pass, not an average that masks one language. Publish measured latency/preparation-step counts only as synthetic experiment results with model/version/run IDs, never projected business outcomes or regulatory compliance.

## Implementation Gates

Research supports the scope, not permission to start deployment. The following gates have not been executed or approved in this phase.

| Gate | Owner and evidence needed | Blocks |
| --- | --- | --- |
| G1 Scope and policy | Workshop sponsor: approve synthetic/nonbinding/no-delivery framing, nine-lab versus short route, EN/FR requirement, reusable-brief dates and Copilot/submission policy | Publishing a customer/event-branded workshop |
| G2 Tool discovery | Engineering owner: load required Azure AI guidance through tool_search when available; record actual tool output, not inferred advice | Implementation workflow that requires those tools |
| G3 Platform terms and access | Platform owner: documented maturity/SLA/preview acceptance, approved project/model/SKU, hosted region, quota/concurrency/cost budget and learner permissions | Cloud runs or availability claims |
| G4 Networking and identity | Security/platform owners: resolve D4 ingress discrepancy; account/project creation constraints, private DNS/egress/ACR, tool auth, reviewer identity/ownership and telemetry access | Shared or remote exposure |
| G5 Reproducible toolchain | Engineering: freeze selected sibling source, pin a verified dependency set, validate protocol/client/adapter/Toolbox transport, linux/amd64 build and explicit history behavior | Runnable lab instructions or deployments |
| G6 Domain and approval | Business/governance reviewer: sign off synthetic terminology and versioned rules; engineer verifies pure calculation, immutable drafts, transactions, restart recovery, idempotency and concurrent decisions | Declaring core workflow complete |
| G7 Bilingual execution | EN/FR reviewer and evaluator owner: paired behavior/trace parity, verified references and localized refusals; render site/deck and test links/navigation | Bilingual completion claim |
| G8 Evidence and pilot | Instructor: execute positive/negative tests, SSE/evaluator fail-closed gates, timing pilot, budget/cleanup plan and source attribution | Workshop release/readiness recommendation |

If hosted execution cannot be approved or verified, offer a clearly labeled local fixture replay of calculation and approval logic. It does not satisfy the hosted-agent deployment or hosted identity-isolation learning outcomes. Do not remove privacy controls or bypass missing permissions to preserve a demo schedule.

## Evidence Limits and Next Research

Both source reports were read completely; PDF page citations here are inherited from the customer's completed extraction report, not a fresh PDF rendering. Its page 6 layout/timing uncertainty remains unresolved. Sibling source line citations are inherited observations dated 2026-09-13, with the recorded changing-worktree caveat. Current official pages were freshly retrieved in this phase and do not validate that source snapshot.

The VS Code Foundry wrapper and core skill were read; no setup/sub-workflow was entered because it can install software or perform cloud operations. tool_search is genuinely absent from the callable surface. No deferred Azure resource, model, authentication or AI guidance tool was called without loading. Required Azure tool verification is unavailable, not successful or silently substituted with CLI access. This is a research limitation that does not prevent the scenario decision.

No cloud calls, authentication, dependency installs, application runs, model invocations, real insurance calculations or delivery occurred. No SDK package lock, tool transport compatibility, pricing, quota, live availability, SLA, customer access, production approval, data residency or compliance certification was verified. Documentation discrepancies are retained rather than resolved by assumption.

* [ ] Obtain owner decisions for G1 and G3-G4, including service terms and exact private-ingress topology.
* [ ] Complete required Azure guidance/tool discovery when available, without bypassing the loading prerequisite.
* [ ] Authorize a narrow compatibility spike and freeze the source/toolchain before authoring runnable instructions.
* [ ] Implement and test calculator/approval boundaries first; then adapt all nine EN/FR labs from that verified slice.
* [ ] Pilot timing and bilingual execution, render localized assets, and gather new evidence before release.

No clarifying question blocks Phase 2 research. Missing policy, access and deployment decisions are implementation gates, not assumed customer commitments.

## Validation

Local document checks passed: research marker, one H1, nine lab rows, policy/state/platform coverage, ASCII text and final newline. PowerShell parsed both JSON blocks and Test-Json validated the full fixture against the embedded schema. Exact 100000-cent arithmetic, case/version references, rule-ID/kind mapping and initial audit continuity passed.

Ten mutation checks passed: string/negative/fractional amounts, forged actor field, READY/null, INCOMPLETE/non-null, pending approval revision, and action/reason mismatch were rejected; EN locale and a structurally valid but arithmetically wrong amount passed the schema as expected. The latter demonstrates why an independent semantic calculator check is required. No proposed calculator implementation, transaction engine, authentication, restart, concurrent command, live EN/FR agent or deployment test ran. Those acceptance examples remain future implementation gates. The complete report was reread for final review; editor diagnostics and source-reference integrity are checked separately below.

Final integrity checks passed for nine labs, 21 acceptance examples, eight implementation gates, the fixture/schema, six sibling source paths and line bounds, and source report/PDF existence. Earlier editor diagnostics reported no errors; final editor diagnostics are run after this validation-record update. Reference integrity does not constitute a fresh semantic audit of the sibling source or a PDF visual review.
