<!-- markdownlint-disable-file -->
# Task Research: Bilingual UI Apps (web-chat, reviewer-app)

## Scope

Make `apps/web-chat` and `apps/reviewer-app` bilingual (English/French) end to end: a manual EN/FR toggle in each frontend, all static UI text and demo/sample data translated, and backend error text localized via a small message catalog. `apps/workshop` was also named in scope but has no frontend; findings below cover it separately.

## Prior Decisions This Request Overrides

* `.copilot-tracking/plans/logs/2026-09-15/reviewer-app-log.md`, AD-05 and WI-24: the reviewer UI was deliberately shipped English-only, matching web-chat, with fr-CA left as an open item ("Decide whether reviewer-app copy needs fr-CA... but the repository is otherwise bilingual", impact medium). This task closes WI-24 by adding fr-CA to both surfaces.
* `.copilot-tracking/plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md` scoped "bilingual" to the workshop *lab curriculum* (docs/labs, docs/fr/labs) and the agent's own bilingual response templates, not the React frontends. That work is complete and unaffected by this task.

## User Decisions Gathered (via clarifying questions in conversation)

* Manual EN/FR toggle button in each app's header. Default `en-CA`. Persisted per-browser via `localStorage`.
* Backend error text becomes bilingual too: a small message catalog keyed by a stable error `code`, selected by a language the frontend sends with each request.
* Scope: `apps/web-chat` + `apps/reviewer-app` frontends, `apps/web-chat/frontend/src/samples.js` demo queries, plus `apps/workshop` (see below).

## apps/workshop Has No UI Surface

`apps/workshop/` contains `calculator.py`, `approval_repository.py`, and their tests — no `frontend/`, no FastAPI app. It backs the hands-on lab exercises (already bilingual in `docs/labs/` + `docs/fr/labs/`), not a running UI. The only English text in these modules is:
* Module/class/method docstrings (developer documentation).
* Internal exception messages (e.g. `CaseAlreadyExistsError(f"Case {case_id!r} already exists")`) that are never rendered in any UI — they exist for developers reading stack traces and tests asserting exception types, not for reviewers or applicants.

Translating these would mean bilingual Python docstrings/exception text with no runtime or learner-facing benefit, and would diverge `apps/workshop/approval_repository.py` from the byte-identical copy noted in AD-04/RI-02 of the reviewer-app log for no behavioral gain. Recommendation: exclude `apps/workshop` from code changes in this task; keep it as English developer-facing source, matching every other Python module in the repo (which are all English-only, including the agent and both apps' own backend code — only user-facing *response and UI text* is bilingual anywhere in this repository). Record as a follow-on note, not a blocking gap.

## Existing Bilingual Conventions to Match

* `data/synthetic/fixtures/*.json` and `data/synthetic/rulebook.json`: every user-facing string is a `{"en-CA": "...", "fr-CA": "..."}` object, e.g. `case-syn-005-missing-plan.json` already has `"fr-CA": "Sélection de régime manquante"`. New bilingual data (samples.js) should reuse this exact key shape and, where the same concept already has an approved French translation in a fixture, reuse that translation verbatim for consistency.
* `src/quote-preparation-agent`'s agent-facing response text is bilingual today (`apps/web-chat/app.py`'s `content_text(content, locale="en-CA")` reads a `{"en-CA","fr-CA"}` map the agent emits) — the applicant chat *answers* are already bilingual; only the surrounding chat UI chrome (buttons, labels, disclaimers) is English-only.
* `docs/_includes/head_custom.html` implements bilingual EN/FR nav-hiding for the Jekyll docs site — an unrelated static-site pattern, not reusable code, but confirms `en`/`fr` (docs) vs `en-CA`/`fr-CA` (data) are the two locale-tag conventions already in use. This task uses `en-CA`/`fr-CA` throughout, matching the data/fixture convention since these are Canadian French UI strings.

## apps/web-chat/frontend Inventory

* `src/main.jsx` (single file, ~180 lines): all UI text is inline JSX (no existing string extraction). Every visible label, aria-label, button title, empty-state message, and the fixed disclaimer footer is a plain English string literal. No i18n library is present; `package.json` has no `i18next`/`react-intl`/etc.
* `src/samples.js`: `sampleQueries` array with English-only `title` and `prompt` per demo query (3 entries, ids `case-syn-002`, `case-syn-004`, `case-syn-005`). These correspond 1:1 to the bilingual fixtures already in `data/synthetic/fixtures/`; French translations should track the tone/terminology already established there (e.g. reuse "Sélection de régime manquante" for the CASE-SYN-005 title).
* `src/request.js`, `src/stream.js`: no user-facing strings (pure request/stream helpers), out of scope.
* `frontend/tests/samples.test.js`: currently likely asserts `title`/`prompt` are strings; will need updating once they become `{en-CA, fr-CA}` objects.
* `index.html`: static `<html lang="en">`; should track the active language at runtime (`document.documentElement.lang`).

