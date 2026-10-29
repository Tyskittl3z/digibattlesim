# Digimon Battle Simulator — Codex handoff

## Use the drag-and-drop app

Open **[APP/DeckCompare.html](APP/DeckCompare.html)** in your browser. Drop two text
decklists (or paste them) to compare quantities and available card statistics.
Click **Save after-report** to keep the exact inputs, hashes, all statistics,
missing data and simulation status. No installation or server is required.

The app has Digimon TCG-inspired styling. **Head-to-head simulation remains
unavailable** until the underlying gameplay verification passes. The frozen
runner/checkpoint/final-audit software is implemented, but correctly refuses the
current blocked evidence and has played 0/10,000 final matches.
The bundled card metadata covers the supplied 41 cards; other IDs are retained with
explicit missing-data notices. See `APP/README.md` for supported input formats.

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
