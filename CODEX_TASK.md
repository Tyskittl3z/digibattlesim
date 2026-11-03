# First Codex task (execute, don't just plan)

> **Latest live continuation:** Gameplay-first. **446 tests pass**. Game0000
> reaches turn6 /83commands, same original seed and choices, exact replay.
> Continue selected RESOLVE_PENDING effect21, BT22-023 EndYourTurn unsuspend
> targeting B:EX13-022#3 at Bmemory−3, from
> `ARTIFACTS/gameplay-continuations-2026-11-03-05/game-0000-segment.json.gz`.
> Replace the broad orientation guard with actual-event filtering and execute
> B BT11Rina memory +two EX13Rina self-suspend/Draw/After evolution reactions.
> Preserve post-Draw choices, individual−2 discounts and pending-end timing.
> Still zero full valid matches; prefixes do not count toward60.

> **2026-11-02 current priority:** User delegated choosing the best starting
> matchup. Use the distinct-list Ulforce mirror 123129 vs122110, not the original
> pair's default CLI argument. Read `PYTHON_DEVELOPER_HANDOFF.md`, latest STATUS,
> and `REPORTS/ULFORCE_BOOTSTRAP_PROGRESS_2026-11-02.md`. Latest source passes335
> tests. New diagnostic version02 records60 original context-bound seeds with
>30 starts each and60 exact replays; all60 HALT, zero valid full-match credit.
> Finish the encountered real effects and inspect overbroad scope guards;
> retain all evidence and the original randomized queue.

> **2026-11-01 live continuation:** Read the latest STATUS section and
> `REPORTS/EX13_LIVE_ENGINE_PROGRESS_2026-11-01.md`. The selected engine now has
> 307 passing tests and actual balanced diagnostic attempts; both60-attempt
> versions halted and provide zero accepted-match credit. Continue from their
> preserved seeds and exact blockers; do not restart the project or reinterpret
> the diagnostic cohort as the completed fact-finding requirement.

> **2026-10-30 continuation:** The user expanded this engine track to selected,
> randomized exact pairs from `DigiLab_EX13_Top_Decklists_Deduplicated.xlsx` and
> chose English-version worldwide rules. The old two-deck-only restriction below
> is historical and superseded for this authorized track; all integrity,
> no-advice, source-evidence, fresh-matchup and freeze requirements remain.
> Read `REPORTS/EX13_ENGINE_PROGRESS_2026-10-30.md` before continuing. The current
> explicit-context foundation has 193 passing tests but no full-game simulator
> support or valid matches for the first imported pairing. Continue implementing
> its remaining scoped mechanics and full gameplay, then the 60/roadmap/10,000
> gates. The other chat owns catalog/import/comparison/storage/browser work.

## Goal
Bring the **Jupitermon (A) vs Amaterasumon/Toho (B)** two-deck simulator to at least 60 **fully completed, judge-verified** fact-finding games with balanced starts, then evidence-backed GREEN/YELLOW/RED roadmap readiness. Sixty is the minimum, not proof that all encountered branches were covered. Keep the 10,000-match final evaluation as a later gate. Apply the accepted verification adjustments in `WORKFLOW.md`.

## Immediate steps
1. Reproduce the baseline: run `python -m unittest discover -p 'test_*.py' -q` from `SOURCE/`; identify source hashes and preserve previous reports as versioned artifacts.
2. Reproduce the five EX12-076 Susanoomon HALT cases from `MATCH_LOGS/` or the 60-seed runner. Extract their exact states. Determine official interaction/timing for Decode and leave-the-battle-area protection/replacement from the **loaded** cards only.
3. Implement the required controller choice(s) and exact resolution, with judge citations and targeted tests. Do not conflate a Digimon being moved, a replacement effect, and Decode; resolve in official order.
4. Audit other unmodeled *encountered* optional attacking effects; evaluate legal activate/decline branches rather than forced declines. No unsupported effect may be silently treated as resolved.
5. Pin the rules/format snapshot, then rerun a minimum of 60 complete games (at least 30 starts per deck, equal counts) and verify replay, zones, timing, and ending. Close encountered branch gaps with targeted scenarios; scenarios count as zero full games. If a new halt occurs, solve its loaded-deck rule and rerun. Preserve raw records with engine/rules/criteria hashes.
6. Construct situational three-lane roadmaps under preregistered approval criteria. Separate rules-legality review from strategy-effectiveness review. Require evaluated legal alternatives, metric/objective, multiple independent-seed traces and uncertainty; report unknowns without inventing positive lanes.
7. Only after verified gameplay and frozen pilots may you implement/run the 10,000 real turn-by-turn evaluation; keep learning disabled during the final run.

## Completion gates
- At least 60 **full** legally resolved, judge-reviewed training matches, at least 30 starts per deck with equal counts, plus reviewed coverage of encountered interaction alternatives and zero unresolved mandatory effects.
- No hidden substitutions, skipped active effects, invented rules, or unverified end states.
- Persistent green/yellow/red classifications conditioned on objective board state and traceable evidence; UNKNOWN allowed.
- Comprehensive numerical report and raw compressed match logs.
- Final 10,000 results only if freeze/eligibility gates actually pass; otherwise report exact blockers.
- Preserve every final HALT's seed and trace. No replacement seeds; identical-freeze infrastructure retries replay the original match. Any frozen gameplay/input change requires a new freeze and full final restart, never a mixture of versions.

## Hard restriction
NO deck advice. NO previous deck matchups. NO universal card engine. NO claimed certification based solely on a test-count or a replay-count.