## apps/reviewer-app/frontend Inventory

* `src/main.jsx` (~290 lines): same pattern as web-chat — all text inline. Larger surface: queue table headers, case detail fact lists (State/Revision/Preparer/Reviewer/Created/Submitted, Premium/Currency/Period/Status/Rule ids/Issues/Rulebook version), decision UI (Approve/Reject/Send back for revision, reason-code prompt, approve confirmation), audit trail rendering, and the fixed `NOTICE` disclaimer constant.
* `src/format.js`: pure helpers with English-only output —
  * `formatTimestamp` returns `'Unknown'` for a missing value and otherwise formats via `Intl` with a hardcoded `'en-CA'` locale.
  * `formatList` returns `'None'` for an empty/absent list.
  * `calculationLabel` returns `'not calculated'` for an absent status.
  * `premiumView` returns English `label`/`reason` strings for the `unverifiable` (`'Amount unverifiable'`, `'no currency recorded'`) and `unpriced` (`'Not priced'`) states.
  * `decisionFailure(status, detail, code)` hardcodes client-side override messages for 403 (self-approval and generic), 409 (stale/conflict), 404 (case gone), 401 (session expired), each independent of whatever `detail` the server sent; only the final fallback branch surfaces the raw server `detail` text verbatim.
  * `formatAmount` uses `Intl.NumberFormat('en-CA', ...)` — the locale here affects only digit grouping conventions, not translated words, but should still track the active language for correctness.
* `frontend/tests/format.test.js`: exercises all of the above with English-only expected strings; will need a `language` parameter threaded through and both-language expectations added.

## Backend Error Surfaces

