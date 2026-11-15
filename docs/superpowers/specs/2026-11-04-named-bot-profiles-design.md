# Named aggressive and defensive bots

The user identified the intended players as project Bot A and Bot B, one
aggressive and one defensive. Assign A aggressive and B defensive, as stated in
commentary. Earlier instructions delegate implementation choices and ask for
autonomous execution. Keep the current exact decks, seed and saved history.

Legacy Bot A/B share a scorer and have no separate style configuration. Create
fresh, untrained, transparent profiles for this context. Do not import old
matchup weights, routes, roadmap data or outcomes. Reuse current candidate and
transactional command helpers; leave the historical random runner unchanged.

A favors winning attacks, security pressure and ready attacking bodies. B favors
winning attacks, visible threat removal, ready Blockers, reactive Tamers and
resource preservation. For own unsuspend choices B prioritizes suspended
Blockers, then reactive Tamers with All Turns text, then other Digimon. A favors
suspended Digimon before Tamers. These are declared heuristic preferences,
not empirical play ratings or claims of optimal strategy. Both consider only
their own public view/hand, explicit choice reveals and printed definitions.
Stable deterministic tie breaks use no game RNG. Unknown choice schemas stop
explicitly; never choose a fallback because a handler is missing.

Use a separate bounded named-bot continuation. Revalidate all successful saved
commands/views/results and the entire physical state/RNG before the new segment.
Preserve old command dictionaries and historical policy manifests. Bind new
profiles to context, style, source/configuration hashes, and record each new
choice with its bot identity and rationale. Persist any selected failed action
without rerolling. Exact replay reproduces the full mixed-history checkpoint.

The current game is an engineering continuation: its random prefix prevents
crediting its whole outcome to these bots. All whole-match, fact-finding and
final credit stays zero. No cohorts, route preloading or strategic ratings.
Run only the next bounded segment, preserving any real implementation gap.

Alternatives: reusing legacy deck heuristics would transfer unrelated strategy;
renaming random policies would not implement the requested styles. Fresh profiles
using the existing engine boundary fit the supplied constraints. Python standard
library only, within the existing isolated engine worktree.
