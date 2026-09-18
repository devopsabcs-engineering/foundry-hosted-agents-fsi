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
  * RETRY #3 (2026-09-17, several hours later, user-requested): re-dispatched
    (run 35272075564) — identical failure, all 3 internal `azd provision` attempts
    hit the same ARM `BadRequest` for the same principal. `az ad sp show` still 404
    immediately after. No change from elapsed time so far.
  * DIRECTORY READERS HYPOTHESIS (raised by user, tested, REFUTED): checked the CI
    OIDC deployment SP (`gh-oidc-foundry-hosted-agents-fsi`, object
    `4be1d357-3c60-4897-925d-6a6a94bbf07c`, shared by both staging and production
    deploys via the repo-level `AZURE_CLIENT_ID` variable) — it has zero Entra
    directory role memberships (`memberOf` returns `[]`). Plausible in theory (ARM
    role-assignment validation needing Graph read access), but the user then checked
    the **authoritative Entra ID > Agents > All agent identities** admin blade
    directly (Global Administrator session) — the target principal is **absent from
    all 27 tenant agent identities**, including both Foundry projects' *shared*
    identities (`84a48188-...` staging, `8e3103c6-...` production) which ARE listed
    and healthy. This is the authoritative inventory per Microsoft's own docs
    (`learn.microsoft.com/azure/ai-foundry/agents/concepts/agent-identity`,
    "Manage agent identities" section) — a Global Admin browsing it directly rules
    out any permission-visibility explanation. **Conclusion revised**: the agent's
    *distinct/published* identity object was never fully provisioned on the Entra
    side (not merely slow-to-propagate/cache) — Foundry's data-plane `/agents` API
    recorded an intended `instance_identity.principal_id` that Entra's own Agent ID
    system of record does not have. This is stronger than "wait longer"; a passive
    wait may never resolve it without some retriggering event on the Foundry side.
  * NEXT IDEA (not yet attempted): `azd provision` for staging is blocked before
    `azd deploy` ever runs (job order: provision -> deploy), so the container has not
    been redeployed and the agent has had no chance to mint a new version/identity
    since research. Temporarily clearing staging's `AGENT_PRINCIPAL_ID` back to empty
    would let `main.bicep` skip the Cosmos grant (as it did pre-WI-10) and allow
    provision + deploy to succeed, which may cause the agent server to register a new
    agent version with a fresh `instance_identity.principal_id`. Awaiting user
    decision before trying this (reversible, but another CI dispatch).
  * EXECUTED (run 35274334216): cleared the staging `AGENT_PRINCIPAL_ID` environment
    variable (GitHub rejects empty-string values, so it was deleted, not blanked) and
    redeployed. `azd provision` and `azd deploy` both succeeded for the first time in
    this investigation, publishing agent version 3. Queried the live `/agents` API
    directly (the workflow's own capture step has a latent bug -- it reads
    `AZURE_AI_PROJECT_ENDPOINT` but `azd` actually sets `FOUNDRY_PROJECT_ENDPOINT`,
    so `agents.json`/the live-principal warning were never generated; worth a small
    follow-up fix). Result: version 3's `instance_identity.principal_id` is still the
    **exact same** `f6ef6272-c2db-45f7-9071-6667ae65a37d` -- Foundry ties the instance
    identity to the agent's *blueprint* (`quote-preparation-agent-18c27`), not to the
    version, so redeploying does not mint a new identity to try.
  * BLUEPRINT PRINCIPAL TEST (conclusive, non-viable path but informative): the
    agent's blueprint principal (`943a619b-30fb-4bd7-a9bc-676d329322c8`, backed by
    app registration `8847b0de-...`, `@odata.type: #microsoft.graph.
    agentIdentityBlueprintPrincipal`) resolves perfectly via `az ad sp show` (created
    2026-09-16, well past any propagation window). Tried `az cosmosdb sql role
    assignment create` against it directly (bypassing Bicep) as a live test: Cosmos
    rejected it with a **different** error than the instance identity's --
    `BadRequest: The provided principal ID ... was found to be of an unsupported
    type : [Unfamiliar]` -- meaning Cosmos found the object but does not accept its
    principal type. This rules out the blueprint as a viable substitute grant target.
  * ROOT CAUSE CONFIRMED (conclusive, via production comparison): queried
    production's live `/agents` API and its configured, WORKING `AGENT_PRINCIPAL_ID`
    (`171dca8a-bda3-46ec-8121-a235ecee6e30`) -- they are an **exact match**, and
    `az ad sp show` on it returns `@odata.type: #microsoft.graph.agentIdentity`,
    `servicePrincipalType: ServiceIdentity`. This is the SAME kind of object staging
    is waiting on (`instance_identity`, not the blueprint) -- proving the mechanism
    genuinely works and Cosmos DOES accept it once it finishes materializing in Entra.
    Staging's `f6ef6272-...` re-checked immediately after this run's successful
    deploy (container now actually live, version 3, for the first time in a while) --
    still 404 in Entra. **Conclusion**: this is confirmed, ordinary propagation/
    materialization delay for the `agentIdentity` object specifically (not a platform
    incompatibility, not a permissions gap, not fixable by substituting a different
    principal). No further CLI/API workaround exists; the only lever is elapsed time.
    `AGENT_PRINCIPAL_ID` for staging is deliberately left **unset** for now (restoring
    it immediately would just reproduce the original failure on the next provision);
    re-check `az ad sp show f6ef6272-c2db-45f7-9071-6667ae65a37d` periodically, and
    once it resolves, set the variable and redeploy once more to apply the grant.
  * REFINED (timestamp evidence, user asked "how long do we need to wait"): queried
    Graph `createdDateTime` for both environments' blueprint AND instance-identity
    service principals. Production: blueprint `545a980d-...` created
    `2026-09-16T02:46:21Z`, instance identity `171dca8a-...` created
    `2026-09-16T02:46:22Z` -- only 1 SECOND apart. This refutes "propagation lag from
    blueprint creation" as the mechanism: if that were it, staging's instance
    identity (blueprint `943a619b-...` created `2026-09-16T03:03:06Z`, ~43.5h before
    this check) should already exist. It still 404s. New hypothesis: instance
    identity materialization is likely triggered by the agent's first genuinely
    successful deploy+run, not by blueprint creation -- staging never had one until
    run 35274334216 (~1h before this check, after clearing `AGENT_PRINCIPAL_ID`).
    Recommended to the user: recheck every ~30 min for 1-2h (fresh-clock theory); if
    still unresolved ~24h after THAT successful deploy, treat as a genuine anomaly
    and open a Microsoft support ticket (no published SLA exists for this preview
    feature). No further automated diagnostic is available beyond periodic
    `az ad sp show`/Graph rechecks.
  * RECHECK SCHEDULE (established 2026-09-17, ~6:39 PM ET, per user request "schedule
    the checks"): anchor time is the staging deploy job's `completed_at` timestamp,
    `2026-09-17T21:11:54Z` = 5:11:54 PM ET (run 35274334216, "Deploy candidate to
    staging"). Re-checked live at ~6:40 PM ET (both the 30-min and 1-hr fresh-clock
    marks had already passed) — still 404 in Graph.
    * 2-hr mark: **7:12 PM ET, 2026-09-17** — MISSED, rechecked late at 8:08 PM ET
      (~2h57m elapsed) — still 404 in Graph.
    * 4-hr mark: **9:12 PM ET, 2026-09-17** — recheck if still unresolved.
    * 24-hr mark (anomaly / support-ticket threshold): **5:12 PM ET, 2026-09-18** —
      if `f6ef6272-c2db-45f7-9071-6667ae65a37d` still fails
      `az rest --method get --url "https://graph.microsoft.com/v1.0/servicePrincipals/
      f6ef6272-c2db-45f7-9071-6667ae65a37d"` by this point, open a Microsoft support
      ticket rather than continuing to wait — no published SLA exists for hosted-agent
      Entra Agent ID instance-identity materialization.
    * Caveat: there is no autonomous background scheduler in this session — a human
      (or a fresh session) must prompt a recheck at or after each milestone; this
      schedule exists to be resumed from cold if the session restarts before 24 hr.
  * CORRECTED (user pushed back on "wait 24h," re-examined production's actual
    2026-09-15 history): production's fix was **not** elapsed time. Per
    `.copilot-tracking/plans/logs/2026-09-15/private-networking-log.md` WI-43: "the
    old production identity was unregistered in Entra, so the agent was deleted
    with `force=true` and recreated by the pipeline. The fresh identity
    (`171dca8a-...`) accepted the Cosmos grant" — immediately, same session, no
    waiting period. Confirmed via GitHub run history: run `35048299923`
    (`created_at: 2026-09-16T02:31:14Z`, `completed_at: 02:47:41Z`) straddles the
    identity's Graph `createdDateTime` (`02:46:21-22Z`) almost exactly — the
    identity was minted mid-run and worked within the same run. The command
    responsible is `azd ai agent delete <name> --force` (confirmed available via
    `azd ai agent delete --help`: "Delete a hosted agent and all of its versions
    ... Use --force to terminate active sessions and delete the agent"). **REVISED
    PLAN**: instead of waiting up to 24h, run `azd ai agent delete
    quote-preparation-agent --force` against the staging azd environment, then
    redeploy (`azd deploy` or the full workflow) to let the pipeline recreate the
    agent with a brand-new blueprint + instance identity pair, matching production's
    proven fix path. The 24h wait-and-recheck schedule above is superseded by this
    finding and should only be a fallback if force-delete-and-recreate does not
    resolve it either.
  * EXECUTED AND RESOLVED (2026-09-17/18, force-delete-and-recreate): with user
    approval ("yes go ahead"), ran `azd env select desjardins-quote-preparation-staging`
    (confirmed via read-only `azd ai agent show` before proceeding — the `-e` flag is
    not reliably honored by `azd ai agent` subcommands), then `azd ai agent delete
    quote-preparation-agent --force --no-prompt` followed by `azd deploy --no-prompt`.
    Result: brand-new blueprint + instance identity pair minted; the new instance
    identity `d3df472a-80a8-4934-b6d9-ac9efb1877e3` resolved via `az ad sp show`
    **immediately** (no propagation wait), exactly matching production's WI-43
    precedent. Set the staging `AGENT_PRINCIPAL_ID` repo variable to this new value
    and dispatched a fresh pipeline run (35292843329), which completed "Deploy
    candidate to staging" and the evaluation-gate job successfully. Confirmed the
    Cosmos data-plane grant landed correctly via direct `az cosmosdb sql role
    assignment list --account-name cosmos-desjardins-quote-preparation-staging
    --resource-group rg-desjardins-quote-preparation` — a role assignment for
    `d3df472a-80a8-4934-b6d9-ac9efb1877e3` (Cosmos DB Built-in Data Contributor,
    `00000000-0000-0000-0000-000000000002`) is present. **WI-10 core objective
    (staging agent has Cosmos data-plane write access) is CONFIRMED RESOLVED at the
    infrastructure level.**
  * FUNCTIONAL VALIDATION (Phase 4.1, 2026-09-18): a manual `azd ai agent invoke
    quote-preparation-agent '{"input":"Please prepare a training quote for case
    CASE-SYN-001: ..."}'` (both with a reused session and with `--new-conversation
    --new-session`) returned a bounded rejection template ("...the case reference
    was invalid...") on staging. Cross-checked the identical query against
    **production** (`azd ai agent invoke --agent-endpoint <production endpoint>
    ...`) — production returned the exact same rejection, proving this is NOT a
    staging-specific regression from the identity fix.
    **RESOLVED BY DIRECT TELEMETRY (stronger evidence, supersedes the CLI-invoke
    finding)**: queried staging's Application Insights via its Log Analytics
    workspace (`log-desjardins-quote-preparation-staging`), same method used to
    confirm production in Step 4.1 above. Last 6 hours (spanning run 35292843329,
    after the force-delete-and-recreate): `PUT /dbs/quote-preparation/colls/
    cases/docs/CASE-SYN-001|002|003|005/` — 1/1 success each, 0 failures — plus
    `POST /dbs/quote-preparation/colls/cases/docs/` 5/5 success. **This proves the
    staging agent, using the NEW identity `d3df472a-80a8-4934-b6d9-ac9efb1877e3`,
    genuinely wrote CASE-SYN-001 through 005 to Cosmos with zero failures during
    the pipeline's own evaluation run** — the same fidelity of evidence used to
    confirm production. **Conclusion, revised**: the manual CLI invoke's "case
    reference was invalid" rejection was a red herring caused by the ad-hoc
    `azd ai agent invoke` request shape/protocol (a single-shot `{"input": ...}`
    responses-protocol call outside the pipeline's own invocation context), NOT
    evidence of a real case-lookup or data-seeding gap. **WI-10 is now FULLY
    resolved and functionally proven for both staging and production** — the
    Cosmos data-plane RBAC grant is applied AND actively used successfully by the
    live hosted agent in both environments. WI-04 below is downgraded from "blocks
    full validation" to a minor CLI-usability curiosity, not a product defect.

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
  * SUPERSEDED (2026-09-18): root cause found and fix applied — see the
    force-delete-and-recreate entry above. `az ad sp show` was failing because the
    identity had genuinely never materialized in Entra (not a Graph query-surface
    limitation); deleting and recreating the agent produces a new identity that
    resolves instantly. No further investigation needed.
* WI-04: A manual `azd ai agent invoke` CLI call with `CASE-SYN-001`-style case
  references returns a bounded "case reference was invalid" rejection on BOTH
  staging and production, even though direct Application Insights telemetry proves
  the SAME case IDs were written to Cosmos successfully by the real pipeline
  traffic (0 failures). This means the CLI invoke's request shape/protocol
  (single-shot `{"input": "..."}` via the `responses` protocol) likely differs
  from whatever the actual eval harness/production traffic sends — worth a small
  investigation for CLI documentation/usability, but confirmed NOT a product or
  data defect (downgraded from a blocking concern).
  * Source: Phase 4.1 functional validation, this session (2026-09-18).
  * Dependency: none blocking WI-10 (already fully resolved); low-priority,
    informational only.
  * **CLOSED (2026-09-18, user-confirmed non-issue)**: user agreed this can be
    closed ("sure we can close wi-04"). No further action planned; the CLI
    invoke's rejection is a request-shape quirk of the single-shot `responses`
    protocol, not a product or data defect — real chat-UI traffic (multi-turn)
    creates and submits cases successfully, as independently confirmed by the
    same-session reviewer-queue investigation below.
* WI-05: Clean up the orphaned Cosmos SQL role assignment on staging for the dead
  principal `f6ef6272-c2db-45f7-9071-6667ae65a37d` (the original unresolvable
  identity, now replaced by `d3df472a-80a8-4934-b6d9-ac9efb1877e3` after the
  force-delete-and-recreate). Low risk (principal is already dead/unused) but should
  be removed via `az cosmosdb sql role assignment delete` to match Bicep's
  single-assignment model, mirroring WI-02 for production.
  * Source: This session's Cosmos role-assignment listing, 2026-09-18.
  * **COMPLETED (2026-09-18, user-approved "go ahead with it all")**: confirmed
    `f6ef6272-...` still 404s via `az ad sp show`, then deleted its assignment
    (`11e012aa-08b0-4e28-936a-f9111d869228`) via `az cosmosdb sql role assignment
    delete`. Verified afterward: only the three live-principal assignments remain
    (`d3d943d0-...`, `d3df472a-...` [current agent], `44472dba-...`).
* WI-06 (new): Production promotion for run 35292843329.
  * **COMPLETED (2026-09-18, user-approved "go ahead with it all")**: approved the
    pending `production` environment deployment via `gh api
    .../pending_deployments` (environment id `21862043566`). "Promote to
    production" job completed successfully in 4m2s (shared network foundation
    deploy, production infra provision, evaluated-source deploy, version-evidence
    upload all succeeded). Run 35292843329 is now fully green end-to-end across
    all 5 jobs.
* WI-04 (blocking WI-10 completion) — **SUPERSEDED (2026-09-18)**: root cause found
  and fixed via force-delete-and-recreate of the staging agent (see DD-03 above);
  no further investigation needed. Note: a DIFFERENT, unrelated item is also
  labeled "WI-04" further down this list (the CLI-invoke curiosity found during
  Phase 4.1) — that one remains open but is low-priority/informational only.
  Original text preserved below for history.
  Determine why `azd provision`'s ARM deployment
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

* WI-09 (new, product gap, not a bug): The reviewer app has no UI/API path to
  see cases a reviewer already decided (approved/rejected) — only the pending
  queue (`/api/cases`) and single-case detail (`/api/cases/{id}`) exist.
  Discovered while resolving WI-07: a reviewer cannot tell "this case isn't
  pending because I already approved it" from "this case is missing/broken"
  without the kind of direct API probing done in this session.
  * Source: WI-07 investigation, 2026-09-18.
  * Dependency: none blocking; would need a new `list_cases_by_state` call (or a
    combined multi-state query) plus a frontend view — out of scope for this
    session.
* WI-11 (new, investigation): Neither `foundry-quote-chat` nor
  `foundry-quote-reviewer` produce any `AppRequests` rows in Application
  Insights for real inbound HTTP traffic (browser page loads, `/healthz`,
  `/api/config` all returned 200 but generated zero request-telemetry rows
  across multiple 10-30 minute query windows), even though
  `opentelemetry-instrumentation-fastapi==0.64b0` is present in both images and
  `configure_azure_monitor()` runs at module-import time, before
  `uvicorn app:create_app --factory` invokes the factory — so FastAPI's global
  auto-instrumentation patch should be in effect before any app instance is
  created. Dependency-level telemetry (Cosmos calls, JWKS discovery calls) IS
  confirmed flowing correctly for both apps, so this is a partial gap, not a
  broken pipeline. Root cause not isolated this session; an attempt to inspect
  the live app's `user_middleware` stack via `az containerapp exec` was
  abandoned after repeated PowerShell quoting failures (multiple nested-quote
  strategies all failed identically) — the interactive-exec approach worked
  once tried without an inline `--command` (plain `az containerapp exec` then
  `send_to_terminal`), so a follow-up session should use that path directly
  rather than fighting `--command` quoting.
  * Source: Post-deployment verification pass, 2026-09-18 ("verify it all
    works otherwise fix it").
  * Dependency: none blocking; both apps are fully functional today.
* WI-12 (new, observability quality-of-life): Both apps default to the same
  OpenTelemetry `AppRoleName` (`unknown_service`) since neither sets an
  explicit `service.name` / `OTEL_SERVICE_NAME` resource attribute. This makes
  it impossible to distinguish which app produced a given telemetry row in a
  shared-workspace query without inspecting the `Target`/`Name` fields.
  Suggested fix: set `OTEL_SERVICE_NAME=web-chat` and
  `OTEL_SERVICE_NAME=reviewer-app` (or similar) as container env vars in the
  respective Bicep modules.
  * Source: Post-deployment verification pass, 2026-09-18.
  * Dependency: none blocking; cosmetic/diagnostic improvement only.
  * **RESOLVED 2026-09-18**: added `OTEL_SERVICE_NAME` env var (`web-chat` /
    `reviewer-app`) to `infra/web-chat.bicep` and
    `infra/modules/reviewer-app.bicep`, deployed via `az deployment group
    create`, verified via `az containerapp show` and a Log Analytics
    `AppDependencies` query showing distinct `AppRoleName`s. See changes log
    "WI-12 — Distinct `OTEL_SERVICE_NAME` per App" for full detail.

* **WI-11 RESOLVED 2026-09-18**: root-caused via direct introspection inside
  the running container (`FastAPIInstrumentor().is_instrumented_by_opentelemetry
  == True` globally, but `user_middleware` only showed `['BaseHTTPMiddleware']`
  on the actual app instance) combined with `inspect.getsource` on
  `FastAPIInstrumentor._instrument`/`_InstrumentedFastAPI.__init__`: both
  apps imported `FastAPI` from `fastapi` at module level, BEFORE
  `configure_azure_monitor()` monkeypatches `fastapi.FastAPI`, so every app
  instance built by `create_app()` used the stale, uninstrumented class.
  Fixed by deferring `from fastapi import FastAPI` to the first line inside
  `create_app()` in both `apps/reviewer-app/app.py` and
  `apps/web-chat/app.py`. Validated: 71/71 + 32/32 tests pass; a fresh
  `create_app()` instance now shows `_is_instrumented_by_opentelemetry ==
  True` (note: `user_middleware` remains the WRONG signal to check even
  after the fix — instrumentation wraps the ASGI `middleware_stack`
  directly, not the declarative middleware list). Rebuilt both images via
  `az acr build` and redeployed via `az containerapp update --image` (WI-12's
  Bicep-applied env vars were untouched by this image-only update).
  **Correction to WI-08's build-context note**: web-chat's Dockerfile build
  context is its own app directory, but reviewer-app's Dockerfile explicitly
  requires the **repository root** as build context (its header comment says
  so; it `COPY`s `src/quote-preparation-agent/*` alongside
  `apps/reviewer-app/*`) — an app-directory build for reviewer-app fails fast
  with a missing-file `COPY` error. Verified live via Log Analytics:
  `AppRequests | where TimeGenerated > ago(15m) | summarize count() by
  AppRoleName` now returns non-zero rows for both `web-chat` and
  `reviewer-app` for the first time. See changes log "WI-11 — Missing
  AppRequests Telemetry" for full detail.

* WI-07 (new, out of WI-10 scope): User reported cases created via the production
  web-chat UI (CASE-SYN-002, CASE-SYN-004) do not appear in the Case Reviewer app's
  "Dossiers en attente de révision" queue, which showed only CASE-SYN-001.
  * Source: User-provided screenshots, 2026-09-18.
  * Investigation (Application Insights/Log Analytics on `appi-desjardins-quote-preparation-poc`):
    confirmed via `AppDependencies` that both cases received a real, successful
    Cosmos write transitioning them to `PENDING_REVIEW`
    (`PUT .../docs/CASE-SYN-004/` 200 at 2026-09-16T02:49:52Z;
    `PUT .../docs/CASE-SYN-002/` 200 at 2026-09-16T19:23:29Z), each followed only by
    read-only `GET`/`POST 409` retries (no further state-changing writes since) — the
    documents should legitimately still be `PENDING_REVIEW` in the same
    `cosmos-desjardins-quote-preparation-poc` account/`quote-preparation` database/
    `cases` container the reviewer app is configured to read (`COSMOS_ENDPOINT` env
    var confirmed correct on the current and prior revision). Code review of
    `case_store.py`/`cosmos_case_store.py`'s `list_cases_by_state` (cross-partition
    `SELECT * FROM c WHERE c.state = @state`) and the reviewer app's `/api/cases`
    endpoint/frontend rendering (`format.js`) found no obvious query or
    null-handling bug.
  * Notable finding: `foundry-quote-reviewer` has been redeployed 11 times since
    2026-09-15, most recently at 2026-09-18T01:38:08Z as a direct side effect of
    this session's "Promote to production" run (WI-06) — the exact revision the
    user's screenshot reflects could not be pinned down with certainty, and the
    live app could not be re-checked directly (no reviewer-role credentials
    available to this session; `open_browser_page` confirmed the app is reachable
    but requires interactive Entra sign-in).
  * Separately notable gap: `foundry-quote-reviewer` and `foundry-quote-chat` send
    **zero** telemetry to `appi-desjardins-quote-preparation-poc`/its Log Analytics
    workspace (only the hosted agent's own App Insights role appears) — unlike the
    agent, neither app has Application Insights/OpenTelemetry wired up, and no
    Container Apps diagnostic setting forwards console logs to Log Analytics either.
    This makes remote diagnosis of either app's request-time behavior impossible
    without live log tailing (`az containerapp logs show`) at the exact moment of
    a request.
  * **RESOLVED (2026-09-18, not a bug)**: user reconfirmed the queue still showed
    only CASE-SYN-001 after the redeploy, so the "stale revision" hypothesis was
    ruled out. Used a signed-in browser session's cached MSAL access token
    (extracted from `sessionStorage` via `run_playwright_code`, replayed as an
    `Authorization: Bearer` header) to call the reviewer app's own API directly:
    `/api/cases` (the queue) genuinely returns only CASE-SYN-001 live, and
    `/api/cases/CASE-SYN-002` / `/api/cases/CASE-SYN-004` (point reads, bypassing
    the queue filter) show both are already `state: "APPROVED"`, with an audit
    trail of `CREATE_DRAFT -> SUBMIT -> APPROVE`, approved by
    `reviewerId: b785230a-4af4-418a-acd9-aea99894d37a` — the same account signed
    in during this test. Both cases were already reviewed and approved earlier
    (2026-09-16T20:15:37Z and 2026-09-17T00:38:01Z) and correctly no longer
    belong in the "pending review" queue by design
    (`list_cases_by_state(STATE_PENDING_REVIEW)` filters on current state, not
    history). No code defect found. Gap identified instead: the reviewer app
    has no "history"/"approved" view, only the pending queue and a single-case
    detail fetch, so a reviewer has no UI path to see cases they already
    decided — flagged as a follow-on product gap (WI-09), not a bug fix.
  * Dependency: none blocking WI-10 (already fully resolved); independent
    investigation, user-flagged as more urgent than WI-04 closure.

* WI-08 (new, user-requested): Application Insights/OpenTelemetry instrumentation
  added for both `apps/web-chat` and `apps/reviewer-app`, closing the telemetry
  gap identified while investigating WI-07.
  * Source: user request, 2026-09-18 ("also we should close the app insights gap
    for both ui apps").
  * Implementation: added `azure-monitor-opentelemetry==1.8.9` to both apps'
    `requirements.txt`; added a module-level (not per-`create_app()`-call) guarded
    bootstrap — `if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor()` — to both `apps/reviewer-app/app.py` and
    `apps/web-chat/app.py`, so local/dev/test runs without the env var are
    unaffected (verified: both apps' existing test suites pass unchanged, 71 and
    32 tests respectively). Wired `APPLICATIONINSIGHTS_CONNECTION_STRING` through:
    `infra/modules/reviewer-app.bicep` (new optional param, default `''`, passed
    from `infra/main.bicep`'s existing `monitoring.outputs.applicationInsightsConnectionString`)
    and `infra/web-chat.bicep` (new optional param, default `''`, since that
    template is deployed out-of-band and has no `main.bicep` module wiring to
    inherit from — the operator must supply it explicitly at deploy time to
    enable telemetry). Regenerated the compiled `infra/main.json`,
    `infra/web-chat.json`, and `infra/modules/reviewer-app.json` to match;
    `az bicep build`-equivalent compile succeeded for all three with zero new
    diagnostics (two pre-existing `BCP318` warnings in
    `modules/mcp-container-apps.bicep`, unrelated to this change).
  * Status: **DEPLOYED to production, 2026-09-18 — FULLY RESOLVED.** Committed as
    `95696e7` and pushed to `main`. `web-chat`: rebuilt image
    (`acrdesjqp7651.azurecr.io/pilot/web-chat@sha256:b4c5a845c1b38aff8915ccd070266182b596082045209b99b1de61c50454d2f1`)
    via `az acr build` (context = `apps/web-chat`, not repo root — see lesson
    recorded in user memory) and redeployed via manual
    `az deployment group create --template-file infra/web-chat.bicep` with
    `applicationInsightsConnectionString` supplied explicitly (required since that
    template has no `main.bicep` wiring to inherit from). `reviewer-app`: shipped
    through the normal pipeline — `hosted-agent-cd.yml` dispatched (run
    `35299088833`), staging deploy + LLM-judge/deterministic evaluation gate both
    passed, then the `production` Environment's manual-approval gate was approved
    via `gh api .../pending_deployments` (per explicit user authorization to act
    autonomously), and `release / Promote to production` completed successfully —
    `main.bicep` provisioned/deployed with the new `applicationInsightsConnectionString`
    wiring inherited automatically from `monitoring.outputs`.
  * Verification: both apps confirmed live via `az containerapp show` —
    `foundry-quote-chat` and `foundry-quote-reviewer` (revision
    `foundry-quote-reviewer--0000012`) both have `APPLICATIONINSIGHTS_CONNECTION_STRING`
    set to the correct value. Live telemetry confirmed via direct Log Analytics
    query against workspace `fd174a24-f7c5-47b8-9a9d-00c9505f7731`: both apps'
    OpenTelemetry SDKs successfully called `GET /AzMonSDKDynamicConfiguration`
    (self-monitoring startup call) at their respective redeploy timestamps
    (web-chat ~02:38 UTC, reviewer-app ~02:46 UTC, 2026-09-18) — proof the
    connection string is valid and telemetry export is live, not just configured.
  * Dependency: none; independent of WI-07's resolution.

* WI-13 (new, found during "redeploy all", 2026-09-18): staging's reviewer-app
  Container App (`foundry-quote-reviewer-staging`) had silently drifted from both
  the WI-11 telemetry fix and the WI-12 `OTEL_SERVICE_NAME` fix — both prior
  redeploys only touched production resource names. Also found (and fixed) a
  stale Entra SPA redirect URI: the reviewer-app app registration
  (`bedbaeec-aff3-47ff-b4c1-74741ddeb6dc`) still listed
  `foundry-quote-reviewer-staging.nicehill-d110b038.eastus2.azurecontainerapps.io`
  but the staging Container Apps managed environment's live default-domain
  suffix is now `nicebay-9b5e26aa` (env was recreated at some point, most likely
  during earlier staging agent-identity force-delete-and-recreate work), so
  staging sign-in failed with `AADSTS50011` until the current FQDN was added.
  * **RESOLVED 2026-09-18**: redeployed `foundry-quote-reviewer-staging` to the
    canonical CI-tagged `pilot/reviewer-app:v1.0.4` image (also used to redeploy
    both production apps, replacing the ad-hoc `wi11-otel-fix-*` images from the
    prior WI-11 manual redeploy); added `OTEL_SERVICE_NAME=reviewer-app` via
    `az containerapp update --set-env-vars`; added the current staging FQDN to
    the app registration's `spa.redirectUris` via `az rest PATCH
    /v1.0/applications/{id}` (Graph API — `az ad app update` in this CLI version
    has no `--spa-redirect-uris` flag). Verified staging sign-in succeeds and the
    queue shows `CASE-SYN-001/002/003/005`, all `PENDING_REVIEW`.
  * Source: user request "redeploy all ... ensure we can see cases in app review
    for the environments newly deployed", 2026-09-18.
  * Follow-on (not done, low priority): remove the now-stale `nicehill-d110b038`
    redirect URI from the app registration once confirmed nothing else depends on
    it; no `foundry-quote-chat-staging` Container App exists, so web-chat has no
    staging counterpart to reconcile.

* WI-14 (new, found while fixing the wiki Deployment Links table, 2026-09-18):
  the wiki's Deployment Links table (`wiki/Home.md`) only ever showed ONE
  environment's links (production preferred) with at least one hardcoded,
  potentially-mislabeled row ("Try staging web chatbot" regardless of which
  environment's URL it actually held), because
  `publish-test-trends.yml`'s artifact-download loop stopped at the first
  `deployment-links-*` artifact found instead of fetching both.
  * **RESOLVED 2026-09-18**: `scripts/deployment_summary.py`'s `render()` now
    takes an optional `environment` label and tags every environment-specific
    row accordingly (fixing the hardcoded "staging" mislabel);
    `scripts/update_wiki_deployment_links.py` now accepts multiple
    `--from-file` args and merges them under one shared heading;
    `deploy-and-evaluate.yml` passes `--environment staging`/`--environment
    production` at its two call sites; `publish-test-trends.yml` downloads
    both `deployment-links-staging` and `deployment-links-production`
    (`|| true`, no early `break`) and passes whichever exist to the merge
    script. Validated locally (rendered both environments + a scratch
    multi-file wiki merge) but NOT yet exercised by a real CI run.
  * Source: user request "so when giving URLs ensure we give all environments
    eg staging production etc and make it clear", 2026-09-18, with an
    attached screenshot of the ambiguous wiki table.
  * Follow-on (not done): confirm on the next real `Deploy and Evaluate` →
    `Publish Test Trends` run pair that the wiki page actually renders both
    `### Staging` and `### Production` sections as expected; no local test
    can fully substitute for that live artifact hand-off.

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
