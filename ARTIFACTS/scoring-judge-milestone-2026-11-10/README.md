# Verified scoring and judge components; integration still in progress

This checkpoint saves the finished board/tempo scorer, provisional criteria and
automated judge receipts before the remaining learner/runner work completes.
All actual matches remain paused; no fresh match, production learning update or
live-game rating has run.

The scorer measures board resources, disabled threats, completed checks and
actual memory costs/refunds. It preserves the actual signed color on procedural
changes while marking them ineligible for learning. Tempo reports per-axis leads
and contested leads. Defined weights are heuristic measurements, not winning
probabilities or approved roadmap evidence. The criteria are in the source archive.

The judge ledger verifies a matching real engine event, semantic action args,
Bot C's predecessor anchor, current snapshot, physical conservation and official
source/binding hashes. It accurately labels these automated checks experimental;
it does not claim independent semantic or full-game certification. Software gaps
are rejected without automatically being called illegal or red.

59 focused checks passed: 21 scorer, 8 judge and 30 Bot C tests. See
verification.json for the actual command, timing and component source hashes.
component-source.tar.gz contains the exact five verified files. Existing engine
and player policy files are unchanged. The learner and fresh-game runner are
still being implemented and are not certified by this component checkpoint.
