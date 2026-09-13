<!-- markdownlint-disable-file -->
# Desjardins Customer Evidence Research

Status: Complete for local PDF evidence and scenario comparison. Date: 2026-09-13. Runtime feasibility and organizer confirmations remain unverified.

## Topics and Questions

Extract page-cited evidence from assets/Hackathon - Rencontre prep des coachs.pdf on goals, audience, dates and agenda, language, constraints, judging, suggested use cases, technologies, and data or access assumptions. Compare three practical FSI workshop scenarios and recommend one, separating customer statements from inferred opportunities.

## Method and Boundaries

Source: assets/Hackathon - Rencontre prep des coachs.pdf. Context: .copilot-tracking/research/subagents/2026-09-13/workshop-context-research.md. The newer request names this output and explicitly adds scenario evaluation; it supersedes the narrower output name and scope suggested in the context.

Used existing Git-bundled pdftotext.exe with -enc UTF-8 -layout. The first extraction used the executable's default encoding; re-extraction with explicit UTF-8 removed replacement characters. Node packages were unavailable; no packages were installed. No authentication, uploads, deployments, or customer-system calls occurred.

Extraction artifact: .copilot-tracking/research/subagents/2026-09-13/desjardins-customer-evidence-extracted.txt. It contains 16 form-feed-delimited pages, all nonempty, with zero Unicode replacement characters after correction. Citations below use one-based physical PDF pages, including title and section-divider pages. The final slide is numbered 16.

The text-layer hypothesis was supported. Layout extraction preserves broad column structure, but page 6 time-to-activity pairing remains ambiguous. No companion PDF renderer was found in the same Git tool directory; slides were not visually rendered. Do not treat uncertain row alignment as verified timing. Text extraction does not establish whether images contain additional unextracted details.

All evidence is paraphrased except short product or training names. Findings describe a May 2026 preparatory deck, not independently verified event outcomes. Its May and June dates are past as of this research date. Only research artifacts were intentionally written; no application or workshop implementation was changed.

## Customer Evidence

### Goals and Audience

| Topic | Explicit evidence | PDF pages |
| --- | --- | --- |
| Document purpose | Preparatory meeting for hackathon coaches, issued by the AI practice governance/development and data-valorization team; cover dated May 2026 | 1 |
| Event goal | Second Desjardins AI hackathon, focused on agentic AI, to stimulate internal experimentation, develop AI talent, and accelerate adoption of Desjardins technological capabilities identified as PDM | 2 |
| Broader value | Explore internal-data opportunities, develop expertise on target technologies, encourage interdisciplinary collaboration, and accelerate adoption of the Desjardins Azure environment | 16 |
| Participants | Up to 75 employees in 15 multidisciplinary, cross-sector teams; data professions and business profiles; organizing committee forms teams based on profiles and sectors | 3 |
| Technical audience | Data scientists, data engineering and machine-learning engineering/MLOps advisers, and data-valorization analysts, supported by Desjardins business experts | 2 |
| Meeting agenda | Coach introductions, hackathon execution and coach contributions, questions and discussion | 2 |
| Language | Slide prose is French, with English technology and course names. The deck does not prescribe French-only, English-only, or bilingual teaching, judging, or user interfaces | 1-16 |

Do not expand PDM or internal organizational acronyms without another source. An audience that includes technical roles is not evidence that all participants know Python, container development, or hosted-agent APIs.

### Dates and Agenda

| Date or period in 2026 | Planned activity | PDF pages |
| --- | --- | --- |
| March 11-25 | Registration | 3 |
| From April 10 | Recommended asynchronous DataCamp preparation: AI Agent Fundamentals, 6 hours; Microsoft Azure Fundamentals (AZ-900), 9 hours | 4 |
| May 5 | Mandatory in-person business workshop at EY; business needs/value, processes and responsibilities in agentic AI, pitch/storytelling | 4 |
| May 12 | Virtual technical workshop, mandatory for technical profiles; agentic AI, Azure/tools, platform | 4 |
| May 13 and 15 | Optional/as-needed virtual connectivity clinics | 4 |
| May 19-20 | Hackathon at Maison du developpement durable, Montreal; challenge presentation, solution design and construction | 3-4 |
| Day 1, 09:00-17:00 | Welcome, introductions, challenge/rules/platform/data briefing, initial team programming without environment access, LIDIA access, coaching clinics, programming/presentation preparation, closing | 6 |
| Day 2, 08:30-16:30 | Programming/presentation preparation, coaching and debrief, lunch, further programming, cocktail at 16:30; schedule may be adjusted | 7 |
| May 20, 16:00 | Solution submission deadline | 13 |
| May 21-26 | Technical committee reviews submitted solutions | 13 |
| May 27-28 | Virtual technical evaluations | 3-4, 13 |
| May 29 | Finalist announcement | 4, 13 |
| June 1-5 | Finalist pitch preparation with coach access; page 13 specifies a 30-minute pitch consultation | 5, 13 |
| June 8 | In-person final at Espace Desjardins, Montreal, with finalist presentations and awards | 3-4, 13 |

