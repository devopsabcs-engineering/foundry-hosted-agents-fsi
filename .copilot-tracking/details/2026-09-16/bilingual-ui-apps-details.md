<!-- markdownlint-disable-file -->
# Implementation Details: Bilingual UI Apps (web-chat, reviewer-app)

## Context Reference

Sources: .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md; .copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md (AD-05, WI-24, WI-23); user clarifying-question answers gathered in conversation (manual toggle, localStorage persistence, default en-CA, backend catalog keyed by error code, scope confirmation).

## Implementation Phase 1: Web-chat frontend i18n infrastructure

<!-- parallelizable: true -->

### Step 1.1: Create the web-chat translation dictionary module

Create `apps/web-chat/frontend/src/i18n.js` exporting `LANGUAGES = ['en-CA', 'fr-CA']`, `DEFAULT_LANGUAGE = 'en-CA'`, a `STRINGS` object with one key per UI string used in `main.jsx` and `samples.js` (nested by area: `sidebar`, `topbar`, `gate`, `composer`, `message`, `errors`, `disclaimer`), and a `translate(language, key, vars)` function doing a dot-path lookup with `{name}`-style interpolation (needed for the environment badge, e.g. `topbar.pilotBadge` → en `"{env} pilot"`, fr `"pilote {env}"`).

Files:
* apps/web-chat/frontend/src/i18n.js - new dictionary + translate() module

Discrepancy references:
* Implements the "Recommended Mechanism" and "Design for the Frontend Toggle" sections of the research document.

