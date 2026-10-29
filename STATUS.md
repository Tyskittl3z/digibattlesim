# Verified handoff status

**Snapshot:** JUPITERMON_TOHO_ATTACK_AUDIT_2026-10-19.zip, imported without older-matchup artifacts.

| Metric | Reported in supplied snapshot |
|---|---:|
| Seeded match attempts | 60 |
| A-first / B-first | 30 / 30 |
| Software-completed games | 55 |
| HALT games | 5 |
| Independently judge-certified matches | 0 |
| Approved strategic play lanes | 0 |
| Final evaluation | 0 / 10,000 |
| Reported unit tests | 78 / 78 |

**Revalidated for this Codex handoff:** The test command ran 78 tests, all passed. The 60-seed batch runner reproduced 55 software completions, five HALTs, and a 30/30 starting-player split.

**Outstanding HALT reasons from supplied report:**
- 1 × `SUSANOOMON_TARGET_LEAVE_REPLACEMENT_UNVERIFIED`
- 1 × `SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: BT26-029`
- 2 × `SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: P-213`
- 1 × `SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: BT24-101`

Historical `MATCH_LOGS` contain software audit events, not certified final results. Source version must be part of every subsequent report.

Next goal: complete and verify the five unresolved loaded-deck interactions, then rerun all 60 full fact-finding games.
