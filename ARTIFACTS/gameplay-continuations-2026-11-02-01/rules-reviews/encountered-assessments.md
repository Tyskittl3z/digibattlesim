# Actual encountered actions: source-backed factual assessment

Scope: narrow review of recorded actions and their actual boards. This review grants no match credit, strategy color, or certification. No engine files changed. Original HALTs remain preserved. Exact selected command records and artifact hashes are in `actual-stops.json`.

## Authorities checked

- Official BT11-112 card page: https://world.digimoncard.com/cardlist/?search=true&card_no=BT11-112 . Pinned local `RULES/matchups/123129-vs-124303/sources/official-BT11-112.html`, SHA256 `fdb1fd52a0c1a123ad67b1eb6b472119bca26cba2622cdc1752fc038b0be1cfc`.
- Official BT22-085 card page: https://world.digimoncard.com/cardlist/?search=true&card_no=BT22-085 . Pinned local `RULES/matchups/123129-vs-124303/sources/official-BT22-085.html`, SHA256 `a453871077f17613ac9b1d52bbe3065509f2d0fd75ff8d2e040aa3658d3435f1`.
- Official BT22-023 card page: https://world.digimoncard.com/cardlist/?search=true&card_no=BT22-023 . Pinned local `RULES/matchups/123129-vs-124303/sources/official-BT22-023.html`, SHA256 `a184df26a6bd8c5ccaed325998c9b85a18c0c2d5c0778a20993fd2d6a01e67dd`.
- Official comprehensive rules v4.3: https://world.digimoncard.com/rule/pdf/general_rule.pdf?20260918 . Pinned local `RULES/matchups/123129-vs-124303/sources/general_rule.pdf`, SHA256 `a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271`. Text extracted locally to `general_rule.txt`; exact rule identifiers below refer to that PDF.
- Target identity/card information checked from corresponding pinned official card pages, with extracted source text beside these notes: P-138 is blue Lv.4 Veedramon, DP5000; EX1-013 is blue Lv.3 Veemon; EX13-019 is blue Lv.4 Veedramon/CS; EX13-017 is blue Lv.3 Veemon/CS; BT12-029 is Lv.6 UlforceVeedramon (X Antibody).

## Shared procedures relevant to these actual actions

- CR 1-3-2: "If a player is requested to perform an impossible action, that action will not be carried out. If only some of those actions are impossible, the player performs as many of the required actions as possible."
- CR 1-3-11-1: a card may be declared only if it can be utilized and its cost/alternate cost paid. CR 4-2-2 pays a cost by moving memory toward the opponent by exactly that value.
- CR 6-5-1 and 6-5-1-1: with no unresolved processing, the turn player may play a Digimon or Tamer from hand during main. CR 7-1-3-1 through 7-1-3-3: declare/reveal; pay; place on field and complete play. CR 3-4-3: cards placed in the field are unsuspended.
- CR 15-16-2-1: [On Play] triggers when the action of playing that card completes. CR 15-4-2-2/3 and 15-8-3-1/2: triggered effects trigger whenever conditions are met and resolve after the current rule/effect processing; do not suppress an On Play because there are zero targets.
- CR 15-1-5: mandatory processing must be performed whenever possible. CR 15-9-1-2: mandatory processing cannot be declined.
- CR 15-1-7: an effect with no specified area can specify/reference/affect cards in the battle area. CR 3-4-7-3 and 3-4-7-8: ordinary effects do not affect/reference breeding cards unless they explicitly specify/reference breeding.
- CR 15-10-2-1: for "X Digimon"/"X cards", X or as many up to X as possible must be chosen. CR 15-11-1-3-1: only a target meeting the targeting conditions can be chosen. Thus "1" is mandatory if one or more legal targets exist, but resolves with zero if none exist. Choosing a target is at effect activation/resolution, not a condition for declaring an ordinary hard play.
- CR 6-1-4-1 and 6-6-1/2/3: memory on the opponent's side does not interrupt the card/effect procedure; resolve current processing, then end-of-turn timing and its processing, then transfer turn. CR 6-6-4 additionally covers memory returning to 0 or more during that end timing.

## First actual stop: BT11-112, empty board

`ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-0000.json.gz`, seed `12017913134550805276`, last command PLAY_CARD `A:BT11-112#2`, turn1 A MAIN memory0. Both battle areas and breeding areas empty. Recorded reason: `PLAY_EFFECT_UNSUPPORTED: BT11-112 timing=On Play`.

Official BT11-112: Tamer, play cost3. On Play: "Until your opponent's turn ends, 1 of your Digimon with [Veemon] or [Veedramon] in its name gains <Blocker> and <Evade>."

Assessment: ordinary hard play is legal in this recorded state. Pay3 (A signed memory 0 -> -3), remove this exact card from hand and place it unsuspended in A's battle area. Its On Play triggers; there is no eligible own Digimon, so the effect resolves with no target and grants nothing (CR 1-3-2, 15-10-2-1). This is not an optional decline. No target choice is required on this exact board. Rina remains in the battle area. No unsuspend/suspend/attack happened, so her other printed triggers did not occur. Once processing resolves, end timing and turn transfer give B3 memory. The unsupported software stop supplies no basis to call this hard play illegal or the text ambiguous.

## BT22-085 actual hard plays

Official BT22-085: blue Tamer, cost4. On Play: "1 of your Digimon with [Veedramon] in its name gets +3000 DP until your opponent's turn ends." This is mandatory if a qualifying own battle Digimon exists. It does not include Veemon as a standalone name. Its Start of Your Turn memory setting does not trigger on play; its attack/Jamming effect does not trigger merely by playing it.

