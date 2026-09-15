<!-- markdownlint-disable-file -->
# Release Changes: Reviewer redirect URIs and bilingual UI labs

**Related Plan**: ad hoc (user request in Task Implementor session)
**Implementation Date**: 2026-09-15

## Summary

Two workstreams. First, finish the outstanding reviewer identity work by registering the real deployed Container App redirect URIs alongside the local development URI. Second, extend the bilingual workshop from ten local-only labs to fifteen labs that cover the Azure foundation, the applicant web chat UI, reviewer identity, the reviewer UI, and pilot operations, illustrated with screenshots captured from the running applications.

## Changes

### Added

* docs/assets/images/reviewer-sign-in.png - reviewer app pre-authentication gate
* docs/assets/images/reviewer-queue.png - five seeded cases awaiting review
* docs/assets/images/reviewer-case-detail.png - CASE-SYN-001 with premium, rule ids and audit trail
* docs/assets/images/reviewer-approve-confirm.png - approval confirmation step
* docs/assets/images/reviewer-case-approved.png - post-decision state with APPROVE audit entry
* docs/assets/images/reviewer-case-not-priced.png - CASE-SYN-003 rendering a null amount
* docs/assets/images/web-chat-sign-in.png - applicant chat pre-authentication gate
* docs/labs/lab-10-azure-foundation.md and docs/fr/labs/lab-10-azure-foundation.md
* docs/labs/lab-11-web-chat.md and docs/fr/labs/lab-11-web-chat.md
* docs/labs/lab-12-reviewer-identity.md and docs/fr/labs/lab-12-reviewer-identity.md
* docs/labs/lab-13-reviewer-ui.md and docs/fr/labs/lab-13-reviewer-ui.md
* docs/labs/lab-14-pilot-operations.md and docs/fr/labs/lab-14-pilot-operations.md
* scripts/seed_review_queue.py - seeds a local SQLite case store from the checked-in fixtures

### Modified

* .gitignore - ignore the `.local/` scratch directory used by the reviewer lab
* docs/labs/index.md and docs/fr/labs/index.md - fifteen-lab curriculum split into local foundations and pilot surfaces
* docs/labs/lab-07-run-agent.md and docs/fr/labs/lab-07-run-agent.md - replace the "no reviewer UI exists" claim with a forward reference to Lab 13
* docs/labs/lab-09-teardown.md and docs/fr/labs/lab-09-teardown.md - scope the no-cloud-teardown claim to Labs 00-08 and point forward to Lab 10
* eval/results.json - bilingual parity count moves from 11 to 16 files per language

## Additional or Deviating Changes

* `AGENT_PRINCIPAL_ID` was left unset.
  * The Foundry data plane reports zero deployed agents, so the per-agent Entra identity that parameter expects does not exist yet. It cannot be resolved until the gated deploy workflow runs.
* No authenticated web chat conversation screenshot was captured.
  * The conversation view requires a deployed Foundry agent endpoint and a web chat app registration. Neither exists while the deploy workflow remains gated, so Lab 11 documents the constraint instead of showing a fabricated screenshot.
* Lab 11 and Lab 14 document `PYTHONPATH=apps/web-chat` on the web chat test command.
  * Discovered while validating the drafted commands. Unlike the reviewer tests, the web chat tests carry no `sys.path` insertion and fail to collect without it. The pipeline sets the same variable, so the labs now match CI rather than the shorter command that looked correct.

## Release Summary

Twenty-six files changed: 19 added, 7 modified. Ten new bilingual lab pages extend the curriculum from ten labs to fifteen, seven PNG screenshots were captured from the reviewer and chat applications running locally against real Entra sign-in, and one script was added to seed a review queue from the checked-in fixtures.

No application code changed. The only non-documentation modifications are a `.gitignore` entry and the regenerated evaluation result, whose bilingual parity count moves from 11 to 16 files per language because the new labs were authored as matched pairs.

Validation: the deterministic evaluation gate reports `13/13 records passed; bilingual_parity=PASS`, and every Python suite passes (233 passed, 34 skipped across the agent, evaluation, workshop, MCP, reviewer, and chat suites).

No deployment is required. The GitHub Pages site rebuilds from `main`.
