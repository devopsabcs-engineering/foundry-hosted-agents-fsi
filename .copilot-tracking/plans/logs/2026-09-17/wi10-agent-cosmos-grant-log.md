<!-- markdownlint-disable-file -->
# Planning Log: WI-10 — Hosted Agent Cosmos Data-Plane Grant

**Related Plan**: wi10-agent-cosmos-grant-plan.instructions.md

## Discrepancy Log

### Unaddressed Research Items

* None — research scope was fully consumed by the plan.

### Plan Deviations from Research

* DD-01: The staging agent's live instance identity
  (`f6ef6272-c2db-45f7-9071-6667ae65a37d`) does not resolve via `az ad sp show`
  (checked twice), yet a Cosmos SQL role assignment for that exact principal already
  exists in the staging Cosmos account. The plan proceeds to configure it anyway
  rather than blocking on Entra resolution, because:
  * Research: Cosmos SQL role assignments (`modules/cosmos-rbac.bicep`) do not
    validate `principalId` against Entra at write time — an incorrect value cannot
    fail the deployment, only silently grant the wrong principal.
  * Research: the identical symptom (agent principal not resolving in Entra) was
    already observed and resolved by simple elapsed time in the 2026-09-15
    private-networking session for production's identity.
  * Plan: proceeds with the live agents-API value as the source of truth (the same
    value the workflow's own defensive check already computes), cross-checked against
    the pre-existing Cosmos grant for the same principal, rather than requiring
    `az ad sp show` success as a gate.
* DD-02: The originally-tracked WI-10 wording ("`AGENT_PRINCIPAL_ID` remains unset")
  does not distinguish staging from production. Research found production's variable
  IS set (since 2026-09-16) and its Cosmos grant is live and confirmed via role
  assignment listing. The plan narrows scope to staging only, with production
  reduced to a functional-verification-only step (Phase 4.1) rather than
  reconfiguration.
* DR-03 (Major, found during plan validation 2026-09-17): The plan's per-step
  "Details:" line-number pointers are wrong for 6 of its 7 references — each lands
  inside the *preceding* step's content (or that step's Files/Success
  criteria/Context references/Dependencies metadata block) instead of the step the
  checklist item claims to describe. Verified by direct line-number search against
  the details file this session:
  * Research: not applicable — this is a plan/details internal cross-reference
    defect, not a research-coverage gap.
  * Plan implements: Step 1.1 → "(Lines 13-33)" is correct. Step 1.2 → "(Lines
    35-45)" actually lands in Step 1.1's Discrepancy references/Success
    criteria/Context references (real Step 1.2 content is lines 53-79). Step 2.1 →
    "(Lines 47-58)" lands in Step 1.2 (real Step 2.1 is lines 84-97). Step 3.1 →
    "(Lines 60-72)" lands in Step 1.2/Phase 2 boundary (real Step 3.1 is lines
    123-138). Step 3.2 → "(Lines 74-86)" lands in Step 2.1 (real Step 3.2 is lines
    152-171). Step 4.1 → "(Lines 88-98)" lands in Step 2.1 (real Step 4.1 is lines
    192-209). Step 4.2 → "(Lines 100-108)" lands in Step 2.1's metadata (real Step
    4.2 is lines 227+).
  * Rationale: the details file's per-step Files/Discrepancy references/Success
    criteria/Context references/Dependencies blocks appear to have been added or
    expanded after the plan's line numbers were computed, shifting every subsequent
    step down by roughly one step's worth of lines without the plan being re-synced.
  * Impact: does not block implementation (each step is still locatable by its
    heading text), but breaks the plan's traceability promise for nearly all its
    cross-references.
