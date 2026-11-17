# Ulforce mirror: encounter and rules review ledger

Matchup: Federico Nine 123129 (A) vs Bern 122110 (B). The archived
`board-text-60-piercing-corrected-v2-2026-11-15` campaign is diagnostic
software evidence, not a rules-certified fact-finding cohort.

`build_trace_index.py` regenerates the two machine-readable files here from
the 60 terminal records. `trace-index.json` lists every game seed, terminal
record hash, encountered effect ID, command type, choice type, and cited
official source hash. `choice-references.json.gz` holds the individual effect,
choice, and canceled pending-effect references, including action index and
automated judge receipt hash.
The index does not contain a rules verdict or strategic rating.

## First pass

- 60 terminal software records, 10,047 accepted commands, 3,044 effect
  resolutions across 45 effect IDs, 9,462 recorded choices, and 37 canceled
  pending effects were indexed. Cancellations include the reason and action.
- Every cited source hash matched a local cached official source file and an
  official `digimoncard.com` URL. These are 22 card-page files and one
  Comprehensive Rules PDF. This checks citation identity, not whether the
  judge applied the source correctly. All 3,044 bindings are marked
  `EXPERIMENTAL_UNREVIEWED`.
- The 9,462 choices include 560 Counter windows with one candidate each,
  47 Block windows with multiple candidates, 1,617 main-action choices with
  multiple candidates, and 1,702 pending-effect choices with multiple
  candidates. Candidate generation and every selected branch still need
  semantic review. The old `RULES/INTERACTION_COVERAGE.json` expects
  `BOT_DECISION` and `JUDGE_PATH` events; these records contain neither.
- Official Comprehensive Rules v4.3 section 16-7-4 requires BT20-102
  Piercing to process before the end of the attack. Archived games 24 and 55
  processed it after `END_ATTACK`. See the campaign's
  `RULES_REVIEW_FINDING.md` for seeds, action numbers and record hashes. A
  focused scheduler regression test now exercises the required ordering and
  rejects a closed-attack Piercing pending effect.
- Comprehensive Rules v4.3 sections 15-6-3 and 15-8-3-9 bar activation when
  an effect's only printed processing condition is false. The archived records
  contain 58 BT22-023 inherited unsuspends without a blue Tamer, 8 BT22-022
  Tamer-play activations with too many Tamers, 25 BT22-085 start-turn memory
  activations above 2 memory, and 42 EX13-069 start-main memory activations
  without the required Digimon, plus 12 BT12-029 return activations without
  its printed blue Tamer or [UlforceVeedramon] condition. See
  `CONDITION_REVIEW_FINDING.md` in the campaign folder. Focused tests now
  require cancellation before activation.
- An ordinary or deferred attack can contain a child trigger whose processing
  condition is false. The engine now logs a settlement of that child before
  allowing `END_ATTACK`; a deferred attack's outer pending effect remains
  deferred. Focused tests cover both paths.
- Spot reviews of the other encountered effect IDs found no additional
  confirmed mismatch in sampled paths; they do not certify all resolutions.
  The paid branch of BT22-085 attack Jamming and the decline branches of
  EX13-017 and BT22-022 return replacements were not taken in this archive.

## Eligibility still open

The rules lock is `UNVERIFIED`. The rules and each encountered effect/choice
path require semantic review against the pinned English worldwide card text,
Comprehensive Rules, relevant Q&A, errata and restrictions. The 45 effect IDs
in `trace-index.json` form the encountered-effect checklist; the compressed
references provide examples for each. Reviewer findings should identify a
specific action, source, rule, legal alternatives, and any correction. Changed
engine behavior requires a new, balanced, exact-replayed 60-game cohort under
the reviewed snapshot. Historical records and seeds remain preserved. Do not
promote this archive to certified matches or approve roadmaps from its colors.
The standalone `ContextRuntime.dispatch` scenario API also accepts direct
EX13-023 orientation activation without a pending trigger in a gameplay phase;
the match runners use pending activation, but this API path needs a separate
guard before claiming the mechanic pack broadly verified.

## 2026-11-17 mechanic and source checkpoint

- EX13-023 Q7268 and Comprehensive Rules v4.3 section 7-3 support its
  Assembly -5 play from one eligible Lv.3, Lv.4, and Lv.5 card in the
  controller's trash. The new action records the three physical keys in
  stack order and pays 7 memory. A focused scenario verifies the resulting
  On Play triggers. Archived game 0 action 96 had a reachable Assembly
  choice, so earlier archives cannot count as complete choice inventories.
