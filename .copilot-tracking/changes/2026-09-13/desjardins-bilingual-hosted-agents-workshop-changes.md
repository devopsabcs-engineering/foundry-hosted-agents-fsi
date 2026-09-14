<!-- markdownlint-disable-file -->
# Release Changes: Desjardins Bilingual Hosted Agents Workshop

**Related Plan**: desjardins-bilingual-hosted-agents-workshop-plan.instructions.md
**Implementation Date**: 2026-09-13

## Summary

Implementation in progress. This log is updated as each phase completes.

## Changes

### Added

* src/quote-preparation-agent/.gitkeep, mcp/application-server/.gitkeep, mcp/rulebook-server/.gitkeep, infra/.gitkeep, scripts/.gitkeep - Phase 1: placeholders for empty top-level directories.
* docs/_config.yml, docs/Gemfile - Phase 1: Jekyll site config adapted from the sibling repository's structural pattern (no branding copied).
* docs/index.md, docs/fr/index.md - Phase 1: reciprocal EN/FR landing pages linking to the future docs/labs/ index.
* data/synthetic/quote-contract.schema.json - Phase 2: full draft-07 JSON Schema for the quote-preparation contract.
* data/synthetic/rulebook.json - Phase 2: pinned base-rate/plan-add-on tables, marked WORKSHOP_AUTHORS_ONLY.
* data/synthetic/fixtures/case-syn-001.json, case-syn-002-sedan.json, case-syn-003-unsupported.json, case-syn-004-revision.json, case-syn-005-missing-plan.json - Phase 2: five schema-valid synthetic fixtures covering the exact-100000-cent case, SEDAN, TRAINING_BASIC, unsupported input, and revision invalidation.
* apps/workshop/calculator.py, apps/workshop/__init__.py, apps/workshop/tests/__init__.py, apps/workshop/tests/test_calculator.py - Phase 2: pure deterministic calculator and its unit tests (11 tests).
* requirements.txt - Phase 2: root Python manifest (pytest, jsonschema); none existed previously.
* apps/workshop/approval_repository.py - Phase 3: SQLite-backed ApprovalRepository with the full DRAFT/PENDING_REVIEW/APPROVED/REJECTED state machine, revision-invalidation, self-approval prevention, and idempotent approve/reject.
* apps/workshop/tests/test_approval_repository.py - Phase 3: 10 tests covering happy paths, self-approval rejection, revision invalidation, idempotency, and a threaded concurrency race.
* mcp/application-server/main.py, application_data_loader.py, requirements.txt, tests/test_application_server.py - Phase 4: read-only FastMCP service exposing get_application (known-fixture lookup, explicit not-found for unknown IDs).
* mcp/rulebook-server/main.py, rulebook_data_loader.py, requirements.txt, tests/test_rulebook_server.py - Phase 4: read-only FastMCP service exposing get_rulebook (pinned rate table lookup, explicit not-found for unknown IDs).
* src/quote-preparation-agent/state.py, toolbox.py, graph.py, main.py, __init__.py, requirements.txt, tests/test_graph.py, tests/test_toolbox.py - Phase 5: local (unhosted) LangGraph supervisor/specialist agent (intake -> reference lookup -> composition), wired to the Phase 4 MCP tools in-process and the Phase 2/3 calculator/approval repository; never calls approve/reject/revise.
* docs/labs/index.md, docs/labs/lab-00-setup.md through lab-09-teardown.md (10 files) - Phase 6: English lab curriculum grounded in the Phase 2-5 codebase.
* docs/fr/labs/index.md, docs/fr/labs/lab-00-setup.md through lab-09-teardown.md (10 files) - Phase 6: paired French lab curriculum, natural reviewed French, matching filenames/structure.
* scripts/build-workshop-deck.js, package.json - Phase 6: bilingual EN/FR PptxGenJS deck generator adapted from the sibling script; new root Node manifest.
* eval/golden-dataset.jsonl - Phase 7: 12 records (6 business, 6 fault) covering arithmetic exactness, self-approval, forged-actor/unauthorized-preview, unsupported-input, and revision-invalidation.
* eval/deterministic-tests/checks.py, eval/evaluation_gate.py, eval/tests/test_checks.py, eval/tests/test_evaluation_gate.py, eval/results.json - Phase 7: deterministic check functions and the evaluation gate script, run against the real Phase 2/3/5 code (no LLM judge).
* infra/modules/ai-foundry.bicep, mcp-container-apps.bicep, rbac.bicep, monitoring.bicep, infra/main.bicep, infra/main.parameters.json, infra/README.md, azure.yaml - Phase 8: author-only, undeployed Bicep modules and azd manifest for the two MCP services and the hosted agent, each carrying an explicit AUTHOR-ONLY/NOT-DEPLOYED banner citing Gates G2/G3/G6.