* DR-04 (Major, found during plan validation 2026-09-17): The research document, the
  plan's Derived Objectives, and the details file's Step 4.2 narrative text all cite
  `.copilot-tracking/plans/logs/2026-09-17/semantic-versioning-ci-tagging-log.md` as
  where WI-10 is "tracked" / must be marked resolved for the 2026-09-17 date. A direct
  search this session confirms that file contains zero occurrences of
  `AGENT_PRINCIPAL_ID` or "WI-10" — the actual mention lives in a different file,
  `.copilot-tracking/changes/2026-09-17/semantic-versioning-ci-tagging-changes.md`
  (line 135, a *changes* log, not a *planning* log).
  * Research: states "WI-10, tracked in
    `.../plans/logs/2026-09-17/semantic-versioning-ci-tagging-log.md`" (inaccurate).
  * Plan implements: repeats the same file reference verbatim in Derived Objectives
    and in Step 4.2's checklist wording ("mark WI-10 resolved in both the 2026-09-15
    and 2026-09-17 planning logs") — no DR-/DD- entry previously flagged this as an
    inherited citation error.
  * Rationale: the details file's own Step 4.2 "Files:"/"Context references:" lists
    correctly cite the changes-log path and line 135, so the authoritative file list
    is right even though the narrative text and plan checklist wording above it are
    wrong — an internal contradiction within the same step.
  * Impact: following the plan/narrative text literally would send an implementer to
    the wrong file (or find nothing to update there) at Step 4.2; only the details
    file's Files:/Context references list is accurate.
  * RESOLVED 2026-09-17: corrected the citation in the research document, the plan's
    Derived Objectives, and the details file's Step 4.2 narrative to point at
    `.copilot-tracking/changes/2026-09-17/semantic-versioning-ci-tagging-changes.md`.

* DR-03 RESOLUTION (2026-09-17): re-derived every step's actual line range by
  searching the details file for `^### Step|^## Implementation Phase` and computing
  ranges from the resulting headings. Updated all 7 "Details:" pointers in the plan
  to the corrected ranges (Step 1.1: 13-52, Step 1.2: 53-79, Step 2.1: 84-118, Step
  3.1: 123-151, Step 3.2: 152-187, Step 4.1: 192-226, Step 4.2: 227-256).

Note (Minor, formatting): DD-01 and DD-02 above were originally filed with a `DR-`
prefix, inconsistent with this repository's convention (`DR-` reserved for
"Unaddressed Research Items", `DD-` for this section). Renumbered to `DD-01`/`DD-02`
and the corresponding "Discrepancy references" pointers in the details file
(Step 1.1, Step 2.1) were updated to match.