Timing uncertainties: pages 3-4 describe 30-minute technical evaluations; page 13 says 25 minutes. Page 5 proposes 15 minutes per team per competition day for business and governance coaching; page 6 says 10 minutes for the first business clinic. Page 6's flattened columns do not justify assigning exact times to LIDIA access or each briefing. Retain the 16:00 submission deadline separately from day-end activities.

### Challenge and Human Approval

Pages 8-9 identify one concrete challenge: an agentic exchange with an applicant seeking a vehicle-insurance quote in Ontario. The stated business objective is greater quotation-process efficiency through reduced human effort, improved sales, or both.

Page 9 requires at least one interaction with a Desjardins employee to obtain approval of the quote before sending it to the applicant. This is an explicit release gate, not merely a recommendation to review afterward. The deck does not define premiums, underwriting algorithms, approval implementation, insurance eligibility criteria, or binding authority.

No other concrete challenge is specified. Page 16's references to internal-data and business-problem opportunities are broad themes, not evidence that claims, card disputes, credit decisions, or fraud scenarios were requested.

### Coaching and Delivery Constraints

Page 5 defines four support roles: two business coaches, eight technical coaches, four governance/oversight coaches, and two to four pitch coaches. Technical expertise includes agentic/generative AI and Azure/LIDIA, with contributions from Desjardins, EY, and Microsoft. Technical support covers connectivity, tools/methodologies, and participant guidance throughout the competition.

Governance coaching covers AI ethics, data governance, security, organizational requirements, and responsible practices. Business coaches keep solutions focused on the business challenge; pitch coaches support business/executive presentations. Page 14 asks all non-pitch coaches to arrive at the hackathon venue by 10:00 on May 19 and notes that technical training and Microsoft coach contributions still need finalization.

Page 12 requires a runnable, easy-to-use prototype suitable for limited evaluation time, constructive collaboration, and source attribution, including assistance from chatbots, StackOverflow, or other people. It explicitly prohibits GitHub Copilot for the competition. Penalties or disqualification are indicated for rules/submission issues, without a detailed sanction schedule.

This research is not a competition submission. A future workshop must not assume that Copilot-assisted coding is permitted: ask whether the prohibition also applies to preparatory learning. No blanket ban on every chatbot or every AI coding tool can be inferred from the named prohibition.

### Judging and Deliverables

Page 12 lists six technical dimensions without numerical weights or score thresholds:

* Relevant use of agentic AI
* Human-in-the-loop and control of agents
* Domain data and business rules
* Prototype quality and robustness
* Measurement, observability, and control
* Responsible AI, data, and ethics applied to agents

The four business dimensions are business-problem relevance, business value/impact, feasibility/scalability/transferability, and pitch/demo quality. The top six teams after technical evaluation advance to the business round (page 12).

Required submissions are code and a README through DevOps, plus presentation slides, a one-pager, and video/demo through SharePoint (pages 12-13). Page 11 provides a challenge-sheet template for current/target state, business need, risks, requirements, governance, milestones, KPIs, stakeholders, solution architecture, the model's role/decisions/limits/governance, and expected impact. Template examples such as conformity and satisfaction targets are prompts, not supplied compliance requirements or numerical targets.

### Technologies and Data or Access Assumptions

| Named resource | Explicit statement | Evidence boundary | PDF pages |
| --- | --- | --- | --- |
| Microsoft Azure and LIDIA | Hackathon uses the LIDIA lab Azure environment, accessible from a Desjardins computer | Does not grant this researcher or a future workshop access; no topology, role, quota, region, or current availability evidence | 3, 5-6 |
| Azure OpenAI | LLMs GPT-5-mini and GPT-4.1-mini; embeddings text-embedding-3-small | Listed event models, not verified current deployments or workshop selections | 10 |
| AI Search | Available service | No index schema, corpus, retrieval configuration, or capacity supplied | 10 |
| SQL database | Database with data included | No engine edition, schema, provenance, sensitivity classification, or synthetic-data guarantee supplied | 10 |
| Storage account | Available resource | No dataset paths or access policy supplied | 10 |
| Functions App | Python and container options | Does not establish hosted-agent service availability | 10 |
| Container registry and App service | Available resources | Registry, hosting topology, and permissions unspecified | 10 |
| SharePoint | Hackathon documents, data/business rules, and deliverable drop folder | Actual files, rules, URLs, and permissions are absent | 10 |
| DevOps | Code snippets for interaction with Azure resources; code/README submission | No repository URL, credentials, or pipeline configuration provided | 10, 12-13 |
| DataCamp | Recommended agent and Azure foundations preparation | Recommendations are not proof of course completion | 4 |

