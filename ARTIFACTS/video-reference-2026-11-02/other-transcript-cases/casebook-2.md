# Transcript-derived timing cases — second batch

This chapter adds six candidates without modifying the first casebook. Matchup labels and card names are inferred from captions and remain unverified. No video was viewed for this chapter, official card text was not checked, no production code changed, and no simulator match or judge-certification credit is earned. These are hypotheses for fixture design once the printed text and board state are pinned.

Original transcript SHA-256 hashes, byte counts and paths are in `source-manifest-2.json`. Timestamped text is preserved in the corresponding three `*.segments.json` files with whitespace normalized.

## Jupiter / Vulcanus — inferred labels

### JV1 — Two separate removals, one-use prevention, and source-card protection scope

- **15:38–16:18.** A linked When Attacking effect first attempts deletion. At 15:49–15:57 the narrator describes Succession supplying a prevention effect: “when any of his tier straight Digimon or tamers will leave the battle area by trashing your top security cards, they don't leave.” A second linked effect then attempts return to hand. At 16:04–16:17: “it only protects the stack cards of Jupiter and raft mode from being returned to hand or decks ... doesn't prevent the Digimon itself from being returned ... protection effect is once per turn that has already been used”.
- **Claim:** two attack-triggered removals resolve separately; a prevention is used on the first and unavailable on the second. A distinct protection concerning cards in a stack does not cover returning the whole Digimon.
- **Candidate assertions after printed-source confirmation:** track the exact prevention instance and its once-per-turn usage; collect both attack-triggered effects without merging their removal events; distinguish the affected Digimon object from its individual digivolution cards; preserve physical-card destinations when the top card returns and sources go to trash.
- **Unknowns:** exact IDs, source text, protection duration, whether the narrator means “digivolution cards” by “stack cards”, and which cards actually remain in the resulting trash/hand. Do not implement the scope distinction from that colloquial phrase alone.

### JV2 — Leave prevention pays by trashing a linked card

- **18:54–19:23.** An Option attempts to delete the lowest-DP opposing Digimon. At 19:00–19:12: “the option card divines version Omega that is linked together with Volcanis gives another effect ... will leave the battle area by trashing one of his link cards. It doesn't leave and title stream will be trashed to protect it from being deleted.” At 19:14–19:23 the Option's recovery and optional Arts Digivolution are then described, with Arts declined.
- **Claim:** a linked Option grants leave prevention to the host; the player pays by trashing a different linked card; the host survives; the resolving Option continues its later clauses, and its Arts choice is independent.
- **Candidate assertions after printed-source confirmation:** select and move the exact linked physical card as prevention cost; cancel the host's leave event while retaining the rest of the stack; recalculate linked bonuses and any link-capacity state; finish the original Option effect and expose the separate Arts choice.
- **Unknowns:** the exact granted text, cost selector, once-per-turn restriction and relationship between host and grant source. The narration alone does not establish whether the granting linked Option could instead pay for its own granted prevention. No such branch should be assumed.

## Abbadomon / Omnimon Alter — inferred labels

### AO1 — Collision's blocker grant versus a player's blocking obligation under immunity

- **11:23–12:10.** The narrator describes two Digimon as immune to opposing Digimon effects. At 11:39–11:54: “collision, giving all the opponents Digimon blocker, and they must block of able ... neither Cres Guruman or itself will gain blocker ... Blitz Greymon naturally has blocker on its own ... collision still forces the player to attempt to block if able”. The native Blocker blocks, with attack-target-switch reactions then described.
- **Claim:** immunity prevents an effect from granting Blocker to these Digimon, while an existing native Blocker remains usable; Collision's blocking obligation is treated as applying to the player rather than as a change to the immune Digimon.
- **Candidate assertions, only after the official Collision definition and immunity text are checked:** compute granted keywords separately from native keywords; derive legal blocker choices from the current board; enforce any player-facing obligation without inventing Blocker on an unaffected Digimon; process attack-target-change triggers after a legal block.
- **Unknowns:** this is a rules-sensitive interpretation, not an established rule from this source. Exact immunity scope and the official distinction between an effect on a player versus a Digimon are required. Captions alone cannot validate the narrated mandatory block.

### AO2 — “Would leave” Delay activation and Evade on the same threatened deletion

