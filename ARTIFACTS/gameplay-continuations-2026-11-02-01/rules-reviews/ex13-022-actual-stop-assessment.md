# Actual EX13-022 battle digivolution stop

Scope: `ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-0059.json.gz`, seed `7068922568811995332`. This is a source-backed factual review of that exact board and chosen command. It makes no pilot/strategy choice and grants no full-match credit or certification. No engine files changed. Exact last command and state retained in `ex13-022-actual-stop.json`.

## Exact encountered state

B active, turn3 MAIN, memory6, no pending effects/attack and once_used empty. B battle contains only unsuspended one-card B:EX13-019#1 Veedramon (entity1), played turn1. B breeding contains B:EX13-002#1 alone. B hand:

- B:BT12-029#1
- B:P-138#3
- B:BT11-112#2
- B:BT22-022#1
- B:EX13-022#4

A battle contains only unsuspended one-card A:BT11-032#1 UlforceVeedramon (entity2), no statuses. A breeding contains A:EX13-002#4 alone. No Tamers are on the field. Chosen command is B:EX13-019#1 -> B:EX13-022#4, printed normal "Blue3 from Lv.4", route_index0, cost3.

## Exact official sources

- EX13-022: https://world.digimoncard.com/cardlist/?search=true&card_no=EX13-022 . Pinned HTML SHA256 `4771e6eab5218e833eebf7d1ff6cf70ad6fa51a51d556f8a404ac88f07256874`.
- EX13-019: https://world.digimoncard.com/cardlist/?search=true&card_no=EX13-019 . SHA256 `0e9158139b3c4d46987c85a968f40469743a76892cba86227871ed897b1e4d5a`.
- BT11-112: https://world.digimoncard.com/cardlist/?search=true&card_no=BT11-112 . SHA256 `fdb1fd52a0c1a123ad67b1eb6b472119bca26cba2622cdc1752fc038b0be1cfc`.
- BT11-032: https://world.digimoncard.com/cardlist/?search=true&card_no=BT11-032 . SHA256 `82c0b74c599cb27d0784d93959057b2504e97c4e593af5ee0a0fce51db30d50e`.
- EX13-002: https://world.digimoncard.com/cardlist/?search=true&card_no=EX13-002 . SHA256 `9d2abc2c3a5f20aebefbcb5b89818a4559748ddbde4e20f92562092b7267cd4f`.
- BT11-023: https://world.digimoncard.com/cardlist/?search=true&card_no=BT11-023 . SHA256 `8a0641a7b790f34271ee55cfac8b183f29ce2f546bfd62b704069952e5001e23`.
- Comprehensive rules v4.3: https://world.digimoncard.com/rule/pdf/general_rule.pdf?20260918 . SHA256 `a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271`.

EX13-022 exact relevant text:

> [On Play] [When Digivolving] [When Attacking] [Once Per Turn] You may play 1 Tamer card with [Veedramon] in its text from your hand without paying the cost.
>
> [All Turns] [Once Per Turn] When any of your Tamers are played, 1 of your opponent's Digimon or Tamers can't suspend until their turn ends.

## Bounded legal resolution and decisions

1. This exact evolution is legal: EX13-019 is blue Lv.4 and EX13-022's ordinary route is blue Lv.4 cost3. CR8-1-3-1/2/3: reveal, choose matching requirement and source, pay3, stack and draw1. B memory6 ->3. CR8-1-2-3 preserves the source orientation. Result is an unsuspended B AeroVeedramon with EX13-019 underneath, same ongoing entity. Its inherited source effect is Jamming (CR4-3-3/15-3-1). EX13-019's former top-card When Attacking Tamer-play effect is not an inherited effect.

2. The exact stored B deck's top (last element; actual runtime drawing uses deck.pop) is B:BT11-023#1. That card is drawn into B hand before When Digivolving is processed. B deck39 ->38. This statement concerns the preserved original prefix, not a guarantee about a subsequently changed replay.

