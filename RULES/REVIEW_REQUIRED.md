# Loaded-matchup rules evidence and unresolved judge work

No rulings in this file are certified. The supplied manifest explicitly labels
every loaded card `UNVERIFIED`. Its catalog URLs and text hashes identify the
handoff's assertions; they are not independently retrieved official evidence.

## Official evidence access

The read-only request to `https://world.digimoncard.com/rule/` returned a proxy
CONNECT **403** on 2026-10-29. `world.digimoncard.com` was added to the environment
configuration draft, preserving package-manager presets. The runtime policy has
not applied this draft. Review/save the domain change in environment settings,
then publish the environment. Retry the official request after activation.
TLS verification and the configured proxy were retained. No secret is required.

## Five original reproducible halts

Exact zones, stacks, memory, statuses, once-per-turn state, pending queues, RNG,
seed, active card text, and trace tails are preserved in
`ARTIFACTS/baseline-2026-10-29/susanoomon_halt_states.json.gz`.
Match numbers below are one-based; engine indexes are one less.

| Match | Seed | Selected target | Target stack, bottom to top |
|---|---|---|---|
| 13 | 12077286973717431745 | BT26-016#1 | BT26-016#1 |
| 15 | 9160277152681596760 | BT26-029#2 | BT24-031#2, BT24-034#1, BT26-029#2 |
| 19 | 4909610865248968442 | P-213#2 | BT24-034#4, P-213#2 |
| 33 | 1839104164317051099 | P-213#1 | BT24-034#1, P-213#1 |
| 59 | 374462323305242857 | BT24-101#3 | BT24-003#2, BT24-031#4, BT25-033#2, P-213#1, BT24-101#3 |

For each state, an official rules review must identify every active replacement,
prevention, and Decode effect; its controller; legal payment/selection/decline
branches; simultaneous-trigger ordering; and whether the selected Digimon still
moves after each branch. It must distinguish exposed main text, inherited text,
and any Succession-granted effect. A card moving to security is not deletion.
Do not replace the halts with a mandatory automatic decline.

Official card references supplied by the handoff, pending retrieval:

- EX12-076: https://world.digimoncard.com/cards/?card_no=EX12-076&search=true
- P-213: https://world.digimoncard.com/cards/?card_no=P-213&search=true
- BT24-101: https://world.digimoncard.com/cards/?category=522033&search=true
- BT26-016/029/033/103: https://world.digimoncard.com/cards/?search=true&category=522038
- Comprehensive rules and official card Q&A: https://world.digimoncard.com/rule/

## Encountered optional attacking effects

The original cohort recorded **34** forced unmodeled declines: BT26-016 **12**,
EX12-065 **17**, EX12-036 **5**. These are software diagnostic observations,
not learned choices or approved strategy evidence. Remaining work includes exact
legal cost/target alternatives, nested effects, shared once-per-turn limits,
and resulting responses before any branch can support a strategic lane.

## Additional software defect found during this continuation

`FullMatch.hard_play` calls `play_with_effects`, which delegates EX12-062,
EX12-026, and BT26-013 to an opening-only `MatchZones` helper. Its documented
contract excludes stacks and unresolved protection/trigger effects. In full
games this could delete a top card without moving its sources, leave its old
stack registered, and register a self-sacrificed EX12-062 as still in play.
The old invariant counted only totals and could overlook these states.

The strict `EvidenceMatch` runner fixes singleton ghost registrations, validates
every physical copy, and refuses complex-board calls before the opening helper
mutates zones. `PREFIX_HANDLER_*` halts are conservative scope barriers, not
judge rulings that an action is ILLEGAL. Full stack-aware resolution still needs
officially supported timing/protection tests. Historical runners remain intact
solely for reproduction; use `match_evidence` for current diagnostic evidence.

## Independent review and final gate

Tests, replay, source hashes, and software `JUDGE_PATH` event names do not certify
rules. The evaluation gate requires an explicit independent review attestation
bound to all 60 exact transcript hashes and the current source/input hashes,
official source snapshots/citations, deck-restriction review, and both approved
roadmap files. Code review is not a Digimon judge review.

No rule fix is claimed for the five original halts. No strategic GREEN, YELLOW,
or RED lane is approved. UNKNOWN proposals must remain distinct from RED and
ILLEGAL. The 10,000-match runner, atomic freeze, and resume protocol remain
behind the eligibility gate; a reserved seed schedule is not a played match.