- **14:14–14:40.** A redirection causes an attacking Digimon to battle a stronger target. At 14:28–14:38: “Since Cres Guruman will leave the battle area, our courage united delay effect will trash itself to play out the AD1 Greymon. At the same time, Cres Guruman has the keyword evade. When this Digimon would be deleted by suspending this Digimon, it isn't deleted.” A played Digimon's On Play effect is then described at 14:40.
- **Claim:** a Delay effect associated with an impending departure is activated, and Evade also prevents that departure; the narrator gets both the played card and a surviving threatened Digimon.
- **Candidate assertions, only after timing/rulings are verified:** represent a threatened leave event separately from a completed zone move; offer the exact legal pre-leave effects and costs; determine whether using one makes the other no longer activatable; queue a played card's On Play effect only if the play actually occurred. A fixture must assert the officially correct outcome, which may differ from the narration.
- **Unknowns / high-priority check:** “at the same time” hides activation order. The caption does not prove both activations are legal or that the threatened Digimon is unsuspended at Evade payment. Check the precise Delay trigger, whether it has a leave-event requirement after prevention, and the battle/attack timing before adopting this line.

## Rebootmon / Marsmon — inferred labels

### RM1 — Reboot unsuspension retriggers a temporary effect on the opponent's turn

- **03:58–04:08**, **04:43–04:50**, **05:13–05:23** and **06:19–06:30**. At 04:00–04:08: “all turns effect activates once returned when this Digimon gets linked or unsuspend until your turn ends. This Digimon gains piercing and blocker ... your opponent's Digimon effects don't affect it.” The narrator says these expire when the turn passes at 04:48–04:50. At 05:14–05:23: “unsuspend phase where reboot man has a keyword reboot which can unsuspend itself and his alternate effect will activate once again ... to the end of reboot's turn.” A subsequent opposing Digimon effect is described as ineffective at 06:26–06:30.
- **Claim:** the first grant expires, then Reboot causes an unsuspension on the opponent's turn; that is a fresh trigger granting immunity and keywords through a later “your turn ends” boundary.
- **Candidate assertions after printed-source confirmation:** reset once-per-turn usage at the correct turn boundary; dispatch Reboot's actual unsuspension event; trigger an All Turns ability on that event; calculate “your turn” from the effect controller, not simply the currently active player; preserve the renewed effect through the remainder of the opponent's turn when the printed duration requires it.
- **Unknowns:** ASR renders “once returned” and “walker”; neither is card text. Pin the exact grant duration and whether the event is a genuine state change. Do not fire the trigger merely because an already-unsuspended card reaches the unsuspend phase.

### RM2 — Effect-caused evolution versus ordinary evolution, with an explicit optional decline

- **07:00–07:30**, **08:44–08:57** and **09:10–09:35**. At 07:22–07:29 an All Turns effect is narrated as “when effects play or digol any Digimon, which includes itself ... Then this Digimon may battle one of your opponent's Digimon.” At 08:49–08:57 a tamer offers a Digivolution: “However, it will choose not to because this is considered as digolving by an effect”. At 09:10–09:14 an ordinary paid evolution is made, and its subsequent When Digivolving effect links a card, ultimately returning the opposing trigger source to deck.
- **Claim:** the narration distinguishes ordinary paid evolution from evolution performed by an effect; an optional tamer evolution is declined, and later a different evolution occurs through a normal action.
- **Candidate assertions after printed-source confirmation:** carry event cause/provenance independently from cost payment; an ordinary action does not become “by an effect” just because its resulting card has a When Digivolving effect; preserve explicit accept/decline choices for optional evolution; activate the opposing effect only on the conditions in its printed trigger and with a valid source.
- **Unknowns:** this is one narrated choice, not a bot policy recommendation or proof that declining is optimal. Exact tamer text, opposing once-per-turn availability and any App Fusion provenance must be checked separately. Linking itself is not demonstrated to satisfy a “play or digivolve” trigger, and should not be conflated with either event.

## Additional source-quality limits

- “Once returned”, shifting monster names and “[music]” insertions are frequent. These cannot determine exact keyword spelling, identifiers or conditions.
- One line at 03:33–03:35 in the Reboot transcript says targets “can unsuspend”; surrounding narration appears to describe an unsuspend restriction. Pin the printed negation rather than silently correcting the caption.
- The Jupiter transcript at 16:30 calls the Option Gravity Crush, then at 16:59 calls it Gravity Quest. Exact identity must come from a list/official source. Its narration also suggests a distinct timing candidate: a delayed end-of-turn memory loss is processed before an end-of-turn Option-use effect whose permitted cost depends on the opponent's then-current memory (**16:26–17:17**). This ordering should not be assumed mandatory without a full trigger-choice reconstruction.
- No game outcome, matchup win rate, legality certification or pilot training data should be derived from these notes.
