# UlforceVeedramon vs Gallantmon transcript review

Evidence status: transcript-only. No footage of this game was opened in this review. The source is the user-uploaded timestamped text `/workspace/attachments/1d65edb1-e371-46e1-93c4-4e737509638b/Pasted text.txt`. It describes an 11:26 video. Transcript card names are noisy; named set numbers and matching effect wording support the IDs below, but uncertain mappings remain explicit. This supplies regression candidates, zero simulated or judge-certified matches, zero strategic lanes, and no result evidence.

Comparison target: context `53f4e043b49fca0bf6e691754098e73774995cfee182e7c8245cf446e2d70733`, exact current A/B lists from `ARTIFACTS/ex13-engine-2026-10-30/context.json`.

## Scope difference

The narrated Gallantmon deck includes EX13 Gigimon, Guilmon, WarGrowlmon and Takato, BT7 Takato, and an apparent BT21 Gallantmon. These cards are absent from current selected B. The transcript therefore cannot be treated as a replay of the selected exact matchup. The selected A has all of EX13-002/017/019/022/023/069, BT11-112, BT11-023 and P-138, making its generic trigger sequences particularly useful. Current B overlaps BT19-009, EX13-015, EX8-073 and the training Options. Do not import the video's deck composition, pilots, or outcome.

## Candidate cases

1. **00:08–00:24; 00:33–00:59; 01:14–01:25; 02:49–02:59; 04:21–04:35 — Training reveal followed by later Delay evolution.**
   - Transcript: Punching Training reveals two and selects a BT19 Growlmon; Parkour Training reveals Mental Training; Mental Training reveals a promo Veedramon. Later Delay effects reduce normal evolution costs by two.
   - Grounded current IDs: LM-061 Punching Training (B), LM-058 Parkour Training and P-104 Mental Training (A), BT19-009 Growlmon (B). The promo Veedramon's exact ID is not established merely by its nickname.
   - Printed check: LM-061/058 both have a conditional color-requirement exemption while no same-name training is in the battle area; reveal two, choose one matching-color card, return rest to bottom, place Option in battle area; Delay evolves one Digimon into a matching-color Digimon with cost reduced by two. P-104 has blue-only search and Delay. Q4192 says evolution requirements still apply; Q4195 permits choosing not to evolve.
   - Regression: preserve explicit chosen reveal card/bottom order, Option instance and later trashing; do not invoke Delay on the initial use; require legal evolution requirements even when reduced cost is zero. Include a same-name Option already in battle area to exercise the exemption condition independently of usable color sources.
   - Unknowns: exact full reveal order, other hand choices, and enough source states to replay the whole opening are absent. The transcript alone does not prove legal turn-of-placement Delay timing.

2. **01:23–01:30 — BT19-009 Growlmon's When Digivolving Tamer play.**
   - Transcript: evolution into BT19 Growlmon, then free EX13 Takato if one or fewer Tamers.
   - Printed check: BT19-009 exactly says `[When Digivolving] If you have 1 or fewer Tamers, you may play 1 [Takato Matsuki] from your hand without paying the cost.`
   - Regression: zero/one/two Tamer branches; optional decline; choose an actual Takato instance; queue its real On Play effects. Ordinary hard play of Growlmon must not fire or be blocked by this unrelated trigger.
   - Scope: BT19-009 is current B; narrated EX13 Takato is not. A selected-pair synthetic case can use B's BT19-080, but must be labeled an adapted case, never this video's exact state. Subsequent narrated EX13 Gigimon-triggered evolution is outside current B.

3. **02:36–02:48 — EX13-017 Veemon's When Moving search.**
   - Transcript: move breeding Veemon to battle area, reveal three, add BT22 Rina.
   - Printed check: EX13-017 `[When Moving] [On Play]` reveals three and adds one card with Veedramon in text or Royal Knight trait; bottom rest. BT22-085 Rina is in current A and has Veedramon in effect text.
   - Regression: run the actual move-triggered search before ordinary main action availability; choose one physical card and preserve the rest's bottom order; moving does not re-run a generic On Play trigger.
   - Unknowns: exact other two revealed cards/bottom order are unreported.

