# Piercing timing discrepancy found during rules review

**Status: confirmed rules discrepancy; the 60 games remain software evidence.**

The cached official Comprehensive Rules Manual (SHA-256
`a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271`)
says in section 16-7-4 that Piercing's pending Security check is processed
immediately before the transition to the end of attack timing. Section 16-7-3
says the check is mandatory. The official BT20-102 card page (SHA-256
`6769bd16a111b682dc8f9a27fb5ea0e5a4438a6822e160c79575f480fcd8519b`)
prints Piercing on the card.

In corrected software game 24 (seed `4274756805820524210`, terminal record
`9f8c629b1e22b50bc8fcee260c5be06b85767109d0b3d21bb6735f243d930d89`),
zero-based action 163 executed `END_ATTACK` and cleared the attack. Action 164
then resolved `BT20-102.piercing_check` and checked `A:BT11-032#1` while no
attack context existed. Game 55 (seed `6404560857263661070`, terminal record
`204b670b8ee8a44bd06d9d550ed3eed7f8fa6debbfce6a988393aaf6ce44f286`)
has the same order at actions 162–163, checking `A:EX13-019#2` after
`END_ATTACK`.

The end-of-turn attack keeps an outer effect depth. The subsequent battle
triggers, including Piercing, were queued at that same depth, so the scheduler
deferred them until after `END_ATTACK`. This is a timing defect. Bot C's count
for the checked card is correct as a measurement of what the software did, but
it does not certify the order as legal. The original seeds, states, commands,
and outcomes remain preserved. No rules-certified fact-finding credit is
claimed from this sequence.
