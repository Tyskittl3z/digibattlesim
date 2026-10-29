# First Codex task (execute, don't just plan)

## Goal
Bring the **Jupitermon (A) vs Amaterasumon/Toho (B)** two-deck simulator to 60 **fully completed, judge-verified** fact-finding games, then evidence-backed GREEN/YELLOW/RED roadmap readiness. Keep the 10,000-match final evaluation as a later gate.

## Immediate steps
1. Reproduce the baseline: run `python -m unittest discover -p 'test_*.py' -q` from `SOURCE/`; identify source hashes and preserve previous reports as versioned artifacts.
2. Reproduce the five EX12-076 Susanoomon HALT cases from `MATCH_LOGS/` or the 60-seed runner. Extract their exact states. Determine official interaction/timing for Decode and leave-the-battle-area protection/replacement from the **loaded** cards only.
3. Implement the required controller choice(s) and exact resolution, with judge citations and targeted tests. Do not conflate a Digimon being moved, a replacement effect, and Decode; resolve in official order.
4. Audit other unmodeled *encountered* optional attacking effects; evaluate legal activate/decline branches rather than forced declines. No unsupported effect may be silently treated as resolved.
5. Rerun 60 complete games, 30 starts per deck, and verify replay, zones, timing, and ending. If a new halt occurs, solve its loaded-deck rule and rerun. Preserve raw records with engine/rules hashes.
6. Construct situational three-lane roadmaps and report approved vs unknown entries with supporting judge/evaluation evidence; do not invent a positive lane when the evidence is insufficient.
7. Only after verified gameplay and frozen pilots may you implement/run the 10,000 real turn-by-turn evaluation; keep learning disabled during the final run.

## Completion gates
- 60 **full** legally resolved, judge-reviewed training matches with 30/30 starting-player balance and zero unresolved mandatory effects.
- No hidden substitutions, skipped active effects, invented rules, or unverified end states.
- Persistent green/yellow/red classifications conditioned on objective board state and traceable evidence; UNKNOWN allowed.
- Comprehensive numerical report and raw compressed match logs.
- Final 10,000 results only if freeze/eligibility gates actually pass; otherwise report exact blockers.

## Hard restriction
NO deck advice. NO previous deck matchups. NO universal card engine. NO claimed certification based solely on a test-count or a replay-count.
