<!-- markdownlint-disable-file -->
# Release Changes: Bilingual UI Apps (web-chat, reviewer-app)

**Related Plan**: bilingual-ui-apps-plan.instructions.md
**Implementation Date**: 2026-09-16

## Summary

Adds a manual EN/FR toggle, full UI-string translation, and a backend bilingual error-message catalog to `apps/web-chat` and `apps/reviewer-app`, plus bilingual demo-query data in `apps/web-chat/frontend/src/samples.js`.

## Changes

### Added

* apps/web-chat/frontend/src/i18n.js - bilingual (en-CA/fr-CA) translation dictionary + `translate()` lookup
* apps/web-chat/frontend/src/useLanguage.js - `useLanguage()` hook (localStorage persistence, `document.lang` side effect)
* apps/web-chat/messages.py - bilingual backend error-message catalog (18 codes) + `pick_language`/`message`
* apps/reviewer-app/frontend/src/i18n.js - bilingual (en-CA/fr-CA) translation dictionary + `translate()` lookup
* apps/reviewer-app/frontend/src/useLanguage.js - `useLanguage()` hook (localStorage persistence, `document.lang` side effect)
* apps/reviewer-app/messages.py - bilingual backend error-message catalog (14 codes) + `pick_language`/`message`

### Modified

* apps/web-chat/app.py - flattening `HTTPException` handler; `X-UI-Language` threaded through session/message endpoints and 413 middleware; `FoundryClient.events`/`content_text` now honor the resolved locale for agent answers
* apps/web-chat/auth.py - `PilotAuth.verify`/`authorize` take a `language` parameter; all 7 raise sites now coded + localized
* apps/web-chat/tests/test_app.py - error-body assertions gained `code`; added fr-CA, fallback, and bilingual-answer-streaming tests
* apps/web-chat/tests/test_auth.py - error-body assertions gained `code`; added fr-CA and missing-header fallback tests
* apps/web-chat/frontend/src/main.jsx - `useLanguage()` wired in; EN/FR toggle added to topbar; all strings translated; `X-UI-Language` header added to the shared `api()` fetch helper
* apps/web-chat/frontend/src/samples.js - demo query `title`/`prompt` converted to `{en-CA, fr-CA}` objects, reusing CASE-SYN-005's fixture fr-CA title verbatim
* apps/web-chat/frontend/src/i18n.js - added `topbar.switchToFrench`/`topbar.switchToEnglish` toggle-button keys
* apps/web-chat/frontend/src/style.css - toggle button styling
* apps/web-chat/frontend/tests/samples.test.js - assertions updated for `{en-CA, fr-CA}` shape, including per-locale fixture-id/length checks
* apps/reviewer-app/app.py - flattening `HTTPException` handler; domain exception handlers and `decide()`'s inline check now coded + localized via `X-UI-Language`
* apps/reviewer-app/auth.py - `ReviewerAuth.verify`/`authorize` take a `language` parameter; all 7 raise sites now coded + localized
* apps/reviewer-app/tests/test_app.py - fixed exact-body assertion to include `code`; added fr-CA and fallback cases
* apps/reviewer-app/tests/test_auth.py - error-body assertions gained `code` where detail text is checked; added fr-CA and fallback cases
* apps/reviewer-app/frontend/src/main.jsx - `useLanguage()` wired in; EN/FR toggle added to topbar; all strings translated; `X-UI-Language` header added via the shared `api()` helper; `language`/`t` threaded into `Premium`/`Queue`/`Detail`
* apps/reviewer-app/frontend/src/format.js - `formatAmount`/`formatTimestamp`/`formatList`/`calculationLabel`/`premiumView`/`decisionFailure` gained a `language` parameter and now look up translated literals
* apps/reviewer-app/frontend/src/i18n.js - added `activity.recordingDecision`, `topbar.languageToggleAria`, `reason.commands.reject`/`reason.commands.revise` keys
* apps/reviewer-app/frontend/tests/format.test.js - added fr-CA expectations alongside unchanged English assertions
* docs/labs/lab-13-reviewer-ui.md - replaced the English-only callout with a description of the new bilingual toggle

