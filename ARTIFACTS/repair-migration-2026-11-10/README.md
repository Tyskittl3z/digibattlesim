# Explicit repair migration — private setup verification

**Verified:** 173 focused tests passed in 73.877 seconds. Independent review and
artifact audit found no remaining publication blockers after the cached-code
correction. The separate durable private proof passed in 4.920 seconds. Both
builds and migrated replay/resume load source directly in isolated workers.

These artifacts concern saved-game integrity across code repairs. They do not
start a production campaign or lift the match pause. Actual fresh matches,
production learning/ratings, accepted fact-finding credit and final evaluation
credit remain zero.

The original private build comes from the published integration source archive,
with one deliberate temporary engine gap in `match_preparation._redraw`. It
stops after opening preparation and an already selected redraw. The gap exists
only in the archived private fixture sources, never in live SOURCE. The repaired
build must reproduce the successful prefix with the same seed, complete state,
RNG, views and saved decisions before it can return a migrated stopped record.

`verify-private-repair.py` is the proof producer. It uses exclusive output files
and cannot overwrite evidence. Before executing it on frozen, reviewed source,
pin the exact three-file map in `approved-private-source-changes.json`: private
match-preparation repair, recognized runner bootstrap and new migration module.
The producer asserts that the observed differences match this separate map.
It verifies migration without a learning-player actor or policy choice, then
retries only the already selected action in a private fixture with choice
disabled. Pure identity derivation may construct a named-bot manifest helper.

The producer archives original and current source bytes, stopped/migrated/retried
records, and replay/proof receipts. It confirms the parent, production historical
record and learning model remain unchanged. Judge receipts remain experimental
automated checks, without independent semantic or full-game certification.

The opening/phase proof exercises changed execution identities and saved-action
retry. Handler-module binding/receipt/observation-chain propagation is a separate
focused-test obligation, covered by the 18 migration tests; this opening-only
fixture does not itself establish it.

## Saved evidence

- `verification.json`, `private-repair-proof.json`, `independent-review.md`:
  focused check counts, exact private proof and review closure.
- `approved-private-source-changes.json`: separately pinned three-file map.
- `private-original-gap-source.tar.gz` and `original-source-manifest.json`:
  112 original Python files, exactly one private gap relative to the previous
  authenticated source archive. Required context/rules/source assets agree with
  `dependency-manifest.json` (68 files).
- `source-checkpoint.tar.gz` and `source-manifest.json`: all 114 current Python
  files; byte hashes match the final focused run and independent review.
- `private-original-stopped.json.gz`: immutable original stopped fixture.
- `private-migrated-stopped.json.gz`: same physical/RNG checkpoint under current
  source, with full embedded parent and hashed repair lineage.
- `private-retried-selection.json.gz`: one resolved retry of that same selection.
- `replay.json`: exact migrated/retried replay receipts.
- `pause-control.json`: current disabled production-run control.

The proof uses child-enforced actor/choice prohibitions. Parent-process mocks do
not control those subprocesses. Runtime code/hash consistency is a software
check; external signatures and independent card-rules certification are absent.
