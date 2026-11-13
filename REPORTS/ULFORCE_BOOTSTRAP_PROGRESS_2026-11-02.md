# Ulforce bootstrap checkpoint — November 2, 2026

The user delegated the starting matchup. Two distinct imported Ulforce lists
(123129/Federico Nine vs122110/Bern) narrow the implementation surface to22
official-source-pinned cards. Both list counts are50 main+4 eggs; their different
composition hashes and complete card definitions are saved in
`ARTIFACTS/ulforce-bootstrap-2026-11-02/`. The original queue is byte-unchanged
(SHA256 `c9baefb35eda2a8940938a8fb3198aee97be4ca72e8a304d00740e0bb89e2219`).

## Implemented

- A shared capability resolver pins the exact context and ordered source IDs
  separately, then checks its saved lock. It supports both original and mirror
  basic actions without authorizing arbitrary imported effects.
- Diagnostic input selection, saved provenance, fresh context-bound pilots and
  seeds, contained paths, explicit CLI selection and exact-context replay.
- Replay and cohort inputs are checked against their expected identity and byte
  hash before creating the runtime. Parsing uses exactly the bytes being hashed.
- Changed context during a cohort cannot produce a mixed summary; originals and
  replay failure traces are preserved before errors are surfaced.

## Actual verification

Original baseline:312 tests passed. Current full suite: **335 passed in57.555s**.
Focused integration before the replay hardening:71 tests passed. An independent
review found a preflight/rerun race that could execute a different approved
context before detecting a mismatch. Two regressions failed first, reproducing
that swap and a separate hash/parse double-read mismatch; both pass after the
single-byte-snapshot and expected-context checks. No other material review
findings were reported. This is software review, not card-rules certification.

New context diagnostic02 actually ran60 attempts,30 starts each. All60 records
replay exactly and all60 stop explicitly. Grouped first stops:

| Stop | Attempts |
|---|---:|
| Actual On Play not implemented |42|
| Option use not implemented |8|
| Battle-area evolution not implemented |7|
| Stacked battlefield outside existing scope |2|
| Security card outside existing scope |1|

The security stop is EX13-023. The existing attack module requires a narrow
blank-main whitelist for a plain security Digimon. Review this as a possible
overbroad code guard: ordinary main abilities do not automatically activate in
security. Confirm the exact applicable security wording and shared procedures
before extending support; never suppress a genuine Security effect.

Version01 remains preserved at commit43eace1. Diagnostic02 follows the replay
fix, so its runner hash/pilot identities differ; no aggregate causal comparison
is claimed. The new context reuses no old matchup pilots, roadmaps or results.

**Zero** software-terminal full games, valid fact-finding games, approved lanes,
or final matches exist for this mirror. The next work is the encountered On Play,
Option/evolution/stack and security processing, with printed-trigger tests and
same-seed reruns. A list of79 printed units is an inventory, not an interaction
coverage certificate or a time estimate.