4. **02:59–03:53 — Digivolution within attack-trigger resolution, before Counter.**
   - Transcript: EX13 Veedramon attacks; its attack effect plays EX13 Rina at reduced cost; EX13 DemiVeemon inherited effect unsuspends; Rina suspends to draw and evolve to EX13 AeroVeedramon; Aero plays Rina whose described On Play gives Blocker/Evade, then Aero prevents Gallantmon from suspending. Only afterward narrator announces Counter timing.
   - Grounded IDs: EX13-019, EX13-002, EX13-069, EX13-022, BT11-112 (transcript says `BT1` but the exact narrated Blocker/Evade effect matches BT11-112 in current A).
   - Printed check: the described trigger bodies match those five pinned cards. EX13-069 Q7437 requires suspending the Tamer before processing the `After` evolution; Q7439 prohibits stacking multiple Rina reductions onto one evolution. EX13-022's Tamer-play trigger prohibits suspension until the opponent's turn ends.
   - Regression: preserve attacker stack identity through evolution and unsuspension; resolve newly triggered effects in their actual windows; delay Counter until preceding effects finish. The original attack remains in progress after unsuspension. Enforce each printed Once Per Turn independently, including Aero's shared On Play/When Digivolving/When Attacking limit.
   - Unknowns: exact trigger-order selections beyond narrated order, full hands, complete target alternatives. Do not infer all competing choices were exercised.

5. **03:53–04:01 — EX13-015 Gallantmon Counter and no-deletion fallback.**
   - Transcript: Counter deletes a 12000+ DP target if available; none exists, so trash top security.
   - Printed check: EX13-015's On Play/When Digivolving/When Attacking/Counter timings share one `[Once Per Turn]` effect. Q7250 allows only one Counter effect per attack. Q7248 disallows skipping a legal 12000+ target to force the fallback.
   - Regression: defend with the in-play Counter effect and apply fallback when no deletion happened; do not double-activate the same shared effect at a later trigger that turn; stop normal security check if the attack becomes invalid for a separately established reason.
   - Scope: both card IDs are current-pair compatible. Exact defending OPT usage must be reconstructed; merely reaching Counter does not imply availability.

6. **04:35–05:32 — Failed deletion payment does not prevent Gallantmon leaving.**
   - Transcript: Ulforce evolves, changes orientation, then bottom-decks Gallantmon. Gallantmon attempts its leave-prevention deletion, Ulforce Evades, payment deletion fails, so Gallantmon still leaves; Aero inherited unsuspends Ulforce afterward.
   - Grounded IDs: EX13-023, EX13-015, EX13-022, BT11-112. The transcript's deletion-threshold sources are not safely identified by their noisy names.
   - Printed/Q&A check: EX13-015 prevention requires **by deleting** an opposing 9000-or-less Digimon. Q7247 explicitly says it leaves if prevention stops that deletion. Q7252 says numerical deletion-maximum increases apply to this effect. EX13-023 has Evade. EX13-022 inherited unsuspension can trigger after its suspension.
   - Regression: replacement payment must record actual successful deletion, not mere selection/attempt; do not undo the original bottom-deck event when payment fails. Preserve pending suspension reactions for subsequent legal resolution. Include branches where target is already suspended or deletion succeeds.
   - Scope adaptation: current B can reach 13000 via BT19-007 + BT19-009 at zero-or-less memory; both numerical bonuses are pinned. That is a new synthetic case, **not a claim these were the video's cards**.

7. **05:33–05:44 — BT11-023 ordinary hard-play search.**
   - Transcript: hard play Veemon for three, reveal top three, add BT22 Veemon/Veedramon-like card and bottom rest.
   - Grounded ID: BT11-023 identified by set number and exact two-category search. Target exact ID remains unconfirmed from noisy name.
   - Q&A check: Q2066 permits adding a card from the single available category; Q2067 requires adding as many as possible when both a matching Digimon and blue Tamer are revealed.
   - Regression: do not infer the video intentionally declined a mandatory available blue Tamer; without full reveals it is unknown whether one existed. Existing engine search tests can reuse the printed maximum-selection rule rather than learning this narration as an oracle.

