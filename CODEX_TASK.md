# First Codex task (execute, don't just plan)

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
