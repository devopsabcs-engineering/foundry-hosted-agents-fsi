---
applyTo: '.copilot-tracking/changes/2026-09-16/bilingual-ui-apps-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: Bilingual UI Apps (web-chat, reviewer-app)

## Overview

Add a manual EN/FR toggle, full UI-string translation, and a backend bilingual error-message catalog to `apps/web-chat` and `apps/reviewer-app`, plus bilingual demo-query data in `apps/web-chat/frontend/src/samples.js`.

## Objectives

### User Requirements

* "make the UI apps bilingual — even synthetic sample data should be bilingual" — Source: conversation request.
* Manual EN/FR toggle (not auto-detect), `localStorage` persistence, default English — Source: clarifying-question answers in conversation.
* Backend error messages should also be translated, via a small bilingual catalog keyed by existing error `code`/status — Source: clarifying-question answers in conversation.
* Scope includes `apps/web-chat` + `apps/reviewer-app` frontends, `apps/web-chat/frontend/src/samples.js`, and `apps/workshop` — Source: clarifying-question answers in conversation.

### Derived Objectives

* Add stable machine-readable `code` fields to every backend error path in both apps (currently only one of ~15 paths has one) — Derived from: a code-keyed message catalog requires every path to have a code, not just `SELF_APPROVAL`; this also closes WI-23 from the prior reviewer-app planning log.
* Reverse the prior English-only decision for the reviewer-app UI (AD-05/WI-24 in `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md`) — Derived from: the current explicit user request supersedes that recorded decision.
* Exclude `apps/workshop` from code changes — Derived from: it has no frontend/running UI; its only English text is developer-facing docstrings/exception messages never rendered to a user (see Planning Log DD-02).
* Reuse the fixtures' existing fr-CA translations verbatim where the same concept already appears in `data/synthetic/fixtures/*.json` — Derived from: matching the repository's established bilingual data conventions.

## Context Summary

### Project Files

