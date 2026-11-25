# Strict v4.4 diagnostic probe

This is one software probe, **not** a member of the requested new 60-game
fact-finding cohort. It uses the styled Bot A/B policies, cohort index 0,
original seed `8204123595783142766`, and English-version worldwide context
`79ad61d1d63442f6485318823e643605181321c605d1548760ba633a3e104d78`.
The context pins Bandai's November 20, 2026 Comprehensive Rules Manual v4.4
by SHA-256. The card-page snapshots still need freshness and rules review.

`game-0000-before-route.json` halted at EX13-019's printed digivolution
route. `game-0000-after-route.json` passed that action and halted before
playing EX13-017. `game-0000-after-search.json` passed the play and search,
then halted before breeding promotion. `game-0000-after-promotion.json` passed
that move and halted before A's attack declaration. The two
`game-0000-after-attack-*.json` records passed the declaration and pause at
EX13-019's optional Tamer play; the second one names that missing effect
checker. The subsequent records pass the selected BT11-112 Tamer play, its
Blocker and Evade grant, the inherited egg unsuspend, and both memory gains.
The defender declines Counter and Block. The first security check reveals
EX13-069, whose printed Security effect plays that Tamer without cost, then
the attack ends. The second declaration checks the live Blocker and Evade grant
and BT11-112's suspension trigger. Bot A declines that optional effect. The
next security check reveals LM-057; its printed Security text searches two
cards and places the Option in the battle area. Bot A then plays EX13-017 on
the populated board. The latest record, `game-0000-after-live-play.json`,
pauses before a battle-area digivolution into EX13-022 at command 43.
Each record exactly replayed under its recorded source version at creation.
The latest record exactly replays under the current source version. The
`prefix-comparison*.json` files show that each update retained the original
seed, prior successful choices and states, and the retried failed selection.
The comparisons exclude `execution_id` because source hashes can change; they
record the source changes.

The comparison is diagnostic evidence, not a formal source-only migration or
independent official rules certification. Every probe record has zero fact-finding
and final-evaluation credit. The new cohort and 10,000-game evaluation have
not started.
