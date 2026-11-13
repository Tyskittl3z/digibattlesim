# Explicit engine repair migration

## Intent and authorization

Continue the user's saved-game integrity work: a code repair must preserve the
same game, seed, complete state/RNG and previously selected actions. This is
preparation only. The active instruction to continue concerns this setup step;
actual matches and both cohorts remain paused. The user has delegated routine
implementation choices and asked for continued publication, so no technical
design-choice or publishing approval is requested again.

## Approach

Keep the existing Python engine, bots and strict ordinary replay. A separate
explicit operation verifies the original build, replays the unchanged successful
prefix under the repaired build, and returns a new resumable record with an
embedded immutable parent and a hashed lineage receipt. It never retries the
failed action or asks a player to choose. This is the implementation choice.
Both original and repaired execution must load verified Python source directly
in isolated workers, bypassing cached bytecode. Replay/resume of a migrated
record uses the same verified-source path; ordinary nonmigrated behavior stays
unchanged. The model is serialized frozen and remains unchanged in the caller.

Simply replacing the source manifest would discard the proof that earlier
actions still produce the same game. Restarting with a new seed or reselecting
an action would violate the user's history-preservation requirement. Neither
alternative is supported. An earlier-result change requires separate affected
evidence repair; it cannot pass this exact-prefix migration.

## Public API and scope

`fresh_repair_migration.migrate_repaired_game(record, *, root,
original_source_root, approved_changes, repair_note)` returns a new standard
fresh-learning game record. `approved_changes` is an exact developer-reviewed
map of source basename to `{before: hash_or_null, after: hash_or_null}`;
unlisted changes fail. `verify_repair_lineage(record, root)` validates saved
lineage during ordinary replay/resume. No automatic file writes, campaigns,
matches or training updates occur.

Accept only nonterminal PAUSED, HALT or unchanged-state DIAGNOSTIC_SOFTWARE_ERROR
records. Reject completed games, post-commit audit failures, malformed failure
positions and state mutation at the failed boundary. Preserve literal saved
commands, including UNKNOWN aliases; do not invent a new decision or remap them.

## Verification requirements

1. Check the original record hash, original on-disk Python source map and exact
   dependencies. Run its original `replay_game` in an isolated Python subprocess,
   importing only the verified original SOURCE directory. The original build
   must successfully validate the original record. Never invoke player choice.
   Apply the same source-only isolation to repaired-build execution: hashing
   disk files does not prove which cached code the current interpreter loaded.
   Enforce no learning-actor construction/choice inside migration/replay workers,
   rather than treating a parent-process mock as a worker guard.
2. Require identical context bytes, all RULES file bytes (including official
   sources/index/lock and scoring criteria), campaign, schedule, index, seed,
   first seat, player identities, learning model, criterion, judge, scorer and
   tracker. Snapshot source/dependency bytes before and after verification.
3. Allow only explicit engine changes. Protect policy/learning/scorer/tracker/
   judge/context/seed-schedule infrastructure. A narrowly recognized bootstrap
   upgrade may add this migration module and change the runner from published
   dd5cd17e718097c69e391c09e9b9d9c7c62b8021cc261b696f57543320889718
   to the current lineage-aware runner; future ordinary engine repairs may not
   alter either framework module. All changes still require exact reviewed hashes.
4. Replay successful commands with their saved actor/arguments. Compare exact
   results, full physical state, engine RNG, views, decisions and policy RNG,
   ratings and ordered events. Normalize only top-level snapshot/event
   execution_id, the documented judge binding handler-module source stamp, and
   dependent receipt/observation chain hashes. Never recursively strip hashes or
   default missing state fields. All remaining binding/evidence data must agree.
5. Regenerate current-build snapshots, judge receipts and tracker observations;
   require current automated guards to accept every replayed success. Preserve
   all original evidence inside the parent. The final physical state and RNG
   must match exactly before returning. A failed command remains unexecuted,
   UNRATED and associated with its original-build evidence/selected arguments.
6. Embed parent, original whole-record/record-field hashes, old/new source maps,
   dependency hashes, exact approved differences, original replay receipt,
   execution IDs, successful-prefix count, failed-selection digest, repair note,
   checkpoint/RNG digests and explicit zero-credit experimental certification.
   Verify this lineage and its relationship to a continued prefix on every
   replay/resume. Preserve lineage through subsequent same-build continuations;
   support a second engine-only repair without losing either parent.

## Tests and delivery

Use actual different on-disk source builds in private fixtures, including a
temporary old-only engine gap and its repair. Test migration without learning
actor construction or policy choice, exact one-command retry of saved selection, retained RNG,
pending choice values, repeated repairs, unchanged parent bytes/model and
rejection of changed earlier state/results, protected sources, rules, context,
unapproved diffs, malformed/tampered lineage and completed/audit-failure records.
Mocked runtime availability alone cannot establish cross-build support. Include
timestamp-valid stale bytecode in the repaired build, and prove it cannot hide
a changed earlier result during migration or migrated replay/resume. The
existing pure manifest helper may construct NamedPlayerBot solely to derive its
identity; that is not a player decision or LearningPlayerBot actor invocation.

Publish focused test counts, exact source archive and private replay evidence.
These are software checks with experimental automated judge receipts, not
independent semantic certification or valid-match/roadmap/final evidence.