3. EX13-022's When Digivolving triggers after evolution completes (CR15-16-3-1), and is processed after the digivolution draw (CR8-1-3-3;15-8-3-2). Actual choices: decline its optional play, or play exactly B:BT11-112#2 without paying cost. Rina is the only Tamer in the post-draw hand and has Veedramon in printed text. The drawn BT11-023 is a Digimon, not another Tamer choice. CR4-23-1 and EX13-022 Q7264 define "with X in its text". CR15-9-2-2 makes the play optional; the reviewer chooses neither branch. The consolidated On Play/When Digivolving/When Attacking effect has one Once Per Turn limit, not an independent allowance for each trigger (CR15-14-1-1/4).

4. If declined, no Tamer is played, so EX13-022's All Turns Tamer-play trigger does not occur (CR15-8-3-4). Remain B main memory3 with the evolved stack, no other new effect.

5. If Rina is played, move B:BT11-112#2 from hand into B battle unsuspended, pay no memory (card effect; CR7-1-3/3-4-3). Rina On Play and the existing evolved EX13-022 All Turns Tamer-play effect trigger together. Both are controlled by B. CR15-4-3-1/4/5-1 gives B the choice of which resolves first, then the other; this order should be recorded even though on this exact board either has the same eventual affected entities.

6. Rina On Play is mandatory. The only own battle Digimon eligible for [Veemon]/[Veedramon] in name is the new B:EX13-022#4 AeroVeedramon stack. Choose that entity and grant Blocker and Evade until A's turn ends. The B breeding egg cannot be affected/referenced (CR15-1-7;3-4-7-3/8). No other target/decline is legal here (CR15-1-5;15-9-1-2;15-10-2-1;15-11-1-3-1).

7. AeroVeedramon's All Turns effect is also mandatory and unused. The only opponent battle Digimon/Tamer is A:BT11-032#1 UlforceVeedramon. Choose that unique entity and apply cannot_suspend until A's turn ends. This status does not suspend it or otherwise change its current orientation. A breeding egg is not an eligible target. Record the target explicitly. BT11-032 has no effect that prevents this status.

## Actual Tamer-play observers, checked exhaustively only for this board

- New EX13-022 top effect: yes, All Turns/Once Per Turn Tamer-play prohibition effect as above.
- Opponent A:BT11-032#1: its "[Your Turn] When any of your blue Tamers are played, this Digimon unsuspends" does not trigger during B's turn, and a B Tamer is not one of A's Tamers. No A unsuspend or associated return effect occurs.
- Own EX13-019 source: inherited Jamming is persistent and has no Tamer-play reaction. Its printed top-card When Attacking effect is not active as an inherited effect, and no attack occurs.
- B:EX13-002#1 in breeding: its inherited Tamer-play optional unsuspend cannot trigger from breeding (CR3-4-7-4); as a standalone egg it also grants no inherited effect to a stack here (CR15-3-1).
- B:BT11-023#1 drawn into hand: its inherited Tamer-play memory gain is not granted to the evolved battle stack (CR15-3-1); no memory gain occurs from it.
- Newly played B:BT11-112#2: its own On Play occurs; its separate Veedramon-suspend and blue-Digimon-unsuspend triggers do not occur because no orientation changed.

The newly evolved EX13-022's own inherited unsuspend is not active on itself (CR15-3-1). The free Tamer does not cause an unsuspend event on this exact board. No additional inherited memory or effect draw is justified.

## End timing for the exact action

Evolution costs3 from6; any free Rina play costs0, and neither On Play nor the Tamer-play prohibition changes memory. Therefore both optional branches finish at B3 and continue B main. End-of-turn timing does not occur as part of this action (CR6-1-4-1;6-6-1). If the status/grants branch was taken, their specified expiration is the end of A's turn, not the end of the current B turn. This note selects no next main action.