- BT20-102 Q4725 expressly requires the Then return even when the preceding
  Omnimon/X Antibody condition is false. A current-state scenario verifies
  that return; the old test asserting an empty effect list was removed.
  The true board-wipe condition still halts before payment until reviewed.
- BT20-102 Raid, Comprehensive Rules v4.3 section 16-23, is now an explicit
  attack-time choice. A focused scenario switches the attack to the current
  highest-DP unsuspended opposing Digimon; another records an explicit
  decline. Historical replay fixtures expecting no Raid pending effect are
  stale and were replaced by current-state scenarios.
- The matchup-scoped `RULES_LOCK.json` pins 22 official card pages, the
  v4.3 Comprehensive Rules PDF, and current official restrictions and
  errata HTML. The restrictions page has SHA-256
  `89a71be061a96cf6929cb8b83af916ea7da3e4ba73fe817e5f4b325a9bf886a1`;
  the errata page has SHA-256
  `283a2d4e1f3b91c7ab9d93eb9823a38524a3a755706d655b5ae0d3849e904ce9`.
  No loaded card number appears in either page. The official rules index
  points to `general_rule.pdf?20260918`, whose cached bytes have SHA-256
  `a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271`.
  The index itself has SHA-256
  `7c9b088ab92babdc87a38170f99be6f73e9e82fc5bf2299a843e8bf572a8475b`.
  Official effective dates for the card pages and Comprehensive Rules were
  not found, and no separate complete snapshot review is recorded. The
  lock validator reports `UNVERIFIED` with those two blockers. This
  checkpoint credits zero new rules-certified matches.
- A noncredit smoke replay with the new Assembly action halted at action 97,
  seed `16664364153905075627`, before selecting a main action. The learning
  bot's strict candidate grammar rejected `ASSEMBLY_PLAY` with
  `LEARNING_ACTION_FIELDS`. Its archived record SHA-256 is
  `5a4a1db02f6d9b31f1cc42c17e4cc8536363e34bedf0626c4a86aa63b0dfa57f`.
  A focused bot-to-judge scenario exposed and fixed that pipeline gap.
- A new smoke archive under the changed source snapshot replayed the same
  scheduled seed exactly: 155 accepted actions and 155 Bot C observations,
  including two Assembly plays, ending with Bot B as winner. Its record
  SHA-256 is
  `9cab2c93b926b6078a46892fc37331aabb3e338913d9b5d718e9a81f72d910c8`.
  Both seats used `BOARD_AND_CARD_TEXT` with random exploration off. This is
  one experimental software game and contributes zero to the verified 60.
- Gameplay-phase calls to `ContextRuntime.dispatch` now require a pending
  trigger. The direct scenario API remains available in `SCENARIO`; a focused
  test rejects gameplay activation without a pending effect. Security text
  can no longer be dispatched from a battle-area card without its checked
  security window. A timing scenario now queues the printed effect instead
  of invoking it directly in gameplay. An old BT11-112 archived replay test
  was redundant with the current security-play scenario and was removed
  because its old pending IDs cannot replay under the repaired engine.
- The empty prospective 60-game campaign driver pins the canonical matchup
  rules-lock hash, current source file hashes, scoring criteria and
  board-text policy source before game zero. It is still preparation, not
  a run. It refuses to start game zero while the rules lock is `UNVERIFIED`.
  The lock currently carries zero accepted credit.
- Independent code review identified two provenance failures: a card document
  could borrow another card's valid official page, and a next-game handoff
  could accept a prior receipt with the wrong record hash. The validator now
  compares each card document's URL, path and SHA-256 to its exact loaded
  card definition. The prospective driver binds each prior terminal segment
  to its saved receipt, game ID, schedule entry and context before loading
  the next game's model. Synthetic tampering tests cover both failures.
- A focused current-state scenario also follows BT20-102 Raid through battle
  deletion, mandatory Piercing, a Security check and attack end in order.
- BT20-102's *true* first condition remains unsupported in the generic
  engine. The earlier claim that BT12-029 reaches it was incorrect:
  Comprehensive Rules v4.3 sections 2-3-1-2 and 2-3-1-3 distinguish the
  exact bracketed name `[X Antibody]` from "with [X Antibody] in its name."
  BT12-029 is named `UlforceVeedramon (X Antibody)`, so evolving Bot B's
  single BT20-102 onto it leaves the condition false; the mandatory Then
  return still resolves (Q4725). Neither exact loaded deck has a source card
  named `Omnimon` or `X Antibody`. The only card with `Omnimon` in its longer
  name is Bot B's single BT20-102, which cannot be beneath itself. A true
  condition in a future matchup still halts before payment pending survivor,
  simultaneous-deletion, leave/replacement and Q6018 implementation. This
  branch does not block the selected pair's conditional path.
