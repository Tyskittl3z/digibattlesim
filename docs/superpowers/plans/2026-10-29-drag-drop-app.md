# Drag-and-drop comparison app implementation plan

> **For agentic workers:** Execute inline with superpowers:executing-plans and TDD. User requested autonomous work, chose Both (statistics and head-to-head) and explicitly requested important information in the after-report. No extra approval pause.

**Goal:** Deliver an immediately openable browser app for importing two decklists, inspecting numerical differences and saving exact evidence, with truthful head-to-head readiness and no fabricated simulation results.

**Architecture:** Plain browser HTML/CSS/JS, built into one offline HTML file. Pure shared JavaScript handles parsing/statistics/reporting; Node's built-in tests exercise it. A Python standard-library builder embeds only supplied card metadata, sample inputs and source hashes. The current simulator cannot produce verified head-to-head win rates; its panel must clearly remain unavailable, with no pretend results or fake run controls. The actual verified simulation runner remains blocked work, not claimed delivered by this interface.

**Tech Stack:** Browser File API/Web Crypto, vanilla JS, Node test runner, Python standard library; no runtime install or server for the delivered HTML.

**Spec:** Latest user request: drag/drop decklists, Both comparison types, save important information for the after-report. AGENTS.md's integrity, no-deck-advice and new-matchup-isolation boundaries remain in force.

## Constraints / review focus

- Accept DigimonCard.io-style quantity/name/card-code text and common code/quantity variants. Reject ambiguous/broken rows visibly; do not silently omit them.
- Arbitrary user lists may be compared numerically. Unknown card IDs keep exact counts/names and explicit missing metadata; never infer effects, eggs or costs from guesses.
- No data leaves the browser; no external assets or calls. Render uploaded text with textContent, never HTML.
- New inputs recompute everything; old match results never become a new matchup's results. Simulated wins/losses/rates remain null and matches played0 until a real verified runner exists.
- After-report JSON must preserve original texts/filenames, canonical composition and raw hashes, validation issues, full unfiltered statistics/differences, dataset provenance, current simulation blockers and actual result/log fields (empty/unavailable now).

### Task 1: Tested deck comparison and report core

**Files:** `APP/compare.js`, `APP/tests/compare.test.cjs`.
- [x] Write failing tests for both supplied54-card lists, duplicate aggregation, common text variants, invalid lines, unknown metadata and report honesty/retained exact inputs.
- [x] Implement parser, summaries, weighted overlap/differences, pairing readiness and async report export with SHA-256.
- [x] Run Node tests; no dependencies in production.

### Task 2: Offline usable interface

**Files:** `APP/template.html`, `APP/style.css`, `APP/ui.js`, `APP/build.py`, generated `APP/DeckCompare.html`.
- [x] Build two accessible drop/paste panels with examples, swap/clear, automatic comparison, searchable differences, composition bars and report download.
- [x] Include a separate honest head-to-head panel showing unsupported/unverified status without a win-rate guess.
- [x] Build a single file, exercise drag/drop, paste, malformed input, unknown cards, report download and mobile layout using available browser/DOM tools.

### Task 3: Review and delivery

- [x] Run code review and relevant regressions plus existing128 Python tests. Preserve decks/engine unchanged.
- [x] Update README/STATUS, record verified capabilities and remaining simulation blocker; refresh checksums and deliver HTML directly plus project archive at completion.

## Execution record

- User chose Both and requested important information retained in after-report, then Digimon TCG visual theme. Interface scoped to general numerical intake; actual gameplay remains verified-matchup-only, no universal engine or deck advice.
- Core tests initially failed against missing parser/report behavior, then passed. Readable HTML report escaping/embedded complete JSON regression failed before implementation and passed afterward.
- Code review found conflicting quantity/code suffix interpretation and BOM byte loss. Focused tests reproduced and fixes reject ambiguous rows, decode strict UTF-8 preserving BOM, and save original byte hashes. Additional browser regression exposed textarea CRLF normalization; original text now retained separately until editing. Canonical composition uses locale-independent ID order.
- Browser/build checks exposed an inline script-end-tag packaging error; builder escapes embedded script-end text and executable-script checks passed. Browser file chooser recursion guarded.
- Theme: blue/orange frames, digital playmat, inline vector icons; responsive and keyboard accessible. No external assets/requests. Installed Chromium used via elevated process permissions and internal loopback server; direct file navigation blocked by managed browser policy. No policy was modified.
- Verification: 9 Node core tests, 1 inline-build test, 6 real Chromium interaction/download/mobile tests, existing128 engine tests all passed. Engine/deck files unchanged, no new played simulation or certification claimed.
- Full user Both goal remains partially blocked: statistics, intake, reports and visual interface ready; actual head-to-head results still require engine/rules/pilot/freeze work. Report state stays matches0 and null wins/losses/rates, no previous results reused. See APP/README.md and REPORTS/APP_VERIFICATION_2026-10-29.md.
