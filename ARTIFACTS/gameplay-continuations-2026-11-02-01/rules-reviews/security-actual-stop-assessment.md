# Actual EX13-023 security stop

Scope: the single recorded security check below. No full-match credit or certification granted; no engine edits.

`ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-0008.json.gz`, seed `14636286304401485632`, command index25 `CONFIRM_ATTACK`. Turn3, active A, memory5. Attacker A:EX13-017#3 is a suspended one-card Veemon with no statuses, DP1000. B has5 security. Recorded guard: `SECURITY_CARD_UNSUPPORTED: EX13-023 source=B:EX13-023#2`. Both Counter and Block windows were explicitly declined. Checked card B:EX13-023#2 is UlforceVeedramon, DP12000, with no printed [Security] effect.

Exact record/state retained in `security-actual-stop.json`. Official card sources:

- https://world.digimoncard.com/cardlist/?search=true&card_no=EX13-023 ; pinned HTML SHA256 `3d50f704648b02667258fceb3f3675a80141599f76ca4ad1beeb3069d8fad7aa`.
- https://world.digimoncard.com/cardlist/?search=true&card_no=EX13-017 ; pinned HTML SHA256 `2aa137a4f5c18f878139b6021a274f44a1ad001b0a952390ef6690031e5e77d4`.
- Shared official comprehensive rules v4.3 https://world.digimoncard.com/rule/pdf/general_rule.pdf?20260918 ; pinned PDF SHA256 `a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271`.

Exact relevant rules:

- CR13-1-6: "A checked card is removed from the security stack and is treated as not being in any particular area."
- CR13-1-7: "A checked Digimon card is treated as a Security Digimon."
- CR13-1-8-1-1: reveal the top security card.
- CR13-1-8-2-1: effects triggered by the security check must resolve before the next action.
- CR15-16-10-1: [Security] triggers when a security check is performed on that card. CR15-16-10-2: a triggered [Security] effect immediately activates without pending activation, taking precedence even if other effects trigger simultaneously.
- CR13-1-8-3-1: battle the Security Digimon against the Digimon performing the check, resolving all processing before the next action.
- CR14-2-1-1/2: higher DP wins, lower DP loses; CR14-2-2 deletes the losing Digimon immediately. CR4-15-1: deletion places the deleted card in trash.
- CR14-2-3: Security Digimon are not deleted even when they lose a battle.
- CR13-1-8-4: "A card revealed from a security check is placed in the trash unless it belongs to an area."
- CR13-1-5: if the checking Digimon is no longer in the battle area, it cannot perform more security checks.
- CR11-6-1/2: end-of-attack timing occurs and resolves before the attack ends.

Actual effect assessment:

1. EX13-023 has no [Security] text. No checked-card effect needs activation here. It was neither played, digivolved, nor an attacker: its ordinary [On Play]/[When Digivolving]/[When Attacking] triggers do not occur (CR15-16-2-1,15-16-3-1,15-16-5-1).
2. Its Blocker text cannot reopen the passed block window or make a checked card block: CR12-1-1 specifically requires a Digimon in the battle area. The checked card is not in that area (13-1-6).
3. Its Evade has no relevant deletion to prevent. Ulforce wins this battle; additionally Security Digimon are never deleted by losing security battles (14-2-3). Placement in trash under13-1-8-4 is not that deletion. No Evade choice arises.
4. Its [All Turns] text refers to "this unsuspended Digimon" and prevention of opponent effects on its DP/stacked cards. It is not a field Digimon (CR4-3-1;13-1-6/7), has no unsuspended field orientation, and there is no opponent DP reduction/return/trash effect in this battle. That protection cannot prevent normal security-check trash placement, a rule procedure. There are no stacked cards on the checked card.
5. A:EX13-017#3 is a one-card top Digimon, so its printed inherited leave-area prevention is not inherited by itself (CR15-3-1). Its own name is Veemon, not Veedramon, and battle deletion is also not removal by opponent effects. No such replacement applies.

Expected exact bounded result: remove B:EX13-023#2 from B security (5->4); battle1000 vs12000; delete A:EX13-017#3 to A trash; then place B:EX13-023#2 in B trash under13-1-8-4. No draw/play/orientation effect, memory change, or additional check. Finish end-of-attack timing, clear the attack and remain in A main at memory5. No winner is established by this check. Existing B:EX1-013#3 and B:P-138#3 remain unchanged; A breeding egg remains unchanged. This is a software guard issue on the exact trace, not card-text ambiguity.
