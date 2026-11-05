# Printed wording and trigger correction — November 2, 2026

The user correctly pointed out that printed card wording defines effects.
Several prior "interaction gaps" were overly restrictive implementation guards,
not ambiguity requiring new rulings. Implement the words at the printed timing;
normal game procedures and timing use the comprehensive rules. Unimplemented
code must not be described as a card-text ambiguity or an ILLEGAL action.

## Concrete defect and correction

The previous cohort had 43 PLAY_EFFECT_UNSUPPORTED halts. **24 of those attempts,
covering 12 cards, involved cards with no On Play effect.** The old code allowed
only three blank-main cards and five search cards, so unrelated When Digivolving,
When Attacking and other abilities prevented normal hard play.

`printed_triggers.py` now reads only leading printed labels. A timing mentioned
inside another effect's body is not a trigger for that line. Ordinary play:

1. Validates the selected inputs, actual hand copy and current play window.
2. Pays the printed normal play cost and places the card.
3. Queues only effects actually labeled On Play. Unimplemented On Play processing
   still stops explicitly instead of inventing a result.
4. Preserves all other printed abilities. It does not fire them on play, grant
   digivolution-only buffs, perform an evolution draw, or activate inherited text
   from a singleton top.

The twelve observed cards were separately reviewed for basic play/search and
breeding actions while already in play. Their unrelated abilities do not observe
those actions. This is a capability for those actions only; attack/keyword and
opponent-effect handling is not certified or silently enabled. In particular,
BT17-016's printed self-immunity remains relevant when an opponent effect applies;
these basic actions apply no opponent effect to that Digimon.

Candidate generation no longer preflights an unselected attack or breeding
evolution and blocks choosing a different action. Printed candidates remain
explicitly provisional; the chosen action validates its actual conditions.
Orientation dependency inspection also separates timing labels from effect text
instead of interpreting a heading's "When Digivolving" as an orientation event.

## Verification

**312 unit tests passed**, full command from SOURCE:
`python -m unittest discover -p 'test_*.py' -q` (51.727 seconds).
New behavior and review regressions were observed failing before implementation.
Independent software review confirmed the twelve printed bodies and found the
remaining premature breeding-candidate check; that check was corrected and its
regression passes. No additional judge certification is claimed.

Replayed the exact original command prefixes for **all 24** wrongly blocked
plays. Every pre-action runtime/physical state exactly matched the saved original
pre-HALT state. All 24 plays now resolve at the correct cost, with no unrelated
trigger activated. These are regression-prefix replays, **not full matches**.
Full evidence is `ARTIFACTS/printed-trigger-correction-2026-11-02/recorded-play-regressions.json`.

The balanced diagnostic cohort was actually rerun on the same 60 original match
seeds, 30 starts per deck. All 60 records replay exactly. Candidate-generation
code changed, so the reference-policy hash and pilot identities changed; do not
treat this as the same frozen pilot or attribute aggregate differences solely
to the trigger fix. The direct 24-prefix regression isolates that correction.

Current diagnostic halts:

| Implementation limit | Attempts |
|---|---:|
| Actual On Play processing not implemented | 31 |
| Option use | 16 |
| Battle-area evolution | 8 |
| Stacked battlefield | 2 |
| Scoped attack/battlefield capability | 3 |

All 60 still halt; there are zero software terminal games, zero accepted
fact-finding matches, zero approved roadmap lanes and zero final matches. These
are implementation limits. Clear printed wording should be implemented directly;
do not ask for a ruling merely because code for that wording is unfinished.

Saved cohort: `ARTIFACTS/imported-diagnostic-2026-11-02-01/`.
No decklist, catalog/UI code, rules interpretation or old-matchup training was
changed. Remaining work is to implement the actual effects and shared procedures
at their proper windows, then satisfy the existing full-match evidence gates.
