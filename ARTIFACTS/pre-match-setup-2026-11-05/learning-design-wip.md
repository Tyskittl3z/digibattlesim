# Interaction learning WIP handoff — paused before implementation

The user said to pause before starting the match. No source/test/criteria files
were created by this worker; no actual game, opening/deal, tests or cohort ran.
The following is saved design work, not implemented behavior or a passing claim.

## User-defined objective and accepted initial criterion

User chose actual observed board/tempo impact, not winning probabilities:
removed/incapacitated opposing cards, completed successful Security checks,
battle-area development with low memory expense, opposing body count and stack
size. Green=positive, Yellow=near-zero/mixed neutral, Red=negative under explicit
heuristic arithmetic. Failed/unresolved commands are UNRATED, not red/illegal.
Judge legality and approved roadmap evidence remain separate.

Proposed initial weights accepted by root before the pause:
- remaining Security count difference: 2 per card;
- completed successful Security checks: 2 per check;
- battle units: 2 per unit;
- digivolution/source cards: 0.5 each;
- printed level: 0.25 per level;
- printed DP: 0.1 per 1000 DP;
- ready card: 0.5;
- ready Blocker: an additional 1;
- hand-card difference: 0.5 per card;
- breeding development: 0.5 base (exact level treatment still to settle);
- memory expense: subtract 0.5 per memory;
- neutral threshold: absolute reward <=0.25.

All components must be inspectable, with criterion source/hash before play.
Do not call a material sigmoid a winning probability, or call these colors
empirically approved strategy. Exact incapacitation/status weighting, terminal
outcome handling and breeding contribution still need implementation decisions.

Use public before/after views and stable entity IDs to avoid counting normal
reanchoring/evolution as removing and recreating a whole body. Opponent breadth
and total source depth must be explicit. Don't separately reward draws if hand
change already captures them. Log successful-check count and Security-count
change separately with the defined weights.

Read actual cost from PAY_* result steps first, then direct result.cost, then a
clearly tagged actor-relative same-active gauge fallback. Avoid double-counting
nested top-level cost plus PAY step. Preserve actual paid cost even when later
memory gains obscure net gauge movement. Turn changes alone manufacture no
payment. Efficiency has an explicit zero-cost/free case, not division by zero
or a globally-cheapest claim.

## Agreed APIs (not yet implemented)

Owned future files:
- SOURCE/interaction_learning.py
- SOURCE/test_interaction_learning.py
- RULES/learning-2026-11-04/INTERACTION_CRITERIA.json

Export CRITERIA, CRITERIA_SHA256, criteria_manifest().

score_transition(before_view, after_view, seat, *, command=None, result=None,
                 context=None, public_metrics_before=None,
                 public_metrics_after=None)

Returns label, meaning, reward, components, memory_cost, efficiency,
criterion_sha256, status='HEURISTIC_OBSERVED_BOARD_IMPACT', and public tempo
summaries. Context supplies pinned printed definitions. Base views stay unchanged.

Bot C public_metrics() schema agreed with tracker/runner workers:
{'successful_security_checks': {'A': int, 'B': int},
 'board': {'A': {'battle_card_count': int, 'digimon_count': int,
                'tamer_count': int, 'option_count': int,
                'total_stack_cards': int, 'digivolution_card_count': int,
                'largest_stack_size': int}, 'B': same}}

Only committed actual successful Security confirmation increments the counter;
declarations, canceled attacks and direct attacks at zero Security do not.
Pass metrics via score_transition keyword args, and via
bot decision['public_metrics']; don't add unexpected keys to base player view.

LearningState(): export(), state_id property, from_dict(export),
update_completed(game_id, winner, decisions, *, eligible=True).

LearningPlayerBot(context, seat, learning_state, policy_seed):
manifest(), choose(view,candidates,decision=None), bottom_order(remainder),
decision_log, export_rng(), restore_rng().

Six base decision fields remain decision/public_view_sha256/candidates/chosen/
reason/bot_id. Add learning metadata with context_id, seat, state_key,
action_key, input_state_id, mode, support, epsilon. Runner attaches each resolved
decision's actor rating as d['reward']=rating['reward'] (or d['rating']=rating),
and explicit EXPERIMENTAL_RESOLVED status if supplied.

## Learning rules

Fresh separate per-seat tables, no archive or old-matchup learning import.
Model stays frozen within a game; update only between completed eligible games.
No HALT/pause updates. Deduplicate game IDs, reject conflicting duplicate update
payloads, and count one independent support unit per state/action per game.
Store mean observed board reward and wins/visits separately. At least three
completed independent-game supports before overriding the declared style.
Root permits an optional small discounted future-board-return term (gamma0.95)
to recognize setup; if added, expose immediate mean and future return separately,
never rename win association as causal probability. This part is not implemented.

Key coarse own/public state and current decision kind/effect plus normalized
candidate. Remove copy indices and transient entity/pending IDs so observations
can generalize across actual dealt cards without preloading game routes.
Retain card numbers, action/target roles and semantic costs. Don't use exact
hidden opponent cards, future Security contents, deck order or private snapshots.

Use explicit epsilon0.10 named-policy exploration with separate Python Random
seeded externally by context/cohort/game/seat/training-input hash. Never use game
RNG or ReferencePilot. Save and restore policy RNG states, and retry selected
failed actions without selecting them again. Validate all offered choice schemas
before exploration so unknown software behavior cannot become a blind decline.

## TDD/verification still pending

No tests were written or run. Planned cases: green/yellow/red actual field
deltas; larger removed stack > rookie; ready Blocker incapacitation; reanchoring
without false removal; completed-check counters; memory cost/cap/turn changes;
free efficiency; privacy; cold-start style; min3 learned override; duplicate
update idempotence/conflict; no halted training; frozen within-game model;
policy RNG export/resume; no game RNG use; deterministic exact learning state.
