<!-- markdownlint-disable-file -->
# Workshop Context Research

Status: Context research complete; full workshop research remains in progress. Date: 2026-09-13.

## Topics and Questions

Establish verified local anchors, applicable authoring rules, skill boundaries, the cheapest document check, and independent scopes for Air Canada adaptation and customer PDF evidence. Do not extract or invent PDF findings in this initial pass.

## Verified Findings and Evidence

* README.md, line 1 contains only the repository title.
* Root inventory contains .git/, README.md, and assets/. Asset inventory contains only assets/Hackathon - Rencontre prep des coachs.pdf; contents and page count remain unknown.
* Explicit checks found no AGENTS.md or .github/copilot-instructions.md in the target or ancestors through the drive root.
* ../foundry-hosted-agents/README.md describes a nine-lab English/French workshop, docs/labs/ and docs/fr/ content, and a companion deck. Only the README was inspected, so child paths remain reported anchors.
* The sibling README reports LangGraph orchestration, separate synthetic MCP services, role-restricted tools, a tool-free composer, and evaluation gates. It explicitly limits fixture results and pilot claims; do not convert those claims into Desjardins readiness evidence.
* The sibling README's conversation warning conflicts with its basic direct-invoke example. Resolve the intended invocation path during lab research.

## Applicable Authoring Rules

* Follow the supplied HVE Task Researcher template for the primary document. Begin tracking research with <!-- markdownlint-disable-file -->; this is exempt from the supplied general Markdown rules, including frontmatter-first requirements.
* Keep local references plain and workspace-relative. Use ../foundry-hosted-agents/ for sibling anchors. External links are allowed.
* Write concise, precise prose with descriptive headings, ASCII punctuation, and a final newline. Avoid em dashes and bold-prefix bullets.
* For later non-exempt workshop Markdown, use required title/description frontmatter and no duplicate H1. Preserve real French accents where appropriate.
* Modify only .copilot-tracking/research/ with apply_patch, then run focused validation immediately.

## Skill Guidance

* PDF: Use existing local pdf-parse or pdftotext tooling, retain page references, and flag extraction/layout uncertainty. No installs, cloud uploads, or alternate output folders.
* Brainstorming: Gather constraints first, compare two or three approaches, then recommend one; ask one unresolved question at a time.
* Foundry: The VS Code wrapper and main Foundry skills were read in the required order. No dependency setup ran because it can install packages. No Foundry execution workflow was entered.
* Best-practices blocker: tool_search is absent from the callable tool surface. The listed deferred foundrytk-get_agent_code_gen_best_practices tool was not called without required discovery. Parent should discover and invoke it before implementation plans/code when available.
* Previously supplied memory reinforces that runnable instructions need execution evidence. No sibling or future workshop command was executed here.

## Independent Research Scopes

### Air Canada Adaptation

Read sibling-specific instructions before expanding beyond ../foundry-hosted-agents/README.md. Inspect the reported docs, lab navigation, EN/FR mirror, decks, and nearby validation/build entry points. Return verified paths with line references, learning outcomes, timing/prerequisites if documented, reuse/change/remove recommendations, and stale-command risks. Do not read the customer PDF or choose the final FSI use case. Write only to .copilot-tracking/research/subagents/2026-09-13/air-canada-adaptation-research.md.

### Customer PDF Evidence

Read assets/Hackathon - Rencontre prep des coachs.pdf with an available local extraction tool, without installing anything. Return page-cited facts on audience, agenda, coaching expectations, constraints, use cases, and success criteria; distinguish quotations, paraphrases, and inference. Preserve unknowns and sensitive details conservatively. Do not inspect sibling labs or design the workshop. Write only to .copilot-tracking/research/subagents/2026-09-13/customer-pdf-evidence-research.md.

## Suggestions, Not Customer Facts

* Compare adapting the existing lab progression against a shorter customer-specific progression once both evidence tracks return.
* A synthetic member-dispute intake and evidence-summary workflow is a possible distinct FSI scenario, subject to customer fit and human-review boundaries. It is not selected.

## Validation and Remaining Work

Cheapest check: PowerShell text assertions for leading comment, primary template headings, pending-evidence markers, no local Markdown links, and final newline; then editor diagnostics. No project test runner or Markdown lint configuration was visible in the root inventory.

Validation result: PowerShell structure checks passed for both files after correcting final newlines. Editor diagnostics reported no errors. Manual final review completed; workshop execution and PDF contents remain unverified.

* Pending: Air Canada lab-level research
* Pending: Page-attributed customer PDF evidence
* Pending: Required AI best-practices discovery and current official Foundry verification
* Pending: Evidence-backed FSI choice and bilingual completion criteria

## Clarifying Questions

None blocks the two research scopes. Ask the user about duration, participant skills, language terminology, scenario preference, and approved environments only where the PDF does not answer them.

## Primary Research Artifact

.copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md
