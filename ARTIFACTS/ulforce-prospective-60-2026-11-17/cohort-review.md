# Ulforce 60-game software cohort review

Reviewed 2026-11-21. Scope: the selected deck 123129 versus deck 122110 matchup, under English-version worldwide rules. This is a review of the saved software records, not an independent rules certification or a result for the 54-deck workbook.

## What the records establish

The 60 scheduled seeds each have a terminal game record, 30 starts by each seat. Bot A won 26 games and Bot B won 34. All 60 terminal reasons were successful direct attacks. The records contain 10,910 judge-accepted commands, 10,910 Bot C observations, and 78 replay receipts with `exact_match: true`. The final record for every game matches its scheduled seed and first player. Turns ranged from 6 to 18 (mean 10.07).

The command-boundary board-impact labels total 4,080 GREEN, 5,391 YELLOW, and 1,439 RED. Of these, the commands marked learning-eligible are:

| Seat | GREEN | YELLOW | RED |
| --- | ---: | ---: | ---: |
| A | 1,191 | 367 | 691 |
| B | 1,173 | 452 | 681 |

These colors measure the immediate observed public board change under `RULES/learning-2026-11-10/INTERACTION_CRITERIA.json`. They are not best/medium/worst strategy approvals. For example, 544 attack declarations were RED at the declaration boundary, while the cohort later recorded 532 successful security checks. Declaring an attack suspends its attacker before the check resolves; the declaration's RED label cannot by itself say whether the full attack was a poor choice. The cohort ran through five engine-source manifests because four encountered judge halts required source repairs and exact prefix migrations.

## Limits that affect the next run

- Both pilot manifests say `BOARD_AND_CARD_TEXT` and use the same `BOARD_TEXT_HISTORY` policy source. The promised aggressive Bot A versus defensive Bot B distinction is not present in this cohort. Different deck, seat, hand and seed inputs do not establish different policy styles.
- The board-text policy ranks available legal candidates by its live heuristic first. Prior history breaks ties in that live score. The saved model therefore cannot change a strict live ranking, even after 60 games. The cohort is evidence of sequential history handoff, but only limited adaptation from that history.
- The rules lock is `UNVERIFIED`: 23 official-document entries lack an effective-date pin, and its separate review is missing. Saved judge receipts and replay show internal software consistency; they do not independently certify every play against Bandai rules and rulings.
- `ROADMAPS/A.json` and `ROADMAPS/B.json` are candidates for a different Jupitermon versus Amaterasumon matchup. They must not be applied to these Ulforce games. There is no approved green/yellow/red Ulforce strategy roadmap or frozen 10,000-game evaluation.
- The full test discovery run before the final source repair had 736 tests with 19 failures and 16 errors. Focused return tests and exact replay passed after the repairs, but full-suite health is still unresolved.

## Next gate

First make the A and B policy styles explicit and decide how a completed attack's later board effects should inform learning. Then repair or classify the full-suite failures, finish the official-source date and separate rules review, and run a **fresh** 60-game cohort on one fixed engine and the intended two policies. Review conditional alternatives before approving strategic roadmaps. Only after that should a frozen, learning-disabled 10,000-game evaluation be considered.

The saved campaign status correctly remains at `accepted_fact_finding_credit: 0` and `final_evaluation_credit: 0`. No result in this note changes that status.

## Audit basis

Counts above were recomputed from each `game-0000` through `game-0059` final `segment-*.json.gz`, its command ratings, Bot C observations, scheduled seed/first-player entry in `campaign-lock.json`, and every `replay-*.json` receipt. Each final command's `judge.accepted` and status were checked. See each game's `actions.csv`, `report.md`, `commit.json`, and final segment for the underlying events and state.
