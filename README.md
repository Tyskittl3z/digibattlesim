# Digimon Battle Simulator — Codex handoff

## Use the current app

Open **[APP/DigiBattle-DeckLab.html](APP/DigiBattle-DeckLab.html)** after downloading
it, or extract the [project backup](BACKUPS/DigiBattle-Rebuilt-2026-11-02.zip) and
open that file from `APP/`. It includes the full **4,481-record official English
catalog**, numerical deck comparison, construction checks, saved workspaces and
exact-input reports. See [APP/README.md](APP/README.md) for the installable offline
PWA launcher and browser storage details.

The app now exports **simulation preparation requests** validated independently
by the Python engine bridge. **Match evidence** shows actual readiness blockers
for the matching loaded decks and keeps stale diagnostics separate from reviewed
valid matches. No battles are started by exporting a request. Head-to-head win rates
remain unavailable until the gameplay/evidence workflow is completed.

```sh
python TOOLS/engine/request.py path/to/export.battle-request.json
python TOOLS/verify_project.py
```

Read [docs/ENGINE_HANDOFF.md](docs/ENGINE_HANDOFF.md) for the versioned browser/engine
contract and exact remaining mechanics work. GitHub Actions runs the same software
checks. Passing tests never substitutes for rules certification.

This is the **current Jupitermon vs Amaterasumon/Toho simulator** transferred for software development with Codex. It is not a universal rules engine or a deck-building advisor.

**READ FIRST:** `AGENTS.md` (immutable project boundaries), `STATUS.md` (verified current state), `CODEX_TASK.md` (the exact next work).

The user-approved verification adjustments are in `WORKFLOW.md`: pinned official
rules/format, a minimum balanced 60-match cohort plus branch coverage, separate
legality/strategy reviews, preregistered lane criteria and strict HALT/restart
policy. Missing official evidence remains UNVERIFIED; no lane or result is
approved by adopting these requirements.

## Current continuation (2026-10-29)

Use the strict evidence runner from `SOURCE/`:

```bash
python -m unittest discover -p 'test_*.py' -q
python -m match_evidence --out ../ARTIFACTS/current-NEW-UNIQUE-VERSION --count 60
python -m evaluation_gate --cohort ../ARTIFACTS/current-NEW-UNIQUE-VERSION
```

The gate currently exits **2 / BLOCKED**. See `REPORTS/WORKFLOW_ADJUSTMENTS_2026-10-29.md`
and `RULES/REVIEW_REQUIRED.md` for evidence and remaining work. No final matches
or strategic lanes are certified. `ROADMAPS/` contains UNKNOWN-only candidates;
`EVALUATION/` contains an unplayed seed schedule, not a freeze.

The historical runners below remain unchanged for reproduction. Their internal
`VALID_COMPLETE_GAME` label means software completion only. A stricter reaudit
found invalid physical states in 11 of the original 55 software completions;
these must not be counted as valid fact-finding matches.

## File layout
- `SOURCE/`: runnable Python matchup engine, card manifests, cost data and unit tests.
- `DECKS/`: exact two decklists — never edit without user permission.
- `MATCH_LOGS/`: 60 prior compressed attempts, including five HALTs; legacy audit data from this source version.
- `REPORTS/`: prior audit outcomes and halt descriptions.
- `README_FIRST.md`: original archive readme, preserved.
- `CODEX_TASK.md`: initial Codex work item.

## Verify code in this package
Requires Python 3.11+; standard library for bundled tests.

From project root:
```powershell
cd SOURCE
python -m unittest discover -p 'test_*.py' -q
```

Historical baseline runner (experimental; writes its own cohort output from `SOURCE/`):
```powershell
python -m matchup_v12_attack_sources
```

The existing batch runner **will report HALTs** for incomplete Susanoomon interactions. These are expected baseline defects. Do not interpret the winner counts as judge-certified.

## Open in Codex (desktop)
1. Unzip this folder onto your computer.
2. Open Codex from the ChatGPT desktop app, then open this folder as the working project.
3. Begin: `Read AGENTS.md, STATUS.md, and CODEX_TASK.md. Execute CODEX_TASK.md, running tests and maintaining evidence logs. Do not ask me for permission between steps unless genuinely required.`

Codex CLI alternative: install/sign in to Codex CLI, open this folder in a terminal, and run `codex`.

## Report contract
Results and user-requested comparisons are numerical, with explicit rule-check
and missing-data status. No card swaps or unsolicited strategy recommendations.