### Removed

## Additional or Deviating Changes

* Web-chat Phase 3 implementor introduced then self-fixed a name collision: the endpoint `async def message(...)` shadowed the module-level `messages.message()` catalog function within `create_app()`'s closure. Fixed by aliasing the import (`message as localize`).
  * No lasting impact; caught before phase completion.
* Web-chat Phase 3 implementor introduced then self-fixed a test bug: `sse()` serializes with `ensure_ascii=True`, so the new bilingual-streaming test had to parse SSE `data:` lines with `json.loads` rather than substring-matching raw accented characters.
  * No lasting impact; caught before phase completion.
* `pytest-asyncio` is not configured in this repo; the new web-chat `authorize()`-with-missing-header test uses `asyncio.run(...)` inside a sync test function instead of adding a new test-framework dependency.
* Web-chat Phase 1 implementor nested the sidebar brand strings (`sidebar.brand`/`sidebar.brandSub`) rather than under `topbar`, since that's where the markup actually lives in `main.jsx` — `topbar.pilotBadge` was still built as planned.
* Reviewer-app Phase 6 implementor added `code` assertions only to `test_auth.py` cases that already asserted `.detail` text content, rather than to every test that merely asserts `status_code` (no body to extend); added dedicated fr-CA/fallback tests instead where the new behavior is actually exercised.
* Confirmed `SelfApprovalError`'s existing English text matches the plan's assumption exactly: "You prepared this case and cannot decide it."
* Web-chat Phase 2 implementor preserved the pre-existing environment-badge bug (hardcoded literal instead of `config.environment` interpolation) per instructions, only translating the displayed literal text; tracked as WI-02 follow-on.
* Reviewer-app Phase 5 implementor fixed a Node ESM resolution issue: `format.js`'s new `./i18n` import required an explicit `.js` extension because `node --test` doesn't extension-guess like Vite does.

## Release Summary

All 7 implementation phases complete. 6 files added, 18 files modified, 0 removed.

**Added**: `apps/web-chat/frontend/src/i18n.js`, `apps/web-chat/frontend/src/useLanguage.js`, `apps/web-chat/messages.py`, `apps/reviewer-app/frontend/src/i18n.js`, `apps/reviewer-app/frontend/src/useLanguage.js`, `apps/reviewer-app/messages.py`.

**Modified**: both apps' `app.py` (flattening `HTTPException` handler, `X-UI-Language`-driven localization on every error path and the size-limit middleware; web-chat additionally threads the resolved locale into the agent's own streamed chat answers), both apps' `auth.py` (coded/localized raises), both apps' backend test suites (added `code` assertions, fr-CA cases, fallback cases), both apps' `main.jsx` (EN/FR toggle, full string translation, `X-UI-Language` header on every authenticated request), `apps/web-chat/frontend/src/samples.js` (bilingual demo-query data), `apps/reviewer-app/frontend/src/format.js` (localized formatting/error-mapping helpers), both frontends' test suites, and `docs/labs/lab-13-reviewer-ui.md` (corrected English-only callout).

**Dependency/infrastructure changes**: none — no new packages added to either frontend or backend; both apps' existing Node/npm and Python/pytest toolchains were reused as-is.

**Validation**: 145 automated tests passed across both frontends (`node --test`) and all three Python suites (`pytest apps/web-chat/tests`, `pytest apps/reviewer-app/tests`, `pytest apps/workshop/tests` — confirming the deliberate `apps/workshop` exclusion caused no regression), plus both frontend production builds (`npm run build`) succeeded with 0 failures.

**Deployment notes**: none — no environment variables, secrets, infra, or deployment steps changed. Both frontends are still built as static assets served the same way as before; both backends still respond with English by default when the new `X-UI-Language` header is absent, so this is backward-compatible with any existing client that doesn't send it.