8. **07:45–09:07 — Assembly plus selectable simultaneous On Play order, then Rina reactivation.**
   - Transcript: EX13 Ulforce is played at seven with Lv5 Aero, promo Veedramon and BT11 Veemon underneath; choose its bottom-deck effect first; after new reactions, change orientation by suspending itself, inherit-unsuspend, gain memory and resolve Rina draw; then another pending BT11 Rina suspension reaction activates Ulforce's non-OPT bottom-deck When Digivolving effect again.
   - Grounded current IDs: EX13-023, EX13-022, BT11-023, BT11-112, EX13-069; P-138 is consistent with the **described inherited gain-memory effect**, but `promo Veedramon` alone is not sufficient visual identification.
   - Printed/Q&A check: Assembly -5 requires Lv5/Lv4/Lv3 all Veemon/Veedramon (Q7268); printed cost 12 implies seven when one applicable reduction is used. Q7266 allows controller choice between simultaneous On Play effects. BT11-112 Q7200 allows choosing a When Digivolving effect; Q7199 forbids bypassing exhausted per-turn limits. The bottom-deck effect has no OPT; the orientation effect does.
   - Regression: preserve material physical identities/zones and instance identity; queue each simultaneous effect separately; preserve pending reactions through nested effects; activation by Rina is not an actual digivolution event and does not create a digivolution draw or reset OPT. Test both legal original On Play orders and explicit chosen branch. The opposing BT21/BT7/EX13 cards in the narrated leave/play-back chain are outside current B and cannot be transplanted into current-pair fixtures.
   - Unknowns: material source zones are not completely specified by text, so exact Assembly legality is not certified here; no exact state replay claimed.

9. **09:24–09:45 — Evade leads to security-trash fallback, then inherited unsuspension.**
   - Transcript: EX13 Gallantmon attempts to delete 12000-DP Ulforce; Ulforce suspends for Evade; no deletion occurs, so security is trashed; EX13 Aero inherited then unsuspends Ulforce.
   - Printed/Q&A check: EX13-015 Q7249 explicitly permits the fallback after choosing a legal deletion-protected target. EX13-022 inherited is all-turns once-per-turn.
   - Regression: follow the resolution order: deletion attempt and prevention, then the same resolving effect's fallback, then eligible queued suspension triggers. Confirm security trash is not a check and does not fire normal security effects; no automatic game win merely because security reaches zero. Exercise inherited OPT already used vs available.

10. **09:58–11:15 — EX8-073 independent effects and changing orientation protection.**
    - Transcript: Gallantmon X evolves for one over Gallantmon, gives +4000 to itself/-4000 to Ulforce until next opposing turn ends; narrator says the DP reduction starts affecting Ulforce when it later suspends to Evade. Its distinct deletion/fallback effect is OPT, while the DP-changing When Digivolving/When Attacking effect repeats on attack.
    - Grounded IDs: EX8-073, EX13-023; narrator explicitly describes EX13 Growlmon inherited +2000 but that card is outside current B. B's BT19-009 can provide a conditional +2000 in an adapted state, provided memory is zero or less.
    - Printed/Q&A check: EX8-073 exactly has two separate effects with those timings; the DP effect is not OPT. Q3975 gives controller order for simultaneous effects; Q3976/3977 distinguish mandatory target choice from deletion prevented. EX13-023 is protected from opposing DP reduction only while unsuspended. EX13-023 Q7269 states that a suspended Digimon reduced to zero DP is deleted by a rule check **before** its Aero inherited unsuspend can activate. EX8-073 Q3982/3983 discuss protection gaining/losing and later applicability of a previously granted effect, but a precise continuous-protection implementation should be crosschecked against shared comprehensive rules.
    - Regression: keep duration and independent OPT for the two EX8-073 effects, re-evaluate orientation-conditioned protection, and execute rule checks before queued unsuspend effects. Do not reduce the Digimon's DP by merely making a deletion attempt. Create explicit boundary variants around 0 DP. Narrated terminal attack is not accepted as a replayed/certified outcome.

## Source integrity checks

All 16 referenced official-source files were hashed against the selected context's pinned SHA-256 and matched: LM-061, LM-058, P-104, BT19-009, EX13-017, EX13-019, EX13-002, EX13-069, EX13-022, BT11-112, EX13-015, EX13-023, BT19-007, BT11-023, P-138 and EX8-073. Source HTML for EX13-015 and EX13-023 was directly spot-checked against the extracted main text. The referenced Q&A entries come from the locally pinned `CARD_QA.json`; retrieval/hash checks are not independent rules certification.