Microsoft Foundry hosted agents, Agent Framework, LangGraph, MCP, and a specific multiagent architecture are not named in the PDF. They belong to the requested workshop direction, not verified customer infrastructure. The PDF does not establish private networking, identity setup, approved model regions, external access, data residency, retention policy, or production readiness.

## Inferred Workshop Opportunities

The following are research recommendations, not customer commitments or tested implementation plans. All three teach a small hosted orchestrator coordinating two specialist roles, with synthetic read-only tools and a human-controlled final release. Use a single hosted runtime with logical specialist agents as the minimal concept; separately hosted specialists are optional, subject to later platform verification. More agent instances are not intrinsically better against the relevance criterion on page 12.

### Ranking

| Rank | Scenario | Customer-evidence fit | Hands-on practicality | Main limitation |
| --- | --- | --- | --- | --- |
| 1 | Ontario auto-insurance quote preparation and employee approval | Direct match to pages 8-9; approval, domain rules, measurement, and explanation map to pages 11-12 | High with fixed synthetic offers and a starter scaffold | Must avoid implying real pricing, underwriting, or quote issuance; actual rules and hosted runtime remain unverified |
| 2 | Auto-insurance claim intake and adjuster handoff | Inferred adjacent insurance scenario; no claim-processing request in the PDF | High for document completeness and evidence summaries | Less faithful to the explicit quotation/sales challenge; avoid coverage or settlement decisions |
| 3 | Member card-dispute evidence packet and reviewer handoff | Inferred FSI scenario, not a documented Desjardins challenge or system | Moderate; event timelines demonstrate orchestration and evidence handling | Requires additional domain definitions and synthetic records; avoid fraud verdicts, refunds, and chargebacks |

Ranking is qualitative, not a customer scoring rubric. It prioritizes the stated challenge, a demonstrable human gate, bounded business rules, and achievable exercises over product breadth.

### 1. Ontario Auto-Insurance Quote Preparation

The learner builds an assistant that collects a fictional applicant's information and prepares a clearly labeled simulated quotation for employee review. A hosted orchestrator coordinates an intake specialist and a rules/evidence specialist. A deterministic read-only tool returns a fixed training offer from a small invented table; the model never invents a premium, eligibility decision, or policy condition. Unsupported situations produce a request for human review, not a guessed offer.

Use roughly six fictional applicant/vehicle fixtures, a short invented rulebook with stable rule IDs, fixed offer IDs, and paired French/English interactions. None is represented as an actual Desjardins rule, premium, member record, or legally valid Ontario policy. Preserve identical identifiers, amounts, and approval state across languages. Provide equivalent EN/FR learner instructions, exercises, expected outputs, and error explanations; bilingual support is a user requirement, not a deck assertion.

Bounded exercises: complete missing fields; attach rule and fixture references to the draft; prevent applicant-facing release while review is pending; approve, reject, or revise a draft; invalidate approval when the underlying draft changes; replay paired EN/FR cases. A staff view shows the inputs, retrieved rules, fixed offer, uncertainty, and decision history rather than hidden model reasoning. The orchestrator cannot approve its own output; any approver simulation is visibly labeled and does not constitute verified enterprise identity.

Acceptance evidence: no unapproved releases in the fixture suite; no premium/offer outside the fixture table; all recommendation statements linked to evidence; rejected or incomplete cases remain blocked; EN/FR results preserve the same business facts. Trace role transitions, tool calls, approval status, elapsed time, and failures without retaining unnecessary personal-like fields. A run summary can demonstrate efficiency proxies, but cannot establish actual sales improvement or production compliance.

### 2. Auto-Insurance Claim Intake and Adjuster Handoff

A hosted orchestrator coordinates an intake/completeness specialist and an evidence-summary specialist. Read-only tools retrieve fictional incident forms, vehicle records, and a small training checklist. The workflow prepares a case packet for a simulated adjuster; it does not accept/deny coverage, determine liability, estimate settlements, or issue payment.

Use four synthetic incident cases, invented document extracts, and paired EN/FR descriptions. Exercises cover a missing incident date, conflicting dates across documents, evidence citations, and an incomplete packet routed back for clarification. Provide mirrored learner instructions and a bilingual claimant/reviewer experience with consistent case IDs and findings. Show a human reviewer which checklist items are satisfied, unresolved, or contradictory, with their source records.

Approval controls release of the draft packet to a simulated queue. Acceptance checks require source-backed summaries, unchanged facts across languages, visible conflicts, and no release before reviewer approval. This is comparatively bounded and practical with a starter scaffold, but its connection to the deck is insurance adjacency and shared evaluation criteria (pages 9, 11-12), not an explicit claims use case.