* apps/web-chat/frontend/src/main.jsx - all web-chat UI text, currently hardcoded English
* apps/web-chat/frontend/src/samples.js - demo query data, currently English-only `title`/`prompt`
* apps/web-chat/frontend/index.html - static `lang` attribute
* apps/web-chat/frontend/tests/samples.test.js - existing assertions on samples shape
* apps/web-chat/app.py - session/message endpoints, SSE error frames, size-limit middleware
* apps/web-chat/auth.py - `PilotAuth` token verification and authorization errors
* apps/web-chat/tests/test_app.py, apps/web-chat/tests/test_auth.py - existing exact-body error assertions
* apps/reviewer-app/frontend/src/main.jsx - all reviewer-app UI text, currently hardcoded English
* apps/reviewer-app/frontend/src/format.js - pure formatting/error-mapping helpers with hardcoded English output
* apps/reviewer-app/frontend/tests/format.test.js - existing assertions on formatting helpers
* apps/reviewer-app/app.py - domain exception handlers, `decide()` inline exception, size-limit middleware
* apps/reviewer-app/auth.py - `ReviewerAuth` token verification and authorization errors
* apps/reviewer-app/tests/test_app.py, apps/reviewer-app/tests/test_auth.py - existing exact-body error assertions
* data/synthetic/fixtures/*.json - existing bilingual `en-CA`/`fr-CA` data to reuse/match tone with
* apps/workshop/calculator.py, apps/workshop/approval_repository.py - reviewed, intentionally excluded from this plan

### References

* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md - full research findings backing this plan
* .copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md - prior AD-05/WI-24/WI-23/WI-21 items referenced and superseded/closed by this plan

### Standards References

* No repository-specific coding-standard instruction files apply beyond general conventions already followed in the existing codebase (per-app duplication over shared packages, minimal dependencies).

## Implementation Checklist

### [x] Implementation Phase 1: Web-chat frontend i18n infrastructure

<!-- parallelizable: true -->

* [x] Step 1.1: Create `apps/web-chat/frontend/src/i18n.js` translation dictionary
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 12-31)
* [x] Step 1.2: Create `apps/web-chat/frontend/src/useLanguage.js` hook
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 32-48)
* [x] Step 1.3: Validate phase changes
  * Run `npm run build` in `apps/web-chat/frontend`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 49-55)

### [x] Implementation Phase 2: Web-chat UI translation and bilingual sample data

<!-- parallelizable: true -->

* [x] Step 2.1: Wire language toggle and translate all strings in `main.jsx`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 60-80)
* [x] Step 2.2: Convert `samples.js` to locale-keyed bilingual data
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 81-97)
* [x] Step 2.3: Update `index.html` and `samples.test.js` (including per-locale fixture-id/length assertions)
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 98-115)
* [x] Step 2.4: Validate phase changes
  * Run `npm run build` and `node --test tests/*.test.js` in `apps/web-chat/frontend`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 116-121)

### [x] Implementation Phase 3: Web-chat backend bilingual error catalog

<!-- parallelizable: true -->

* [x] Step 3.1: Create `apps/web-chat/messages.py` catalog
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 126-144)
* [x] Step 3.2: Add flattening exception handler and thread language through `app.py`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 145-163)
* [x] Step 3.3: Localize `apps/web-chat/auth.py`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 164-180)
* [x] Step 3.4: Thread the UI language into the agent's bilingual answer content (`FoundryClient.events`/`content_text`)
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 181-200)
* [x] Step 3.5: Update web-chat backend tests
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 201-217)
* [x] Step 3.6: Validate phase changes
  * Run `pytest apps/web-chat/tests`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 218-222)

### [x] Implementation Phase 4: Reviewer-app frontend i18n infrastructure

<!-- parallelizable: true -->

* [x] Step 4.1: Create `apps/reviewer-app/frontend/src/i18n.js` translation dictionary
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 227-242)
* [x] Step 4.2: Create `apps/reviewer-app/frontend/src/useLanguage.js` hook
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 243-258)
* [x] Step 4.3: Validate phase changes
  * Run `npm run build` in `apps/reviewer-app/frontend`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 259-263)

### [x] Implementation Phase 5: Reviewer-app UI translation and format.js localization

<!-- parallelizable: true -->

* [x] Step 5.1: Wire language toggle and translate all strings in `main.jsx` (reverses AD-05/WI-24)
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 268-288)
* [x] Step 5.2: Localize `format.js` helpers
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 289-304)
* [x] Step 5.3: Update reviewer-app frontend tests
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 305-320)
* [x] Step 5.4: Update `docs/labs/lab-13-reviewer-ui.md`'s English-only callout
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 321-339)
* [x] Step 5.5: Validate phase changes
  * Run `npm run build` and `node --test tests/*.test.js` in `apps/reviewer-app/frontend`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 340-345)

### [x] Implementation Phase 6: Reviewer-app backend bilingual error catalog

<!-- parallelizable: true -->

* [x] Step 6.1: Create `apps/reviewer-app/messages.py` catalog
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 350-368)
* [x] Step 6.2: Add codes and localization to reviewer-app exception handlers
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 369-384)
* [x] Step 6.3: Localize `apps/reviewer-app/auth.py`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 385-401)
* [x] Step 6.4: Update reviewer-app backend tests
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 402-418)
* [x] Step 6.5: Validate phase changes
  * Run `pytest apps/reviewer-app/tests`
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 419-423)

### [ ] Implementation Phase 7: Validation

<!-- parallelizable: false -->

* [ ] Step 7.1: Run full project validation
  * Execute `npm run build` and `node --test tests/*.test.js` in both frontends, `pytest apps/web-chat/tests apps/reviewer-app/tests`, and `pytest apps/workshop/tests` (confirms no regression from the deliberate exclusion)
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 428-435)
* [ ] Step 7.2: Fix minor validation issues
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 436-439)
* [ ] Step 7.3: Report blocking issues
  * Details: .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Lines 440-443)

## Planning Log

See .copilot-tracking/plans/logs/2026-09-16/bilingual-ui-apps-log.md for discrepancy tracking, implementation paths considered, and suggested follow-on work.

## Dependencies

* Node.js + npm (existing `apps/web-chat/frontend`, `apps/reviewer-app/frontend` toolchains)
* Python + pytest (existing `apps/web-chat`, `apps/reviewer-app` toolchains)
* No new third-party packages

## Success Criteria

* Both frontends render entirely in the selected language with a persisted manual toggle, no leftover hardcoded English text — Traces to: user requirement (manual toggle, bilingual UI)
* The web-chat agent's streamed chat answers (`FoundryClient.events`/`content_text`), not just the surrounding chrome, render in the active UI language — Traces to: Planning Log DR-03 (Plan Validator finding), Implementation Phase 3 Step 3.4
* `apps/web-chat/frontend/src/samples.js` demo queries are fully bilingual, including the fixture-id/length test assertions applied per locale — Traces to: user requirement ("even synthetic sample data should be bilingual"), Planning Log DR-04
* Every backend error response carries a stable `code` and localizes `detail` based on `X-UI-Language`, with unchanged default English behavior — Traces to: user requirement (backend catalog keyed by error code)
* All existing and updated test suites pass (`apps/web-chat/tests`, `apps/reviewer-app/tests`, both frontends' `tests/*.test.js`, `apps/workshop/tests` unchanged) — Traces to: Implementation Phase 7
* AD-05/WI-24 from the prior reviewer-app planning log are explicitly reversed/closed, `apps/workshop`'s exclusion is explicitly documented, and `docs/labs/lab-13-reviewer-ui.md`'s English-only callout is corrected — Traces to: Planning Log DD-01, DD-02, DR-02
