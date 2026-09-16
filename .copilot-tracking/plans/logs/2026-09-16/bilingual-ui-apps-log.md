<!-- markdownlint-disable-file -->
# Planning Log: Bilingual UI Apps (web-chat, reviewer-app)

## Discrepancy Log

### Unaddressed Research Items

* DR-01: `apps/web-chat`'s environment badge hardcodes "Staging pilot" text instead of interpolating `config.environment` (a pre-existing bug, unrelated to bilingual work).
  * Source: .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("Risks / Open Notes")
  * Reason: Fixing it is out of scope for a bilingual-UI task and would be unrelated scope creep; the plan translates the literal displayed text as-is and structures the key so a future fix is a one-line change.
  * Impact: low
* DR-02: `docs/labs/lab-13-reviewer-ui.md` (line 25) contains an explicit `[!NOTE]` callout stating "The reviewer interface is English only. Unlike the applicant-facing chat, which is bilingual because applicants are, this surface serves internal reviewers during the pilot and was scoped to a single language." This is not just a stale screenshot — it is a prose claim that becomes factually false the moment Phase 5 ships. (`docs/labs/lab-11-web-chat.md` was also checked; it only discusses the agent's existing bilingual answer payload from Lab 07, not frontend chrome, so it needs no correction from this plan.)
  * Source: docs/labs/lab-13-reviewer-ui.md (line 25); verified by direct read this session.
  * Resolution: Promoted to in-scope work — Implementation Phase 5, Step 5.4 replaces the callout with an accurate bilingual-toggle description. The broader screenshot-refresh concern for both labs remains follow-on work (WI-01).
  * Impact: medium (upgraded from low — this is a direct textual contradiction a lab participant will read, not a discretionary screenshot update)
* DR-03: `apps/web-chat/app.py`'s `content_text(content, locale="en-CA")` (line 96) was called at its one call site (line 147, inside `FoundryClient.events`) with **no `locale` argument**, so it always resolved to the hardcoded default `"en-CA"`. The agent's actual chat-answer text — the single most substantive piece of user-facing content in the app — would otherwise have remained always-English after this plan shipped, regardless of the new EN/FR toggle. The research document quoted this exact function signature under "Existing Bilingual Conventions to Match" but characterized the chat answers as "already bilingual," which was inaccurate given the hardcoded call site.
  * Source: apps/web-chat/app.py (lines 96-97, 147); research document ("Existing Bilingual Conventions to Match").
  * Resolution: Addressed in-scope — Implementation Phase 3, Step 3.4 threads the resolved `X-UI-Language` through `generate()` → `FoundryClient.events()` → `content_text()`. No longer an open gap.
  * Impact: was critical; resolved by adding Step 3.4.
* DR-04: `apps/web-chat/frontend/tests/samples.test.js`'s existing assertions (`sample.prompt.includes(fixtureId)`, `sample.prompt.length < 8000`) check content correctness, not just shape. The initial Details Step 2.3 draft only instructed updating the test to "assert the new `{en-CA, fr-CA}` object shape ... instead of plain strings" without requiring the fixtureId-inclusion and length-bound checks to be re-applied per locale.
  * Source: apps/web-chat/frontend/tests/samples.test.js; .copilot-tracking/details/2026-09-16/bilingual-ui-apps-details.md (Step 2.3).
  * Resolution: Addressed in-scope — Step 2.3 now explicitly requires both checks for both `en-CA` and `fr-CA` values. No longer an open gap.
  * Impact: was major; resolved by updating Step 2.3.

### Plan Deviations from Research

* DD-01: The plan reverses AD-05 and closes WI-24 from `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md`, which deliberately kept the reviewer-app UI English-only.
  * Research recommends: AD-05 recorded English-only as the shipped decision, with WI-24 as an open follow-up question ("Decide whether reviewer-app copy needs fr-CA... reviewer copy stays English-only", medium impact).
  * Plan implements: Full fr-CA translation of the reviewer-app UI, matching web-chat and the rest of the bilingual repository.
  * Rationale: The user explicitly requested "make the UI apps bilingual" in this task, a direct, current instruction that supersedes the prior recorded decision. WI-24's own text already anticipated this ("the repository is otherwise bilingual").
* DD-02: `apps/workshop` is excluded from all code changes despite being named in the user's scope answer.
  * Research recommends: The user's scope answer named `apps/workshop` alongside the two frontends.
  * Plan implements: No changes to `apps/workshop`; its Python docstrings and internal exception messages are treated as developer-facing source, consistent with every other backend module in the repo (which are English-only; only response/UI text is bilingual).
  * Rationale: `apps/workshop` has no frontend or running UI — it is lab-exercise support code. Its only English text is docstrings and internal exception messages never rendered to any user. Translating them would add bilingual Python source with no learner-facing or runtime benefit and diverge it from the byte-identical copy relationship noted in the prior reviewer-app planning log, for no behavioral gain.
* DD-03: Details Step 3.3's success criteria previously stated "Each of the 6 `PilotAuth` error paths returns the correct code," but `apps/web-chat/auth.py` has 7 `raise HTTPException(...)` sites (verified) and Step 3.1's message catalog defines 7 matching codes (`SIGNIN_UNAVAILABLE`, `INVALID_TOKEN`, `APP_NOT_AUTHORIZED`, `SCOPE_REQUIRED`, `MEMBERSHIP_REQUIRED`, `IDENTITY_REQUIRED`, `SIGNIN_REQUIRED`), matching the research document's own 7-item enumeration under "Backend Error Surfaces."
  * Research recommends: 7 enumerated `PilotAuth` error paths (research document, "Backend Error Surfaces" — `apps/web-chat/auth.py` bullet), matching Step 3.1's 7-code catalog.
  * Plan implemented: Step 3.3 success criteria previously stated 6 paths.
  * Rationale: Miscount, not an intentional scope reduction.
  * Resolution: Corrected — Step 3.3's success criteria now states 7 paths, explicitly enumerating `verify`'s 6 raises plus `authorize`'s missing/malformed-header raise. No longer an open gap.
  * Impact: was minor; resolved.

### Implementation Deviations

* DD-04: Web-chat's `create_app()` defines a route handler `async def message(...)` for the message-send endpoint, which shadowed the module-level `messages.message()` catalog function inside that closure's scope (Python resolves names lexically, not by import origin), silently turning every catalog call inside `create_app` into an un-awaited coroutine.
  * Plan specifies: Import and call `message(code, language)` directly per Step 3.1/3.2.
  * Implementation differs: The Phase 3 implementor aliased the import (`from messages import message as localize`) and calls `localize(...)` everywhere inside `create_app`, avoiding a route/decorator rename.
  * Rationale: Self-caught and fixed before phase completion; preserves the existing endpoint name and avoids a wider rename.
* DD-05: The bilingual-answer-streaming test needed to parse SSE `data:` lines with `json.loads` instead of substring-matching raw French text.
  * Plan specifies: No specific serialization detail was called out in Step 3.5.
  * Implementation differs: `sse()` serializes with `json.dumps(..., ensure_ascii=True)`, so accented characters appear as `\uXXXX` escapes in the raw response text; the test decodes each `data:` line via `json.loads` before asserting on `event["text"]`.
  * Rationale: Matches the serialization pattern already used elsewhere in the test file; avoids a flaky assertion.
* DD-06: Reviewer-app's `format.js` needed an explicit `.js` extension on its new `from './i18n'` import.
  * Plan specifies: No extension detail was called out in Step 5.2.
  * Implementation differs: Changed to `from './i18n.js'`.
  * Rationale: Node's native ESM resolver (used by `node --test`) requires explicit extensions for relative imports; Vite tolerates extension-less imports but the plain-Node test runner does not.
* DD-07: Web-chat's sidebar brand strings (`sidebar.brand`/`sidebar.brandSub`) are nested under `sidebar.*` in `i18n.js` rather than `topbar.*` as originally scoped in the Phase 1 prompt.
  * Plan specifies: Details Step 1.1 suggested a `topbar` area for brand strings.
  * Implementation differs: Nested under `sidebar` to match where that markup actually lives in `main.jsx`'s `<aside>` element.
  * Rationale: Matches actual component structure; `topbar.pilotBadge` (the string that does live in the topbar) was still built as scoped.
* DD-08: `pytest-asyncio` is not configured in this repository (no marker/config, no prior async test).
  * Plan specifies: No test-framework detail was called out for the new `authorize()`-with-missing-header web-chat test.
  * Implementation differs: The new test uses `asyncio.run(...)` inside a synchronous test function rather than `@pytest.mark.asyncio`.
  * Rationale: Avoids introducing a new test-framework dependency for a single test case.
* DD-09: Reviewer-app's `test_auth.py` gained `code` assertions only on cases that already asserted `.detail` text content, not on every test that merely asserts `status_code`.
  * Plan specifies: "every error-body assertion gains the code field" (Step 6.4 instruction).
  * Implementation differs: Tests that assert only `status_code` (no body content) were left unchanged; dedicated new fr-CA/fallback tests were added instead to exercise the coded/localized body where it matters.
  * Rationale: There is no body assertion to extend on a status-code-only test; the new tests cover the actual new behavior more directly.



### Selected: Hand-rolled per-app dictionaries + React Context/hook, backend message catalog keyed by stable error codes

* Approach: Each frontend gets its own small `i18n.js` (dictionary + `translate()`) and `useLanguage.js` hook (state + `localStorage` persistence + `document.documentElement.lang` side effect); each backend gets its own `messages.py` catalog keyed by a new stable `code` field, selected via an `X-UI-Language` request header sent by the frontend on every authenticated call, with a single flattening `HTTPException` handler per app so response shapes stay backward-compatible.
* Rationale: Matches the repository's existing dependency-light convention (no i18n library in either `package.json` today) and its existing per-app duplication pattern (`auth.py` is already duplicated across apps rather than shared). Scope (~40-60 strings per app, ~15-20 backend error paths per app) does not justify a third-party i18n library.
* Evidence: .copilot-tracking/research/2026-09-16/bilingual-ui-apps-research.md ("No i18n Library Needed", "Recommended Mechanism for Backend Localization")

### IP-01: Third-party i18n library (react-i18next / react-intl) for the frontends

* Approach: Add `react-i18next` (or similar) to both frontends for translation management, pluralization, and locale formatting.
* Trade-offs: Provides richer features (pluralization rules, lazy-loaded locale bundles, ICU message format) but adds a new dependency to a codebase that currently has none, increases bundle size, and requires learning/maintaining a library API for a string count that doesn't need it.
* Rejection rationale: Disproportionate to the actual scope (two small SPAs, ~50 strings each, no pluralization or locale-bundle-splitting need) and inconsistent with the project's minimal-dependency convention observed in both `package.json` files.

### IP-02: Auto-detect browser language instead of a manual toggle

* Approach: Derive the initial language from `navigator.language` / `Accept-Language` instead of defaulting to `en-CA` with a manual toggle.
* Trade-offs: Removes one click for users whose browser is already set to French, but removes explicit user control and could surprise a bilingual user whose OS locale doesn't match their preferred UI language for this specific app.
* Rejection rationale: The user explicitly answered this clarifying question in favor of a manual toggle with `en-CA` default and `localStorage` persistence; not revisited.

### IP-03: Client-side-only bilingual error text (no backend changes)

* Approach: Keep backend error responses English-only; have the frontend map known `status`/`detail` combinations to French text entirely client-side (extending `format.js`'s existing `decisionFailure` override pattern to every error, including web-chat).
* Trade-offs: Avoids all backend changes (Phases 3 and 6) but requires the frontend to reverse-engineer meaning from raw English server text for the fallback case, which is fragile (any wording change in `app.py` silently breaks translation) and doesn't scale past the few cases `format.js` already special-cases.
* Rejection rationale: The user explicitly answered the clarifying question in favor of a backend catalog keyed by error code, precisely to avoid this fragility; not revisited.

## Suggested Follow-On Work

* WI-01: Update `docs/labs/lab-11-web-chat.md` and refresh any screenshots in `docs/labs/lab-13-reviewer-ui.md` showing the prior English-only reviewer UI (the callout text itself is now fixed in-scope by Step 5.4). Also check `docs/fr/labs/` counterparts if present. (low)
  * Source: DR-02 above.
  * Dependency: This plan's Phases 1-6 must ship first so screenshots reflect the final UI.
* WI-02: Fix the web-chat environment badge to interpolate `config.environment` instead of hardcoding "Staging pilot" text. (low)
  * Source: DR-01 above (pre-existing bug, out of scope here).
  * Dependency: None.
* WI-03: Consider adding automated visual/snapshot tests for both languages to catch future untranslated strings introduced by new features. (low)
  * Source: Identified during planning as a gap not addressed by this task's manual string inventory approach.
  * Dependency: This plan's completion (establishes the baseline to snapshot).
* WI-04: `format.js`'s `formatAmount` still returns a semi-bare `'1425.00 not-a-currency'` for an invalid-but-non-empty ISO currency code (carried over from WI-21 in the prior reviewer-app-log.md); this plan does not fix that underlying data-quality issue, only translates around it. (low)
  * Source: Carried over from `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md`, WI-21.
  * Dependency: None.
