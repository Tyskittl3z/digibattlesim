# Game0000 turn10 actual attack declaration review

The selected **B:BT11-032#1 → PLAYER** declaration is legal at turn10 / MAIN / memory5. The attacker is ready and unsuspended, played turn4 and ready since turn5, with no active suspension prohibition. Its lower EX13-022 AeroVeedramon supplies only its inherited text. BT11-032 has no When Attacking effect.

Suspending entity-5 triggers **three simultaneous B effects**: EX13-022#1 inherited optional OPT unsuspend and BT11 Rina#2/#3 All Turns optional self-suspension/reactivation. They belong to one depth0 group; B chooses the next effect after the previous processing finishes. Opponent A Rinas do not trigger from B suspending its own Digimon. Reactivation does not itself evolve or draw. Used OPT effects must remain unavailable (BT11-112 Q7199).

CR11-1-3/4 requires all declaration-trigger processing before Counter, then Block, then confirmation. Counter and Block remain explicit windows. The saved A board has no active Blocker grants, and A has2 security. No direct-win result follows from this declaration.

A **later actual unsuspend of BT11 Ulforce** remains a separate unsupported event in this increment: it requires its mandatory OPT return1, fresh own BT11 Rina memory effects, and own EX13 Rina optional paid Draw1/After processing. Do not silently bypass that event. The return level cap is3 plus own blue Tamers at processing. This review does not execute a future effect.

Authority: pinned official BT11-032, BT11-112, EX13-022, EX13-069 wording; BT11-112 Q2142/Q2143/Q7198/Q7199/Q7200; comprehensive rules v4.3 (2026-09-18) sections7-1-2-1,11-1/2/3/4/5,15-3-1,15-4-3/5,15-7,15-8-3,15-10-1,15-14-1,15-15-7. The paired JSON verifies the exact six source hashes. Pinned EX13-019 is **Veedramon**.

Segment09 contains140 recorded commands,139 successful commands, and94 source manifest entries (counted). Separate archived-prefix proof and implementation review passed; see archive09-prefix-proof.json and turn10-attack-implementation-review.json. No SOURCE edits or new actual gameplay occurred; no complete-game, rules-certification, strategy or final-evaluation credit is awarded.
