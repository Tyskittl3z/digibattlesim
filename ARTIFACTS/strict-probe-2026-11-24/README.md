# Strict v4.4 diagnostic probe

This is one software probe, **not** a member of the requested new 60-game
fact-finding cohort. It uses the styled Bot A/B policies, cohort index 0,
original seed `8204123595783142766`, and English-version worldwide context
`79ad61d1d63442f6485318823e643605181321c605d1548760ba633a3e104d78`.
The context pins Bandai's November 20, 2026 Comprehensive Rules Manual v4.4
by SHA-256. The card-page snapshots still need freshness and rules review.

`game-0000-before-route.json` halted at EX13-019's printed digivolution
route. It exactly replayed under its recorded source version before the route
checker edit. `game-0000-after-route.json` uses the new checker, retains the
same seed, choices, and first eight successful state transitions, and exactly
replays under the current source version. Its original failed selection was
retried with the same command arguments, view, choices, and policy RNG. It now
halts before playing B's EX13-017 because a strict play/effect checker is not
installed. `prefix-comparison.json` records these comparisons and the one
changed source hash.

The comparison is diagnostic evidence, not a formal source-only migration or
independent official rules certification. Both records have zero fact-finding
and final-evaluation credit. The new cohort and 10,000-game evaluation have
not started.