Success criteria:
* `translate('fr-CA', 'sidebar.newQuote')` returns a French string; `translate('en-CA', 'topbar.pilotBadge', {env: 'production'})` returns `"production pilot"`.
* Every string literal currently inline in `main.jsx` (per the research document's web-chat inventory) has a corresponding key.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md (Lines under "apps/web-chat/frontend Inventory" and "Design for the Frontend Toggle") - full string inventory and interpolation requirement

Dependencies:
* None (new file).

### Step 1.2: Create the web-chat `useLanguage` hook

Create `apps/web-chat/frontend/src/useLanguage.js` exporting a `useLanguage()` hook that reads `localStorage.getItem('fhaf-ui-language')` on mount (falling back to `DEFAULT_LANGUAGE` from `i18n.js`), exposes `{ language, setLanguage, t }` where `t` is `translate` bound to the current `language`, persists to `localStorage` on every `setLanguage` call, and side-effects `document.documentElement.lang = language.slice(0, 2)` on change.

Files:
* apps/web-chat/frontend/src/useLanguage.js - new hook

Success criteria:
* Toggling language updates `localStorage['fhaf-ui-language']` and `document.documentElement.lang`.
* Hook returns `en-CA` on first load in an environment with no stored value.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Design for the Frontend Toggle") - persistence and default-language requirements

Dependencies:
* Step 1.1 (`i18n.js` exports).

### Step 1.3: Validate phase changes

Run the frontend build for web-chat to confirm the new modules have no syntax errors before wiring them into `main.jsx`.

Validation commands:
* `npm run build` (in `apps/web-chat/frontend`) - confirms `i18n.js`/`useLanguage.js` compile cleanly under Vite

## Implementation Phase 2: Web-chat UI translation and bilingual sample data

<!-- parallelizable: true -->

### Step 2.1: Wire the language toggle and translate all UI strings in main.jsx

Update `apps/web-chat/frontend/src/main.jsx` to call `useLanguage()` at the top level, render a two-state toggle control in the topbar (showing the other language's short label, e.g. "FR"/"EN"), and replace every hardcoded string enumerated in the research document's web-chat inventory with `t('...')` calls, including aria-labels and title attributes. Add `'X-UI-Language': language` to the headers of every authenticated `fetch` call (session creation, message send/stream, conversation delete). Preserve the existing (out-of-scope) environment-badge behavior of not interpolating `config.environment` — translate the literal displayed text only, structured so a future fix is a one-line change per the research document's Risks section.

Files:
* apps/web-chat/frontend/src/main.jsx - replace inline strings with `t()`, add toggle control, add language header to fetch calls

Discrepancy references:
* Preserves the pre-existing environment-badge bug noted in the research document's "Risks / Open Notes" rather than fixing it (out of scope for this task).

Success criteria:
* No hardcoded English UI string literals remain in JSX text nodes, `aria-label`, or `title` attributes (dynamic values like case IDs/timestamps excepted).
* Switching the toggle re-renders all visible text in the selected language without a page reload.
* Every authenticated fetch call includes the `X-UI-Language` header matching the active language.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("apps/web-chat/frontend Inventory", "Risks / Open Notes") - full inventory and environment-badge caveat

Dependencies:
* Implementation Phase 1 completion (`i18n.js`, `useLanguage.js`).

### Step 2.2: Convert samples.js to locale-keyed bilingual data

Update `apps/web-chat/frontend/src/samples.js` so each `sampleQueries` entry's `title` and `prompt` become `{ 'en-CA': '...', 'fr-CA': '...' }` objects (the `tools` array stays as-is — tool names are technical identifiers, not translated copy). Reuse the fixture's existing fr-CA translation verbatim for the CASE-SYN-005 title ("Sélection de régime manquante") and match the fixtures' formal French register for the other two entries.

Files:
* apps/web-chat/frontend/src/samples.js - convert `title`/`prompt` fields to locale-keyed objects

Success criteria:
* All 3 sample entries have both `en-CA` and `fr-CA` populated for `title` and `prompt`.
* `main.jsx`'s rendering of sample queries selects `sample.title[language]` / `sample.prompt[language]`.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Existing Bilingual Conventions to Match", "apps/web-chat/frontend Inventory") - fixture reuse guidance

Dependencies:
* Step 2.1 (rendering code that consumes the new shape).

### Step 2.3: Update index.html and frontend tests

Set the initial `<html lang="en">` in `apps/web-chat/frontend/index.html` to be overwritten at runtime by `useLanguage.js` (leave the static attribute as a sane pre-hydration default). Update `apps/web-chat/frontend/tests/samples.test.js` to assert the new `{en-CA, fr-CA}` object shape for `title`/`prompt` instead of plain strings, and re-apply the existing content assertions (each sample's `prompt` includes its fixture id, each `prompt` stays under the 8,000-character composer limit) to **both** the `en-CA` and `fr-CA` values, not just the shape.

Files:
* apps/web-chat/frontend/index.html - confirm static `lang` default is documented as pre-hydration only (no functional change required if already `en`)
* apps/web-chat/frontend/tests/samples.test.js - update assertions for locale-keyed `title`/`prompt`, re-applying the fixture-id and length checks per locale

Success criteria:
* `node --test tests/*.test.js` passes in `apps/web-chat/frontend`.
* The fixture-id and length assertions the existing test performs are still enforced for both `en-CA` and `fr-CA` values, not silently dropped when the shape changes.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("apps/web-chat/frontend Inventory") - existing test file note

Dependencies:
* Step 2.2 (new samples.js shape).

### Step 2.4: Validate phase changes

Validation commands:
* `npm run build` (in `apps/web-chat/frontend`) - production build succeeds with translated UI
* `node --test tests/*.test.js` (in `apps/web-chat/frontend`) - unit tests pass

## Implementation Phase 3: Web-chat backend bilingual error catalog

<!-- parallelizable: true -->

### Step 3.1: Create the web-chat message catalog

Create `apps/web-chat/messages.py` with `LANGUAGES = ("en-CA", "fr-CA")`, `DEFAULT_LANGUAGE = "en-CA"`, `def pick_language(header_value: str | None) -> str` (returns the header value if it is a recognized language, else the default), a `MESSAGES: dict[str, dict[str, str]]` catalog with one entry per error enumerated in the research document's "Backend Error Surfaces" section (codes: `SIGNIN_UNAVAILABLE`, `INVALID_TOKEN`, `APP_NOT_AUTHORIZED`, `SCOPE_REQUIRED`, `MEMBERSHIP_REQUIRED`, `IDENTITY_REQUIRED`, `SIGNIN_REQUIRED`, `PILOT_CAPACITY`, `SESSION_LIMIT`, `CONVERSATION_NOT_FOUND`, `CONVERSATION_EXPIRED`, `REQUEST_TOO_LARGE`, `RESPONSE_IN_PROGRESS`, `IDEMPOTENCY_KEY_REUSED`, `RESPONSE_BUSY`, `CONVERSATION_LIMIT`, `PILOT_BUSY`, `ASSESSMENT_FAILED`, `SERVICE_UNAVAILABLE`), each preserving the exact existing English wording so current behavior is unchanged, and `def message(code: str, language: str) -> str`.

Files:
* apps/web-chat/messages.py - new bilingual message catalog

Discrepancy references:
* Extends WI-23 ("only the self-approval 403 carries a machine-readable code... consider stable codes on 404, 409, and 500") from reviewer-app-log.md to web-chat, which previously had zero codes anywhere.

Success criteria:
* `message('PILOT_CAPACITY', 'en-CA')` equals the current literal text ("Pilot capacity reached. Try again later.") so existing English-only tests keep passing unless intentionally updated.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Backend Error Surfaces", "Recommended Mechanism for Backend Localization") - full raise-site enumeration

Dependencies:
* None (new file).

### Step 3.2: Add a flattening HTTPException handler and thread language through app.py

In `apps/web-chat/app.py`, register `@application.exception_handler(HTTPException)` that returns `exc.detail` as the JSON body directly when it is a `dict`, otherwise falls back to today's `{"detail": exc.detail}` shape (preserves compatibility for any exception not yet migrated). Read `X-UI-Language` via `Header(alias="X-UI-Language", default=None)` in the `identity()` dependency and in the `POST /api/conversations/{id}/messages` handler; pass the resolved language (via `pick_language`) to `SessionStore.create`/`SessionStore.get` (which raise `HTTPException(status, {"detail": message(code, language), "code": code})` instead of bare strings) and into the `generate()` closure so its two SSE error frames render `message('ASSESSMENT_FAILED'|'SERVICE_UNAVAILABLE', language)`. Localize the size-limit middleware's `{"detail": "Request too large."}` (413) the same way, reading the header directly from `request.headers`.

Files:
* apps/web-chat/app.py - add exception handler, thread `language` through session/message endpoints and SSE error frames, localize middleware 413 response

Discrepancy references:
* Implements the "Recommended Mechanism for Backend Localization" steps 1-3 and 6 from the research document.

Success criteria:
* A request with `X-UI-Language: fr-CA` that triggers any of the enumerated errors receives the French text and a `code` field; an absent or unrecognized header falls back to today's English text unchanged.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Recommended Mechanism for Backend Localization", steps 1-3, 6) - handler flattening and language-threading design

Dependencies:
* Step 3.1 (`messages.py`).

### Step 3.3: Localize apps/web-chat/auth.py

Add a `language: str = DEFAULT_LANGUAGE` parameter to `PilotAuth.verify` and `PilotAuth.authorize`, replace each bare-string `HTTPException(status, "...")` raise with `HTTPException(status, {"detail": message(code, language), "code": code})` using the codes from Step 3.1, and update the `identity()` dependency in `app.py` to pass the resolved language into `authorize()`.

Files:
* apps/web-chat/auth.py - thread `language` parameter, raise coded/localized exceptions
* apps/web-chat/app.py - pass resolved language into `verifier.authorize(...)` calls

Success criteria:
* Each of the 7 `PilotAuth` error paths (`verify`'s 6 raises plus `authorize`'s missing/malformed-header raise) returns the correct code and, given `X-UI-Language: fr-CA`, the correct French text.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Backend Error Surfaces" - `apps/web-chat/auth.py` bullet) - enumerated auth error paths

Dependencies:
* Step 3.1 (`messages.py`), Step 3.2 (flattening handler must exist for the dict-shaped `detail` to render correctly).

### Step 3.4: Thread the UI language into the agent's bilingual answer content

`content_text(content, locale="en-CA")` (apps/web-chat/app.py line 96) already extracts the agent's bilingual `{"en-CA", "fr-CA"}` response map, but its only call site inside `FoundryClient.events` (line 147) never passes a `locale`, so streamed chat answers always render in English regardless of the UI toggle — this was a gap the initial research mischaracterized as "already bilingual." Add a `locale` parameter to `FoundryClient.events(self, messages, locale=DEFAULT_LANGUAGE)`, thread the resolved `X-UI-Language` (already read in the `POST /api/conversations/{id}/messages` handler per Step 3.2) through the `events()` call inside `generate()`, and pass it to `content_text(content, locale=locale)` at its call site.

Files:
* apps/web-chat/app.py - add `locale` parameter to `FoundryClient.events`, thread resolved language through to `content_text`

Discrepancy references:
* Addresses DR-03 in the Planning Log (Plan Validator finding): without this step the agent's actual assessment answers never become bilingual even though the UI toggle, samples, and error text do.

Success criteria:
* A message sent with `X-UI-Language: fr-CA` whose agent response contains a `{"en-CA","fr-CA"}` content map streams the `fr-CA` text; the same request with the header absent or `en-CA` streams the `en-CA` text (today's behavior, unchanged).

Context references:
* apps/web-chat/app.py (Lines 96-100, 147) - `content_text` definition and its only call site
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Existing Bilingual Conventions to Match") - notes `content_text`'s existing locale-aware extraction

Dependencies:
* Step 3.2 (language already resolved in the message endpoint).

### Step 3.5: Update web-chat backend tests

Update `apps/web-chat/tests/test_app.py` and `apps/web-chat/tests/test_auth.py` so every assertion on an error response body includes the new `"code"` field, and add representative test cases (at least one auth error, one session error, one SSE error frame) sent with `X-UI-Language: fr-CA` asserting the French text, plus one case confirming an invalid/missing header falls back to `en-CA`. Add a test asserting that a message request with `X-UI-Language: fr-CA` against an agent response carrying a bilingual content map streams the `fr-CA` text (covers Step 3.4).

Files:
* apps/web-chat/tests/test_app.py - update body assertions, add fr-CA cases, add agent-answer locale test
* apps/web-chat/tests/test_auth.py - update body assertions, add fr-CA cases

Success criteria:
* `pytest apps/web-chat/tests` passes.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Backend Error Surfaces" - test coverage note) - existing exact-body assertions to update

Dependencies:
* Steps 3.1-3.4 completion.

### Step 3.6: Validate phase changes

Validation commands:
* `pytest apps/web-chat/tests` - backend unit tests pass with codes + bilingual text + bilingual agent answers

## Implementation Phase 4: Reviewer-app frontend i18n infrastructure

<!-- parallelizable: true -->

### Step 4.1: Create the reviewer-app translation dictionary module

Create `apps/reviewer-app/frontend/src/i18n.js` mirroring Step 1.1's structure and API (`LANGUAGES`, `DEFAULT_LANGUAGE`, `STRINGS`, `translate`), covering every string in the research document's reviewer-app inventory (queue table, case detail, decision UI, reason-code prompt, approve confirmation, audit trail, gate/topbar, the `NOTICE` disclaimer, and the client-authored `decisionFailure` override messages from `format.js`).

Files:
* apps/reviewer-app/frontend/src/i18n.js - new dictionary + translate() module

Success criteria:
* Every string in the research document's reviewer-app inventory has a corresponding key in both `en-CA` and `fr-CA`.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("apps/reviewer-app/frontend Inventory") - full string inventory

Dependencies:
* None (new file).

### Step 4.2: Create the reviewer-app `useLanguage` hook

Create `apps/reviewer-app/frontend/src/useLanguage.js`, identical in behavior to Step 1.2's hook (own `localStorage` key `fhaf-ui-language`, same `document.documentElement.lang` side effect).

Files:
* apps/reviewer-app/frontend/src/useLanguage.js - new hook

Success criteria:
* Same as Step 1.2, scoped to the reviewer-app.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Design for the Frontend Toggle") - shared hook design

Dependencies:
* Step 4.1 (`i18n.js` exports).

### Step 4.3: Validate phase changes

Validation commands:
* `npm run build` (in `apps/reviewer-app/frontend`) - confirms new modules compile cleanly

## Implementation Phase 5: Reviewer-app UI translation and format.js localization

<!-- parallelizable: true -->

### Step 5.1: Wire the language toggle and translate all UI strings in main.jsx

Update `apps/reviewer-app/frontend/src/main.jsx` to call `useLanguage()`, render the same toggle pattern as web-chat, translate the `NOTICE` constant, queue table headers, empty-state messages, decision buttons, reason-code prompt, approve confirmation, case detail labels, and audit trail rendering. Add `'X-UI-Language': language` to every authenticated fetch call (queue load, case detail load, approve/reject/revise). This step explicitly reverses AD-05/WI-24 from `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md`.

Files:
* apps/reviewer-app/frontend/src/main.jsx - replace inline strings with `t()`, add toggle control, add language header to fetch calls

Discrepancy references:
* Reverses AD-05 and closes WI-24 from `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md` — recorded as an explicit Plan Deviation in the Planning Log (DD-01).

Success criteria:
* No hardcoded English UI string literals remain in JSX text nodes, `aria-label`, or `title` attributes (dynamic values excepted).
* Every authenticated fetch call includes the `X-UI-Language` header matching the active language.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("apps/reviewer-app/frontend Inventory") - full inventory
* .copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md (AD-05, WI-24) - decision being reversed

Dependencies:
* Implementation Phase 4 completion (`i18n.js`, `useLanguage.js`).

### Step 5.2: Localize format.js

Add a `language` parameter (defaulting to `DEFAULT_LANGUAGE` from `i18n.js`) to `formatTimestamp`, `formatList`, `calculationLabel`, `premiumView`, and `decisionFailure`. Replace their hardcoded English literals (`'Unknown'`, `'None'`, `'not calculated'`, `'Amount unverifiable'`, `'no currency recorded'`, `'Not priced'`, and the four `decisionFailure` override messages for 403/409/404/401) with lookups into the new `i18n.js` dictionary. Change `formatAmount`'s hardcoded `Intl.NumberFormat('en-CA', ...)` locale to use the active `language` for digit-grouping conventions.

Files:
* apps/reviewer-app/frontend/src/format.js - add `language` parameter to helpers, replace hardcoded strings with dictionary lookups

Success criteria:
* Calling any updated helper with `'fr-CA'` returns French text; calling with `'en-CA'` (or omitting the parameter) returns today's exact English text unchanged.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("apps/reviewer-app/frontend Inventory" - format.js bullet, "Recommended Mechanism for Backend Localization" step 7) - full helper-by-helper inventory and client-override rationale

Dependencies:
* Step 4.1 (`i18n.js`).

### Step 5.3: Update reviewer-app frontend tests

Update `apps/reviewer-app/frontend/tests/format.test.js` to pass a `language` argument through each call under test and add French-language expectations alongside the existing English ones.

Files:
* apps/reviewer-app/frontend/tests/format.test.js - add `language` parameter and fr-CA expectations

Success criteria:
* `node --test tests/*.test.js` passes in `apps/reviewer-app/frontend`.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("apps/reviewer-app/frontend Inventory" - test file note)

Dependencies:
* Step 5.2 completion.

### Step 5.4: Update the reviewer-lab documentation's English-only callout

`docs/labs/lab-13-reviewer-ui.md` (around line 25) contains an explicit `> [!NOTE]` callout: "The reviewer interface is English only... this surface serves internal reviewers during the pilot and was scoped to a single language." This becomes factually false once Step 5.1 ships. Replace the callout with a short note describing the bilingual toggle (matching the tone of the applicant-chat description already in the same paragraph).

Files:
* docs/labs/lab-13-reviewer-ui.md - replace the English-only callout with a bilingual-toggle description

Discrepancy references:
* Addresses the promoted portion of DR-02 in the Planning Log (Plan Validator finding): a direct factual contradiction, not a discretionary refresh, so it is handled in-scope rather than deferred to follow-on work.

Success criteria:
* The lab no longer claims the reviewer interface is English-only.

Context references:
* docs/labs/lab-13-reviewer-ui.md (Lines 23-25) - exact callout text being replaced

Dependencies:
* Step 5.1 completion (the toggle must exist for the doc to describe it accurately).

### Step 5.5: Validate phase changes

Validation commands:
* `npm run build` (in `apps/reviewer-app/frontend`) - production build succeeds with translated UI
* `node --test tests/*.test.js` (in `apps/reviewer-app/frontend`) - unit tests pass

## Implementation Phase 6: Reviewer-app backend bilingual error catalog

<!-- parallelizable: true -->

### Step 6.1: Create the reviewer-app message catalog

Create `apps/reviewer-app/messages.py` mirroring Step 3.1's structure, with codes `SIGNIN_UNAVAILABLE`, `INVALID_TOKEN`, `APP_NOT_AUTHORIZED`, `SCOPE_REQUIRED`, `ROLE_REQUIRED`, `IDENTITY_REQUIRED`, `SIGNIN_REQUIRED` (auth), `CASE_NOT_FOUND`, `SELF_APPROVAL` (existing code, text unchanged), `INVALID_TRANSITION`, `CASE_ALREADY_EXISTS`, `STORE_UNAVAILABLE`, `REQUEST_TOO_LARGE`, `STALE_REVISION` (for the inline `decide()` pre-check), each preserving today's exact English wording.

Files:
* apps/reviewer-app/messages.py - new bilingual message catalog

Discrepancy references:
* Closes WI-23 from reviewer-app-log.md by giving every error path a stable code, not just `SELF_APPROVAL`.

Success criteria:
* `message('SELF_APPROVAL', 'en-CA')` equals the current literal text so `format.js`'s `SELF_APPROVAL`-keyed branch and existing tests keep working unless intentionally updated.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Backend Error Surfaces" - `apps/reviewer-app/app.py` bullet) - enumerated handlers and codes

Dependencies:
* None (new file).

### Step 6.2: Add codes and localization to reviewer-app exception handlers

In `apps/reviewer-app/app.py`, add the same flattening `HTTPException` handler as Step 3.2 (needed for the auth-path errors and the inline `decide()` `HTTPException`). Update the existing `CaseNotFoundError`, `InvalidTransitionError`, `CaseAlreadyExistsError`, and `ApprovalRepositoryError` handlers (each already receives `request`) to read `X-UI-Language` from `request.headers` and return `{"detail": message(code, language), "code": code}` for their respective new codes; update the `SelfApprovalError` handler to use `message('SELF_APPROVAL', language)` instead of its hardcoded string (text unchanged). Update the inline `decide()` `HTTPException` and the size-limit middleware's 413 response the same way.

Files:
* apps/reviewer-app/app.py - add flattening handler, add codes/localization to all 5 domain handlers, inline `decide()` exception, and middleware 413 response

Success criteria:
* Every one of the 6 error paths returns a stable `code` and localized `detail` based on `X-UI-Language`.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Recommended Mechanism for Backend Localization" steps 3, 5) - handler-level localization design

Dependencies:
* Step 6.1 (`messages.py`).

### Step 6.3: Localize apps/reviewer-app/auth.py

Apply the same change as Step 3.3 to `ReviewerAuth.verify`/`ReviewerAuth.authorize` using the codes from Step 6.1, and update the `identity()` dependency in `apps/reviewer-app/app.py` to pass the resolved language into `authorize()`.

Files:
* apps/reviewer-app/auth.py - thread `language` parameter, raise coded/localized exceptions
* apps/reviewer-app/app.py - pass resolved language into `verifier.authorize(...)` calls

Success criteria:
* Each of the 7 `ReviewerAuth` error paths returns the correct code and, given `X-UI-Language: fr-CA`, the correct French text.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Backend Error Surfaces" - `apps/reviewer-app/auth.py` bullet)

Dependencies:
* Step 6.1 (`messages.py`), Step 6.2 (flattening handler).

### Step 6.4: Update reviewer-app backend tests

Update `apps/reviewer-app/tests/test_app.py` (including the exact-body assertion at the line noted in the research document, `{"detail": "The case store is unavailable."}`) and `apps/reviewer-app/tests/test_auth.py` so every error-body assertion includes `"code"`, and add representative `X-UI-Language: fr-CA` test cases plus a default-fallback case, matching Step 3.5's pattern.

Files:
* apps/reviewer-app/tests/test_app.py - update body assertions, add fr-CA cases
* apps/reviewer-app/tests/test_auth.py - update body assertions, add fr-CA cases

Success criteria:
* `pytest apps/reviewer-app/tests` passes.

Context references:
* .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Backend Error Surfaces" - test coverage note)

Dependencies:
* Steps 6.1-6.3 completion.

### Step 6.5: Validate phase changes

Validation commands:
* `pytest apps/reviewer-app/tests` - backend unit tests pass with codes + bilingual text

## Implementation Phase 7: Validation

<!-- parallelizable: false -->

### Step 7.1: Run full project validation

Execute all validation commands for both apps:
* `npm run build` (in `apps/web-chat/frontend` and `apps/reviewer-app/frontend`)
* `node --test tests/*.test.js` (in both `frontend/tests` directories)
* `pytest apps/web-chat/tests apps/reviewer-app/tests`
* `pytest apps/workshop/tests` - confirms the deliberate exclusion of `apps/workshop` from this task caused no regressions

### Step 7.2: Fix minor validation issues

Iterate on lint errors, build warnings, and test failures surfaced by Step 7.1. Apply fixes directly when corrections are isolated (e.g. a missed string, a stale test assertion).

### Step 7.3: Report blocking issues

Document any failures that require design changes beyond minor fixes (e.g. a translation key collision, an `Intl` locale not supported in the runtime) and recommend follow-up research/planning rather than large-scale inline fixes.

## Dependencies

* Node.js + npm (existing `apps/web-chat/frontend`, `apps/reviewer-app/frontend` toolchains)
* Python + pytest (existing `apps/web-chat`, `apps/reviewer-app` toolchains)
* No new third-party packages (deliberately hand-rolled i18n, matching existing dependency-light convention)

## Success Criteria

* Both frontends render entirely in the selected language (`en-CA` default, `fr-CA` on toggle), persisted via `localStorage`, with no leftover hardcoded English text nodes.
* `apps/web-chat/frontend/src/samples.js` demo queries are fully bilingual.
* Every backend error response carries a stable `code` and localizes `detail` based on `X-UI-Language`, defaulting to today's exact English text when the header is absent/unrecognized.
* All existing and updated test suites pass: `apps/web-chat/tests`, `apps/reviewer-app/tests`, both frontends' `tests/*.test.js`, and `apps/workshop/tests` (unchanged).
* `apps/workshop` is explicitly and intentionally left untranslated, per the Planning Log rationale.