* DD-03 (Major, found during implementation 2026-09-17, BLOCKING): Research's DD-01
  concluded that Cosmos SQL role assignments (`modules/cosmos-rbac.bicep`,
  `sqlRoleAssignments`) do not validate `principalId` against Entra at write time.
  Live implementation evidence contradicts this: `azd provision` against staging
  (workflow run 35249247909) failed on all 3 internal retries with an ARM
  `BadRequest`: "The provided principal ID [f6ef6272-c2db-45f7-9071-6667ae65a37d] was
  not found in the AAD tenant(s) [aa93b9d9-037d-4f08-a26d-783cff0e2369]" — the exact
  principal set in Phase 2, matching the exact live agent identity confirmed in
  Phase 1 and already holding a *pre-existing* Cosmos grant
  (`11e012aa-08b0-4e28-936a-f9111d869228`).
  * Research: stated no Entra validation occurs for this resource type.
  * Implementation: ARM rejected the deployment specifically because the principal
    doesn't resolve in the tenant — either (a) ARM does perform this check for at
    least some code path/API version even though the Bicep module's schema doesn't
    require it, or (b) the *existing* assignment for this same principal was created
    at an earlier moment when it *did* resolve, and the identity has since become
    unresolvable again (consistent with DD-01's observation that `az ad sp show`
    fails for it), and ARM re-validates on every deployment attempt rather than only
    at initial creation.
  * Impact: blocks Phase 3/4 entirely — the plan's approach (set the variable, then
    redeploy) cannot complete until the agent principal reliably resolves in Entra at
    deployment time. Per the plan's Step 4.3 escalation clause, no further automated
    retry was attempted.
  * Status: OPEN, escalated to user 2026-09-17. Needs additional research (see WI-04
    below) before a workaround is attempted — do not speculatively grant Graph
    permissions or make tenant-level changes.
  * FURTHER INVESTIGATION (2026-09-17, same day, at user's request): confirmed the
    ARM error's `ActivityId` line attributes it to
    `Microsoft.Azure.Documents.Common/2.14.0` — the Cosmos DB resource provider
    itself, not a separate classic `Microsoft.Authorization/roleAssignments`
    resource (`infra/main.bicep` only creates one RBAC-related resource for
    `agentPrincipalId`, the `cosmosAgentRbac` module). This confirms the Cosmos RP
    genuinely performs AAD validation for `sqlRoleAssignments.principalId`,
    contradicting DD-01/research outright (not a scope/config issue on our part).
  * Ruled out: re-checked `az ad sp show`, Graph v1.0 `directoryObjects/{id}`, Graph
    beta `servicePrincipals/{id}`, a `$filter=id eq '...'` query, and an
    eventual-consistency `$search` query — the principal 404s on every single path.
    This is not an auth/permission/consent gap on our access token (other objects,
    including production's own agent identity below, resolve fine with the same
    token), so **no interactive login or MFA step can fix this** — it is a genuine,
    tenant-wide absence of the object from every Graph query surface right now.
  * Cross-checked against production for comparison: `az ad sp show --id
    171dca8a-bda3-46ec-8121-a235ecee6e30` (production's currently-configured, working
    `AGENT_PRINCIPAL_ID`) resolves successfully, `displayName`
    "...-quote-preparation-agent-AgentIdentity" — confirming agent identities DO
    become classic-resolvable service principals once propagation completes; this is
    not an architectural exclusion for the Agent ID object type as a whole.
    Production's Cosmos account now has 3 role assignments: two duplicates for
    `171dca8a-...` (`bfe58d42-...`, `40683a67-...`, both created successfully post
    propagation — matches WI-02) and one orphaned assignment for a third, older
    principal (`c6ab63bf-914a-4f0e-a65b-5d17a7876823`, likely a prior stale identity).
  * Historical precedent re-examined: `.copilot-tracking/changes/2026-09-15/
    private-networking-changes.md` shows production hit the *identical* ARM
    `BadRequest` on 2026-09-15 for principal `4fcc9b60-d117-4d6c-912a-a3e206270403`
    — a **different** GUID than today's working `171dca8a-...`. This means
    production's resolution was NOT simply "the same identity eventually appeared" —
    the configured value changed to a different (newer) identity at some point
    between 2026-09-15 and 2026-09-17 that happened to already resolve. Staging's
    identity `f6ef6272-...`, by contrast, is unchanged since research and still does
    not resolve after being live for at least the multi-hour span covered by this
    session — there is no newer instance identity currently available from the
    agents API to substitute.
  * Conclusion: this is most consistent with Entra Agent ID propagation/replication
    lag for this specific object, not a fixable configuration, auth, or code defect.
    No further CLI/API remediation is available from this session; the only lever
    known to work (per the production precedent) is elapsed real time before a
    retry. Recommended NOT to keep re-dispatching the full staging deploy pipeline
    on short intervals (costs CI minutes and Azure spend for a predictably repeated
    failure) — retry after a longer wait (hours, not minutes) instead.

## Implementation Paths Considered

### Selected: Configure staging to match production's existing pattern

* Approach: set `AGENT_PRINCIPAL_ID` as a `staging`-environment-scoped GitHub Actions
  variable (mirroring `production`'s existing configuration), then redeploy so
  `infra/main.bicep`'s already-correct `cosmosAgentRbac` module applies the grant.
* Rationale: no code or Bicep change is needed — the gap is purely operational
  configuration, confirmed by tracing the entire mechanism end-to-end this session.
* Evidence: .copilot-tracking/research/2026-09-17/wi10-agent-cosmos-grant-research.md
  (sections "How the repo already models this" and "Variable scope").

### IP-01: Modify the workflow to auto-apply the live agent identity without an
  operator gate

* Approach: change the "Capture the Foundry project identity JSON" step to call
  `gh api .../environments/<env>/variables/AGENT_PRINCIPAL_ID` itself once the live
  value resolves in Entra, removing the manual step entirely.
* Trade-offs: fully automates WI-10 for all future deploys, but the existing step's
  own code comment explicitly documents why this was deliberately NOT done — "grabbing
  the wrong GUID ... would grant Cosmos write access to the wrong principal and still
  leave the agent unable to write." Given today's finding that the live identity can
  fail `az ad sp show` even when it is later confirmed correct (production's
  precedent), full automation risks silently granting an unverified principal on every
  run.
* Rejection rationale: out of scope for "work on WI-10 next," which is about closing
  the existing tracked gap, not redesigning the workflow's safety model. Recorded as
  WI-01 in Suggested Follow-On Work below for a future decision.

## Suggested Follow-On Work

* WI-01: Consider whether the "Capture the Foundry project identity JSON" step should
  auto-apply the live value once it is confirmed to resolve in Entra AND match a
  pre-existing Cosmos grant (a safer, narrower form of automation than IP-01's
  unconditional approach).
  * Source: Planning discussion, IP-01 rejection.
  * Dependency: none blocking; enhancement only.
* WI-02: Clean up the redundant Cosmos role assignment for the production agent
  principal (`171dca8a-...`) — two assignments exist for the same principal/role/scope
  (`bfe58d42-e8ee-5c32-b369-7670f7a20a58` and `40683a67-6907-4c86-b6f1-f78b254f52d2`).
  Harmless today but untidy; removing the extra one via `az cosmosdb sql role
  assignment delete` would match Bicep's single-assignment model.
  * Source: Research, "Production: already resolved" section.
  * Dependency: none blocking.
* WI-03: Investigate why `az ad sp show` fails for the staging agent's live instance
  identity despite an apparently-functional Cosmos grant already existing for it —
  the "Agent ID" Entra object type may not be visible through classic
  `servicePrincipals` Graph queries; confirm via the Microsoft Entra admin center's
  "Agent ID" blade (`entra.microsoft.com` > Entra ID > Agent ID) rather than `az ad
  sp show`, which was not explored this session.
  * Source: Research, "Why `az ad sp show` fails" section (open question).
  * Dependency: none blocking; informational only, would refine the workflow's
    defensive check if a better resolution method is found.
* WI-04 (blocking WI-10 completion): Determine why `azd provision`'s ARM deployment
  rejects `f6ef6272-c2db-45f7-9071-6667ae65a37d` as "not found in the AAD tenant"
  when creating/re-validating its Cosmos SQL role assignment, even though (a) an
  identical assignment for the same principal already exists and was presumably
  created successfully at some point, and (b) research (DD-01) found the Bicep
  module's resource type does not require Entra validation. Candidates to check:
  whether ARM's Cosmos RP performs its own directory lookup independent of the Bicep
  schema; whether the existing assignment predates a propagation-lag window and the
  identity has since become permanently unresolvable (vs. temporarily, as with
  production's earlier precedent); or whether a different resource in the same
  deployment (e.g., a role assignment scope, capability host, or connection) is the
  one actually triggering the check. This directly blocks WI-10's staging closure and
  must be resolved (or the plan's approach revised) before Phase 3 can succeed.
  * Source: Implementation, DD-03 (workflow run 35249247909).
  * Dependency: blocks Phase 3/4 of this plan.

## User Decisions

* None yet — no decision points required user input during planning; the selected
  path follows directly from tracing the existing, already-well-designed mechanism to
  its logical conclusion.
* PENDING (2026-09-17): Implementation is blocked on DD-03/WI-04 — the staging
  `azd provision` fails because the agent principal doesn't currently resolve in
  Entra. Awaiting user decision on how to proceed (e.g., wait and retry later for
  propagation, investigate via the Entra "Agent ID" admin blade per WI-03/WI-04
  first, or accept the blocker and close only the verification/documentation parts
  of WI-10 for now).