Both apps register a security-headers middleware, mount `frontend/dist`, and (in `apps/reviewer-app/app.py`) domain exception handlers. All user-facing error text is currently a bare English string with **no stable machine-readable code**, except the one `SELF_APPROVAL` 403 in reviewer-app (`format.js`'s `SELF_APPROVAL` constant depends on it). Enumerated raise sites:

**`apps/web-chat/auth.py`** (`PilotAuth`): 503 sign-in verification unavailable; 401 invalid/expired token; 403 app not authorized; 403 missing `Chat.Access` scope; 403 missing pilot group membership; 401 missing `oid`; 401 missing/malformed `Authorization` header.

**`apps/reviewer-app/auth.py`** (`ReviewerAuth`): identical structure, "Review.Access" scope and `Reviewer` app role in place of the pilot group.

**`apps/web-chat/app.py`**: `SessionStore.create` (429 pilot capacity, 429 too many sessions for owner), `SessionStore.get` (404 not found, 404 expired), the size-limit middleware (413), `DELETE /api/conversations/{id}` (409 busy), `POST .../messages` (409 idempotency-key reuse, 409 already busy, 409 turn limit, 429 pilot busy), and the SSE `generate()` error frames ("assessment could not complete", "service temporarily unavailable" — these are not `HTTPException`s, they are `sse({"type": "error", "text": ...})` payloads written directly into the stream).

**`apps/reviewer-app/app.py`**: exception handlers for `CaseNotFoundError` (404, no code today), `SelfApprovalError` (403, code `SELF_APPROVAL`), `InvalidTransitionError` (409, no code), `CaseAlreadyExistsError` (409, no code), `ApprovalRepositoryError` (500, no code), the size-limit middleware (413), and an inline `HTTPException(409, ...)` in `decide()` for a revision mismatch detected before the store call.

**Existing test coverage that pins current response bodies exactly** (must be updated, not just extended): `apps/web-chat/tests/test_app.py`, `apps/web-chat/tests/test_auth.py`, `apps/reviewer-app/tests/test_app.py` (e.g. line 312: `assert response.json() == {"detail": "The case store is unavailable."}`), `apps/reviewer-app/tests/test_auth.py`.

## Recommended Mechanism for Backend Localization

1. Frontend sends the active language on every authenticated `fetch` as a header, e.g. `X-UI-Language: fr-CA`, sourced from the same state driving the UI toggle.
2. Each app gets its own `messages.py` (matching the existing per-app duplication convention — `auth.py` is already duplicated rather than shared) with `LANGUAGES`, `DEFAULT_LANGUAGE = "en-CA"`, a `pick_language(header_value)` helper, and a `MESSAGES: dict[code, dict[locale, text]]` catalog plus a `message(code, language)` accessor.
3. FastAPI's default `HTTPException` handler wraps `exc.detail` under a `"detail"` key unconditionally, so passing a dict (`{"detail": text, "code": code}`) as `exc.detail` would nest it. Add one small custom `HTTPException` handler per app that flattens: if `exc.detail` is a `dict`, return it as-is (as the JSON body); otherwise keep today's `{"detail": exc.detail}` shape. This lets every raise site become `raise HTTPException(status, {"detail": message(code, language), "code": code})` without changing the response shape reviewer-app's frontend already parses (`body.detail`, `body.code`).
4. `PilotAuth.authorize`/`ReviewerAuth.authorize` (and `verify`) need `language` threaded in as a parameter from the `identity()` dependency, which reads the header via `Header(alias="X-UI-Language", default=None)`.
5. Reviewer-app's existing domain exception handlers (`case_not_found`, `invalid_transition`, `already_exists`, `repository_failure`) gain stable codes (e.g. `CASE_NOT_FOUND`, `INVALID_TRANSITION`, `CASE_ALREADY_EXISTS`, `STORE_UNAVAILABLE`) and read the request's language header directly (handlers receive `request`, so `request.headers.get("X-UI-Language")` is available with no extra plumbing).
6. The web-chat SSE error frames need the language read once at the top of the `message()` endpoint (from the same header) and passed into `generate()`'s closure, since that code path never goes through an exception handler.
7. Frontend does **not** need its own copy of backend error text — the server renders the string in whichever language the client asked for, so the frontend simply displays `body.detail` as today. The one exception is reviewer-app's `format.js#decisionFailure`, which currently *overrides* the server's `detail` with its own hardcoded English strings for 401/403/404/409; those overrides move into the frontend's own i18n dictionary since they are deliberately client-authored copy, independent of the server's text.

## Design for the Frontend Toggle

* A small `i18n.js` per app (not shared — apps have no shared package today) exporting `LANGUAGES = ['en-CA', 'fr-CA']`, `DEFAULT_LANGUAGE = 'en-CA'`, a nested string dictionary, and a `translate(language, key, vars)` lookup supporting simple `{name}` interpolation (needed for e.g. `${environment} pilot` / `pilote ${environment}` word-order differences).
* A `useLanguage()` hook (colocated in `main.jsx` or a small `useLanguage.js`) holding `language` state initialized from `localStorage.getItem('fhaf-ui-language')` (falling back to `DEFAULT_LANGUAGE`), persisting on change, and exposing a bound `t(key, vars)`.
* A visible toggle control in each app's header/topbar (e.g. a two-state button showing the *other* language's short label, "FR"/"EN"), wired to flip `language` and persist it.
* `document.documentElement.lang` updated on language change (accessibility/SEO correctness for screen readers).
* Every authenticated `fetch` call's headers gains `'X-UI-Language': language`.

## No i18n Library Needed

Given the string count (~40-60 UI strings per app) and the project's existing minimal-dependency style (no i18n library present, `package.json` dependency lists are short and deliberate), a hand-rolled dictionary + hook is proportionate. Adding `react-i18next`/`react-intl` would be over-engineering for this scope (YAGNI) and would need justification neither the codebase nor the user's answers called for.

## Risks / Open Notes

* Web-chat's environment badge (`<span className="environment"><span />Staging pilot</span>`) is a pre-existing, out-of-scope bug: it hardcodes "Staging pilot" instead of interpolating `config.environment` the way reviewer-app's badge does. This task should translate the literal text as-is (not fix the underlying bug) to avoid unrelated scope creep, and should structure the translation key so a future fix is a one-line change.
* Every backend Python test asserting an exact response body (`test_app.py`, `test_auth.py`, both apps) must be updated once a `"code"` field is added, even where the English wording itself doesn't change. This is mechanical but touches most of both test files.
* French translations should be reviewed for tone/terminology consistency with the fixtures' existing fr-CA strings (formal register, e.g. "veuillez", "soumission" not "devis", "régime" not "plan/forfait" — matching `data/synthetic/fixtures/*.json`).
