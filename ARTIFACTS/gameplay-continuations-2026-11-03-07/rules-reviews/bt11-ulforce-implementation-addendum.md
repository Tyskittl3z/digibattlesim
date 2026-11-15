# Ulforce implementation addendum

**No concrete defect found for the actual saved Ulforce interaction.** Independently ran the new EncounteredUlforceBlueTamerTests class: **3 tests passed,21.666s**. The reviewed source hashes remained unchanged during this audit; both BT11 bindings match the pinned card definition, main-text hash and official-source evidence.

Read new bindings in tamer_play_effects.py and battle_evolution.py with the shared play, pending-effect, orientation, grant and transaction procedures. WhenDigivolving queues only after the real bonus draw; optional free play filters own current-hand Blue Tamers. The observer requires the played card's owner, that owner's YourTurn and Blue color. Both effects have no printed OPT. Mandatory self-unsuspend accepts no decline and uses the existing orientation procedure, which emits no change or reaction for an already-unsuspended Digimon. Future true unsuspend still stops precisely at the unimplemented own bounce dependency before state mutation.

The actual saved segment07 now records the expected path: cost4 takes3→−1; draw Rina#3; play her for0; choose her OnPlay grant first targeting A:BT12-029#2; then process Ulforce's mandatory no-change unsuspend. No memory, Draw, bounce or OPT use was invented. Actual Aturn7 completion removes the old restrictions and old BBlocker/Evade, while the new Rina grant remains through Bturn8 end.

Independently verified the optional decline and **four branches** covering both simultaneous orders for each of the two actual Rina targets. Every branch preserves memory−1, RNG, unused OPT and entity-9's existing restriction; every new grant expires at actual Bturn8 end. Replayed all**103** successful commands of the newly saved segment with exact public views/results,108-card conservation after every action and exact final physical state/RNG. Command104 was not executed by this audit.

Full source hashes, binding manifests, branch results, source pins and replay hashes: [bt11-ulforce-implementation-addendum.json](bt11-ulforce-implementation-addendum.json). The earlier phase review was clarified: all A cards were already unsuspended at its turn7 unsuspend phase, so no actual orientation change occurred there; genuine normal-phase unsuspension can trigger the appropriate observers.

No SOURCE edits; this remains experimental encounter evidence with **zero complete-match, strategic-lane or final-evaluation credit**. The next EX13-023 stop and future bounce implementation are outside this addendum.