1. `...2026-11-02-02/attempt-0003.json.gz`, seed `10449966399963017273`, B turn3 MAIN memory2. B battle empty; B breeding EX13-002 + BT11-023. Opponent A has P-138. Hard play B:BT22-085#1 is legal; pay4 -> B signed memory -2; On Play resolves with zero targets. The opponent P-138 is not "your Digimon" and breeding cards are excluded. No target choice. Finish processing/end timing, then A2. The same no-target reasoning applies to actual `attempt-0021` and `attempt-0023`, without needing to enumerate hypothetical boards.

2. `...2026-11-02-02/attempt-0057.json.gz`, seed `2859028109560468444`, A turn4 MAIN memory1. A battle has only unsuspended A:P-138#2 Veedramon with no statuses, B has EX13-017. Hard play A:BT22-085#1 is legal; pay4 -> A signed memory -3. On Play must choose A:P-138#2, the unique qualifying own target, and give +3000 DP until B's turn ends (5000 ->8000 while active). It cannot decline the mandatory buff or choose the opponent card. Record that unique target explicitly even if the engine automatically selects it. Resolve processing/end timing, then B3. P-138 is a one-card Digimon here; its printed inherited memory effect is not active on itself and no unsuspend occurred.

## BT22-023 actual hard plays and target choices

Official BT22-023: blue Lv.5 AeroVeedramon, cost7, DP7000. "[On Play] [When Digivolving] Return 1 of your opponent's level 4 or lower Digimon to the bottom of the deck." This is a mandatory single opposing battle Digimon target when one exists; level5+ and breeding cards do not qualify. On ordinary hard play, execute On Play only. The When Digivolving trigger is not caused by a hard play. Its inherited effect is not active on itself (CR 15-3-1).

1. `...2026-11-02-02/attempt-0010.json.gz`, seed `5110499696458660652`, A turn1 MAIN memory0, both battle areas empty, A breeding an egg. Hard play A:BT22-023#1 is legal; pay7 -> A signed memory -7. On Play triggers and resolves with zero targets. Do not require a nonexistent opponent target and do not turn this mandatory no-op into an optional decline.

2. `...2026-11-02-02/attempt-0017.json.gz`, seed `3688996315290345728`, B turn3 MAIN memory2. Opponent A has the sole P-138#1 (Lv.4 Veedramon), B battle empty. Hard play B:BT22-023#1 is legal; pay7 -> B signed memory -5. On Play must choose A:P-138#1 and return that card to the bottom of A's deck. It is a one-card Digimon in the trace; there are no digivolution cards to dispose of or leave-area replacement effects on it. Returning it is not deletion. Record the unique target.

3. `...2026-11-02-02/attempt-0045.json.gz`, seed `1639833986765908560`, B turn3 MAIN memory6. Opponent A has A:EX1-013#2 (Lv.3 Veemon) and A:EX13-019#1 (Lv.4 Veedramon), each a one-card Digimon with no statuses. B battle empty, breeding an egg. Hard play B:BT22-023#3 is legal; pay7 -> B signed memory -1. On Play must choose exactly one of those two actual opposing battle Digimon, then return the chosen card to the bottom of A's deck. Both are legal targets; neither has a printed return-prevention/replacement effect. This requires an explicit two-way target decision; it cannot be silently skipped or treated as no-target. The reviewer makes no choice or strategy recommendation.

4. `...2026-11-02-01/attempt-0006.json.gz`, seed `4491315600022495233`, A turn3 MAIN memory10. Opponent B has only B:BT12-029#2 (Lv.6); A battle empty and breeding a Veedramon stack. Hard play A:BT22-023#1 is legal; pay7 -> A memory3. The On Play has zero legal targets: the opponent's only battle Digimon is Lv.6. It remains on board, A remains in main after effect resolution because memory is still A3. Own breeding Veedramon does not change that target set.

For hard-play cases1-3, the cost crosses memory. After On Play resolves, BT22-023's "[End of Your Turn] [Once Per Turn] 1 of your blue Digimon or Tamers may unsuspend" triggers at end timing (CR 15-16-12-1). On these exact boards the newly played AeroVeedramon is the only own blue battle Digimon/Tamer, and is already unsuspended. The choice may be declined (CR 15-9-2-2), or it may select that already-unsuspended Digimon; CR 1-3-3 leaves it unchanged and produces no unsuspend event. Breeding is not an eligible target. Do not silently manufacture a useful unsuspend or an inherited memory gain. The presence of an optional choice must be recorded, without judging its strategy.

## One actual BT22-023 battle digivolution stop

`...2026-11-02-02/attempt-0046.json.gz`, seed `2035718192038532479`, B turn4 MAIN memory3. Recorded chosen source B:EX13-019#4 (blue Lv.4 Veedramon/CS, unsuspended, one card), target B:BT22-023#2, special route cost3. This actual source meets the printed "Lv.4 w/[CS] trait: Cost3" condition. Pay3 -> B memory0, stack AeroVeedramon on the source preserving orientation, draw1 (CR 8-1-2-3; 8-1-3-1..3). Then When Digivolving triggers (CR 15-16-3-1), with mandatory choice between opponent A:EX13-017#3 (Lv.3) and A:EX13-019#4 (Lv.4), both one-card battle Digimon without replacement/prevention. Return exactly the chosen card to A deck bottom; record which. The former top EX13-019 now grants its inherited Jamming; its former top-card When Attacking effect is no longer the top-card effect. AeroVeedramon's own inherited unsuspend effect is not active on itself. Main may continue at B0 after current processing; no end-of-turn trigger occurs merely because the cost reached0. No strategy choice is made by this review.