### 3. Member Card-Dispute Evidence Packet

A hosted orchestrator coordinates a transaction-timeline specialist and an evidence-gap specialist, using a fictional transaction ledger and invented procedural checklist. It assembles a member's dispute narrative, supporting events, and missing information for review. No real bank connection, payment execution, account block, fraud classification, chargeback, or refund decision is permitted.

Use four synthetic disputes with fabricated merchants, dates, amounts, and evidence IDs, without real card numbers. Paired EN/FR member conversations and mirrored learner exercises cover a duplicate charge, missing receipt, conflicting merchant dates, and an unsupported policy question. The staff-facing explanation cites ledger events and checklist IDs, distinguishing facts from unresolved assertions.

Human approval gates release to a simulated case queue. Acceptance checks cover balanced evidence summaries, refusal to invent a transaction or policy deadline, translation consistency, and blocked unapproved releases. This teaches multi-source orchestration but introduces more domain setup than quotation preparation and has no direct challenge evidence in the deck; it ranks third despite broad FSI relevance.

### Recommendation and Workshop Scope

Select scenario 1. Its applicant conversation, Ontario auto-insurance context, efficiency objective, and mandatory pre-release employee approval directly match page 9. Evidence-linked rules, traces, a runnable prototype, and an intelligible demonstration map to pages 11-12. The alternative scenarios change the business problem without stronger customer evidence.

Proposed hands-on core, not a customer agenda: allow approximately 150-180 minutes after environment access and starter-project verification. Allocate 20 minutes to synthetic fixtures and business boundaries, 35 to specialist routing/tools, 35 to the approval state machine and blocked paths, 30 to bilingual replay and traces, and 30-60 to a measured demonstration and submission evidence. This is a scoping estimate, not an executed duration or a substitute for the two-day event schedule.

Keep provisioning and platform troubleshooting in a separately verified prerequisite track. If hosted-agent availability or access is not approved, use a local replay to teach logic and label hosting as unverified; do not claim that replay meets the hosted-execution learning outcome. If preparation follows competition rules, do not require GitHub Copilot. Use starter code and ordinary editing until organizers clarify allowed assistance.

Build the demo around one successful reviewed quotation plus a rejected draft, missing facts, and a language-switch case. Deliver a compact architecture view, source-attribution record, reproducible instructions, test evidence, one-page business summary, slides, and a short demo aligned to pages 11-13. Scalability and transferability should be discussed as limitations and future questions, not proven by a handful of synthetic tests.

## Gaps and Clarifying Questions

These do not block the research recommendation, but they block a faithful implementation or event plan:

* Is this a preparatory workshop, a retrospective adaptation, or a later event? Confirm duration and dates rather than presenting the May-June 2026 schedule as upcoming.
* Does the GitHub Copilot prohibition also apply to preparatory workshops, and what assistance/source-attribution rules govern them?
* Must learner materials, support, demos, and judging all support both languages? French slide language alone does not answer this.
* Is a Foundry hosted-agent runtime actually approved and available in the workshop environment? Confirm access, roles, model availability, region, networking, and resource budget through authorized owners.
* What published challenge rules and data can be reused? The deck names SharePoint and SQL content but provides neither the content nor its licensing, provenance, sensitivity, or access authorization.
* Will organizers approve an entirely synthetic quote-preparation adaptation with invented fixed offers and no real underwriting? Who validates the scenario's terminology and educational boundaries?
* How should employee approval be represented for learning, and what approval evidence must the demonstration retain? A simulated reviewer is not an enterprise identity control.
* Which timing is authoritative: 25 or 30 minutes for technical assessment, and 10 or 15 minutes for coaching consultations? Confirm day-1 time/activity mapping if exact agenda replication is needed.
* Are more detailed judging weights, rubric anchors, deliverable templates, and prohibited-tool rules available? They are not provided in this PDF.

### Recommended Next Research

* [ ] Confirm organizer policies, timing conflicts, and bilingual expectations.
* [ ] Obtain an authorized description of the challenge data and rules without assuming system access.
* [ ] Verify current official hosted-agent capabilities and approved environment prerequisites before producing runnable instructions.
* [ ] Map the recommended scenario to reusable workshop assets in the independent adaptation research; no sibling lab inspection was performed here.
* [ ] Pilot the synthetic exercises and EN/FR equivalence checks before committing to the duration estimate.

## Validation

Document format, required sections, and three-scenario coverage assertions passed. Extraction completeness and UTF-8 checks passed: 16 nonempty pages and zero replacement characters. Critical page-level evidence checks passed for the challenge/approval gate (page 9), prohibited tool and judging (page 12), and conflicting technical-evaluation durations (pages 3 and 13). Final document review completed; editor diagnostics reported no errors. No runtime, deployment, or compliance validation was attempted.
