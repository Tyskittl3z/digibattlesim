# Permanent Codex instructions — Digimon Battle Simulator

## Project purpose — NON-NEGOTIABLE
This repository is a **simulation and numerical-results tool**, not a deck-building assistant.
User owns all deck construction, interpretation, and decisions; offer **no card/slot recommendations** and no speculative conclusions. User-requested numerical deck comparisons are allowed. Do not alter decklists without explicit user instruction.

## Scope and isolation
- User request (2026-10-29): add a drag-and-drop browser app for **both** side-by-side deck contents/statistics and head-to-head simulation. Decklist intake/numerical comparison may accept user-supplied lists. This explicitly authorizes the comparison interface; simulation support remains limited to verified mechanics of the selected matchup. Unknown cards/unsupported pairings must remain explicit; never manufacture win rates or reuse another matchup's results. Save exact inputs, hashes, statistics, data gaps, simulation status and actual results/log references in a downloadable after-report.
- **Current simulator gameplay scope**: `DECKS/JUPITERMON.txt` (A) vs `DECKS/AMATERASUMON_TOHO.txt` (B). Browser import/statistics for another pairing do not certify its gameplay support.
- NEW DECK = FRESH START. For any new deck or changed matchup, invalidate all deck-specific roadmaps, training data, pilot weights, and matchup results. Reuse only rules, generic match infrastructure, and verified generic mechanics. Do not seed a new match with another deck's data.
- Never expand toward universal Digimon card support or unsolicited feature work. Work on interactions that the **loaded two decks can actually produce**, as found during gameplay.

## Authority and integrity
- Official Digimon card text, comprehensive rules and official card Q&A/rulings are the hard authority for legality and effect resolution. A judge validates each encountered interaction. Never guess card effects, costs, timings, targets, replacements or player choices.
- Mark unsupported, ambiguous, or unverified mandatory interactions as **HALT** with precise card, effect, state, seed and reproducible trace. Do not silently skip them, manufacture outcomes, or treat an automatic decline of an optional effect as learned skill.
- Keep an explicit distinction between: `SOFTWARE_COMPLETED`, `JUDGE_CERTIFIED`, `HALT`, and `EXPERIMENTAL`. Code tests and deterministic replay alone do not certify rules.
- No actions after game end; validate memory bounds, zone/card conservation, security timing, trigger/Counter windows, and once-per-turn state.
- Pin the selected format/region, language, rules editions, errata, restrictions, effective dates and official source hashes in `RULES/RULES_LOCK.json`. Missing pins remain UNVERIFIED and block final eligibility.
- Separate software integrity, judge-verified legality and strategic effectiveness. A rules judge does not approve strategy colors; strategy review cannot establish legality. See `WORKFLOW.md` for the evidence contracts.

## Fixed workflow
1. Load and lock the two exact decklists; validate 50 main cards + Digi-Eggs as listed and applicable restrictions.
2. Run **at least 60 complete, turn-by-turn bot-vs-bot fact-finding MATCHES**: at least 30 starts per deck, with equal starting-player counts. Sixty is a minimum evidence cohort, not an automatic readiness certificate. Opening probes, partial turns and targeted scenarios count as zero full matches.
3. During those matches discover only in-scope combinations, decision alternatives, interactions, and opponent responses. Judge verifies rules evidence. Fix in-scope defects and rerun affected matches / entire evidence cohort when the engine changes.
4. Close encountered interaction/choice coverage using explicit branch inventories and targeted scenarios where needed; record evidence in `RULES/INTERACTION_COVERAGE.json`. Then save **matchup-specific** situational GREEN / YELLOW / RED lane roadmaps under the preregistered `ROADMAPS/APPROVAL_CRITERIA.json`: objective conditions, evaluated legal alternatives, trace provenance, metric/objective and uncertainty are required. UNKNOWN / UNVERIFIED remain separate; strategically RED is distinct from judge-confirmed ILLEGAL. A rules review or one winning outcome cannot approve a lane.
5. Freeze decks, rules snapshot, both pilots, and both roadmaps with hashes. No learning or exploration in the final evaluation.
6. Run **10,000 ACTUALLY PLAYED turn-by-turn matches**, 5,000 starts per deck, as fast as possible without simplifying effects, inventing outcomes, or violating legality. Stream compressed per-match transcripts, seeds, actions, decisions, interactions and end states. Checkpoint and resume safely.
   Preserve every HALT's original seed and trace; never replace a halted match with a new seed. Infrastructure interruption can replay the original match under identical frozen inputs. Unresolved rules HALTs block continuation. Any change to frozen engine, rules/format, decks, pilots, criteria or roadmaps invalidates all final results and requires a new freeze and full evaluation restart.
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