### Modified

* README.md - Phase 1: expanded from a one-line placeholder to a project overview stating the synthetic-only/non-binding/no-regulatory-endorsement boundary and the default Copilot-free learner path.

### Removed

* apps/workshop/.gitkeep, data/synthetic/.gitkeep - Phase 2: removed once real files populated these directories.
* mcp/application-server/.gitkeep, mcp/rulebook-server/.gitkeep - Phase 4: removed once real files populated these directories.
* src/quote-preparation-agent/.gitkeep - Phase 5: removed once real files populated this directory.
* eval/.gitkeep - Phase 7: removed once real files populated this directory.

## Additional or Deviating Changes

* Phase 1 created 8 new top-level directories (src, mcp, apps, data, eval, infra, scripts, plus docs/fr nested under the existing docs/ path) rather than a literal "9 directories" — the plan's directory count included docs/ itself, which was populated with docs/index.md rather than a placeholder. Not a functional deviation; noted per the Phase 1 completion report.
* docs/_config.yml's `url` field was left blank with a TODO rather than a guessed GitHub Pages URL, since the sibling repository's URL pattern isn't predictable from the repo name alone.
* Markdown lint (Step 1.3) was skipped: no markdownlint tool is installed locally and the environment has remote npm package fetches disabled. Directory/file structure and reciprocal links were confirmed manually instead.
* Phase 2's calculator issue codes use the JSON Schema's canonical enum (MISSING_JURISDICTION, MISSING_VEHICLE_CLASS, MISSING_PLAN, UNSUPPORTED_INPUT, EVIDENCE_UNAVAILABLE, RULE_VERSION_MISMATCH) instead of the illustrative names in the plan (UNSUPPORTED_VEHICLE_CLASS, etc.), to stay consistent with the authoritative schema from the platform-and-scenario-decision subagent research.
* Phase 2 combined the SEDAN and TRAINING_BASIC coverage requirements into a single fixture (case-syn-002-sedan.json) and added a fifth fixture (case-syn-005-missing-plan.json) for INCOMPLETE/missing-field coverage, within the plan's "1-2 more for coverage" allowance.
* Phase 3 consolidated concurrency/idempotency/authorization tests into one test_approval_repository.py file (10 tests) rather than the details file's suggested split into separate test_concurrency.py/test_authorization.py files, and created the SQLite schema inline in ApprovalRepository._init_schema() rather than a separate db/schema.sql file — simpler for a single-class repository, no functional gap.
* Phase 4's two MCP servers each use a uniquely named data-loader module (application_data_loader.py, rulebook_data_loader.py) instead of a generic data_loader.py name, to avoid a sys.modules collision when both servers' main.py entry points are loaded in the same pytest session. No Dockerfile was added for either server; deferred to Phase 8 (infrastructure scaffolding).
* Phase 5's toolbox.py calls the Phase 4 MCP servers' tool functions in-process (loading main.py under a private module name) rather than over a real MCP client/streamable-http session, since this phase is explicitly forbidden from running any hosted/networked deployment. Swapping to a real client session is deferred until Gates G2/G3/G6 clear. Test file names (test_graph.py, test_toolbox.py) differ from the details file's suggested test_agent_local.py per this execution's explicit instructions. Package version pins for langgraph/langchain-core are intentionally loose; exact pinning is Gate G3's job.
* Phase 6's deck-generator execution could not be fully validated: `pptxgenjs` could not be installed (npm registry restricted to an internal feed), so only `node --check` (syntax validation) was run, not an actual PPTX build. Markdown lint was skipped again for the same reason as Phase 1.
* Phase 7 paired EN/FR content inline per golden-dataset record (a description.en-CA/description.fr-CA pair) rather than as two separate language files, mirroring how the Phase 2 fixtures already pair notice/expectedDisplay fields. eval/tests/__init__.py was removed after being found to break combined multi-directory pytest collection (bare `tests` package name collision across apps/workshop, mcp/*, src/quote-preparation-agent, and eval).
* Phase 8 carried over two non-blocking BCP318 nullable-warning lint messages in mcp-container-apps.bicep/main.bicep verbatim from the sibling reference module (safe: the flagged block only evaluates when the guarding condition is true). No deploy/provision/apply command was run; only `az bicep build` (offline compile) was used for validation.
* Phase 9 confirmed the runtime applicant-facing notice text (sourced from data/synthetic/rulebook.json's `notice` field, surfaced via src/quote-preparation-agent/graph.py) conveys the same non-binding/training-only boundary as the docs disclaimer but is not byte-identical wording ("Training simulation only. Not an insurance quote. No delivery." vs. the longer docs disclaimer sentence). Flagged as a follow-up content-review item (see Planning Log), not a blocking defect — all 24 learner-facing Markdown files carry the full disclaimer verbatim.
* Markdown lint was skipped in every phase that authored Markdown (1, 6, 9): `npx markdownlint-cli2` fails with `EALLOWREMOTE` in this sandbox (npm registry restricted to an internal feed, no local devDependency installed). Recommended as a follow-up in an environment with full registry access.

## Release Summary

**Total phases completed: 9 of 9.** All plan checkboxes (Phases 1-9 and every step within them) are marked `[x]` in the implementation plan. The full offline vertical slice — synthetic fixtures, JSON Schema, deterministic calculator, SQLite-backed approval state machine, two read-only MCP services, a local (unhosted) LangGraph quote-preparation agent, a ten-lab bilingual (EN/FR) curriculum with a shared deck generator, a deterministic evaluation suite, and author-only/undeployed Bicep infrastructure scaffolding — was built and validated with no live Azure dependency and no deploy/provision/apply command ever executed.

**Files created: ~80** across `data/synthetic/` (schema, rulebook, 5 fixtures), `apps/workshop/` (calculator, approval repository, tests), `mcp/application-server/` and `mcp/rulebook-server/` (FastMCP services, tests), `src/quote-preparation-agent/` (LangGraph state/toolbox/graph/main, tests), `docs/labs/` and `docs/fr/labs/` (10 EN + 10 FR labs + 2 indexes), `scripts/build-workshop-deck.js` + `package.json`, `eval/` (golden dataset, checks, evaluation gate, tests), and `infra/` (4 Bicep modules, main.bicep/parameters, README, azure.yaml).

**Files modified: 1** (README.md, expanded from a placeholder). **Files removed: 6** (`.gitkeep` placeholders in directories later populated with real content).

**Test results (final Phase 9 sweep):** `pytest apps/workshop mcp src/quote-preparation-agent eval -q` → **49 passed**, 0 failed. `az bicep build` → **5/5 files compiled** (2 non-blocking carried-over warnings in mcp-container-apps.bicep/main.bicep). `python eval/evaluation_gate.py` → **12/12 golden-dataset records passed**, bilingual_parity=PASS. Disclaimer sweep → **24/24 learner-facing Markdown files** carry the required synthetic-only/non-binding/no-regulatory-endorsement disclosure in the correct language.

**Deployment/infrastructure notes:** No Azure resource was created, modified, or deployed at any point. Bicep modules and `azure.yaml` are author-only and explicitly gated behind G2 (platform/security), G3 (reproducible compatibility), and G6 (regulatory/privacy sign-off); model name/version/SKU are left as placeholders pending G2.

**Known non-blocking gaps** (see Planning Log for full detail and priority): markdown lint could not run in this sandbox (registry-restricted); the deck generator's PPTX output is syntax-checked but not actually built (pptxgenjs could not be installed); runtime applicant notice wording is equivalent-but-not-identical to the docs disclaimer wording; Gates G1-G6 remain open and are explicitly out of scope for this authoring effort.


