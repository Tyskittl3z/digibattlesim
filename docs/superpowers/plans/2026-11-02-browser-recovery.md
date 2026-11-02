# Browser Recovery Implementation Plan

> **For agentic workers:** use superpowers:executing-plans inline; user authorized the reconstruction.

**Goal:** Reconstruct the missing browser/catalog PWA and provide a durable verified archive.
**Architecture:** Extend the existing comparison core; deterministic official catalog chunks; hash-bound evidence; one transactional storage adapter; static PWA shell.
**Tech Stack:** Python standard library, plain JavaScript, IndexedDB, Chromium/Playwright.
**Spec:** docs/superpowers/specs/2026-11-02-browser-recovery-design.md

## Global Constraints
No engine/evaluation/deck edits, invented results, certification or recommendations. Official source hashes required. Report actual rebuilt counts. Preserve exact text and file-byte hashes.

## Review Focus
Malformed/non-deck codes; catalog conflicts; date/format restrictions; concurrent stale saves; transaction aborts; offline cold chunk loading; async input races; uploaded HTML.

### Task 1: Official catalog
Files: TOOLS/catalog/{parse_official,build_catalog,verify_catalog}.py and tests; APP/catalog/{manifest,chunks}.
- [x] Test fixtures: base vs alternate, missing numeric fields, duplicate conflicts, deterministic chunks.
- [x] Implement standard-library official HTML parser and reproducible source-pinned build.
- [x] Fetch all advertised official categories with bounded retries, retain hashes, verify all records/chunks.

### Task 2: General deck evidence
Files: APP/core/{catalog,legality,identity}.js, APP/compare.js, APP/tests/general-decks.test.cjs.
- [x] Test unknown codes, quantity/restriction/pair failures, seat/dependency identity changes and generic bot labels.
- [x] Implement conservative legality, explicit support locks and report provenance; keep legacy behavior compatible.

### Task 3: Transactional storage
Files: APP/storage/{db,workspaces}.js; Node/Chromium storage tests.
- [x] Test immutability, conflicts, archive, restore, abort and quota refusal.
- [x] Implement promise-based IndexedDB adapter with atomic report/workspace commits.

### Task 4: PWA shell
Files: APP/index.html, APP/shell/{app,style}.js/css, APP/manifest.webmanifest, APP/service-worker.js.
- [x] Test real import/report/restore, offline missing-prefix imports, mobile/keyboard and stale operations.
- [x] Implement vivid browser shell with demand-loaded catalog, comparison, legality, workspaces, catalog browser and locked evidence stages.
- [x] Verify install/offline caching and error reporting without runtime third-party requests.

### Task 5: Release
Files: APP/README.md, release verifier/launcher, recovery report, downloadable project archive.
- [x] Run complete app/catalog/engine checks; inspect desktop/mobile screenshots; review changes and fix defects.
- [x] Commit reconstruction, package source/history and app, verify archive, deliver download with clear simulation limits.

Completion evidence: REPORTS/BROWSER_RECOVERY_2026-11-02.md. Final branch retained separately; source/history packaged for recovery.
