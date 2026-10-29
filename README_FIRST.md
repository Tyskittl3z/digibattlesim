# Read first — Jupitermon vs Amaterasumon/Toho source-scoped attack audit

This ZIP supersedes the previous experimental decision build as a SOFTWARE audit, NOT as a judge-certified matchup simulator.
It contains ONLY these two loaded decks, fresh runs, source code, and audit reports.
No deck substitutions, previous matchup roadmaps, or other deck-specific code training artifacts were imported.

Run from SOURCE:

```bash
python -m unittest discover -p 'test_*.py' -q
python -m matchup_v12_attack_sources
```

The cohort runner performs 60 seeds (30 first-player starts each). Five currently halt on unresolved Susanoomon target replacement/Decode interactions; they cannot be counted as completed games.
The full 10,000-match evaluation remains blocked until all loaded interactions and strategy lanes meet judge review.
See REPORTS/RESULTS.md and REPORTS/RESULTS.json.
