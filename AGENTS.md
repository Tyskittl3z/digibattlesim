# Permanent Codex instructions — Digimon Battle Simulator

## Project purpose — NON-NEGOTIABLE
This repository is a **simulation and numerical-results tool**, not a deck-building assistant.
User owns all deck construction, interpretation, and decisions; offer **no card/slot recommendations**, no deck-version comparisons, and no speculative conclusions. Do not alter decklists without explicit user instruction.

## Scope and isolation
- **Loaded decks only**: `DECKS/JUPITERMON.txt` (A) vs `DECKS/AMATERASUMON_TOHO.txt` (B).
- NEW DECK = FRESH START. For any new deck or changed matchup, invalidate all deck-specific roadmaps, training data, pilot weights, and matchup results. Reuse only rules, generic match infrastructure, and verified generic mechanics. Do not seed a new match with another deck's data.
- Never expand toward universal Digimon card support or unsolicited feature work. Work on interactions that the **loaded two decks can actually produce**, as found during gameplay.

## Authority and integrity
- Official Digimon card text, comprehensive rules and official card Q&A/rulings are the hard authority for legality and effect resolution. A judge validates each encountered interaction. Never guess card effects, costs, timings, targets, replacements or player choices.
- Mark unsupported, ambiguous, or unverified mandatory interactions as **HALT** with precise card, effect, state, seed and reproducible trace. Do not silently skip them, manufacture outcomes, or treat an automatic decline of an optional effect as learned skill.
- Keep an explicit distinction between: `SOFTWARE_COMPLETED`, `JUDGE_CERTIFIED`, `HALT`, and `EXPERIMENTAL`. Code tests and deterministic replay alone do not certify rules.
- No actions after game end; validate memory bounds, zone/card conservation, security timing, trigger/Counter windows, and once-per-turn state.

## Fixed workflow
1. Load and lock the two exact decklists; validate 50 main cards + Digi-Eggs as listed and applicable restrictions.
2. Run **60 complete, turn-by-turn bot-vs-bot fact-finding MATCHES**: 30 A-first, 30 B-first. Opening probes or partial turns count as zero matches.
3. During those matches discover only in-scope combinations, decision alternatives, interactions, and opponent responses. Judge verifies rules evidence. Fix in-scope defects and rerun affected matches / entire evidence cohort when the engine changes.
4. Save **matchup-specific** situational GREEN / YELLOW / RED lane roadmaps, including conditions, evidence, and provenance. UNKNOWN / UNVERIFIED must remain separate until evidence supports a lane; distinguish strategically RED from judge-confirmed ILLEGAL. Do not arbitrarily promote a lane based on one outcome.
5. Freeze decks, rules snapshot, both pilots, and both roadmaps with hashes. No learning or exploration in the final evaluation.
6. Run **10,000 ACTUALLY PLAYED turn-by-turn matches**, 5,000 starts per deck, as fast as possible without simplifying effects, inventing outcomes, or violating legality. Stream compressed per-match transcripts, seeds, actions, decisions, interactions and end states. Checkpoint and resume safely.
7. Deliver numerical results only: W/L, rate, first-player split, turn distributions, card play frequency, combo frequency, lane evidence, halts and rule-check status. Do not interpret the numbers as a deck-building recommendation.

## Current snapshot (2026-10-19)
- This is the *latest supplied code snapshot*, not a claim of a fully finished simulator.
- Latest 60 attempt cohort: 55 software-completed, 5 judge halts, 0 independently judge-certified; 0 approved strategy lanes, 0/10,000 final matches.
- Five halts arise from **EX12-076 Susanoomon** targeting opponent stacks involving **Decode P-213, BT26-029, BT24-101**, or leave-the-battle-area replacement/prevention effects.
- There are also top-level optional attacking effects recorded as unmodeled declines; no permission to regard them as correct training decisions.
- Historical match logs in `MATCH_LOGS/` are diagnostic evidence from this version, not certified training or final evaluation output.
- Do not import older deck-specific source builds to resolve these halts.

## Development practices
- Before changing rules, identify the exact official card text/ruling and add a focused regression test for that case.
- Keep changes minimal and load-deck-scoped, with deterministic seeds and explicit judge audit entries.
- Run from `SOURCE/`: `python -m unittest discover -p 'test_*.py' -q`.
- Work autonomously, proceed through blockers and tests without repeated permission requests; ask only for genuinely required user decisions.
- Report actual tool-executed pass/fail and match counts, never projected figures.
- Read `CODEX_TASK.md` and `STATUS.md` before editing.
