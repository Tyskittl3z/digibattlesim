# Digimon Battle Simulator — Codex handoff

This is the **current Jupitermon vs Amaterasumon/Toho simulator** transferred for software development with Codex. It is not a universal rules engine or a deck-building advisor.

**READ FIRST:** `AGENTS.md` (immutable project boundaries), `STATUS.md` (verified current state), `CODEX_TASK.md` (the exact next work).

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

Current batch runner (experimental; writes its own cohort output from `SOURCE/`):
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
Results are raw numbers and rule-check status only. No card swaps, no unsolicited strategy recommendations, no deck-version comparisons.
