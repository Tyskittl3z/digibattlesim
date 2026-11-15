# Fresh learning integration checkpoint — 2026-11-10

This is setup verification using private fixtures. Actual matches remain
**PAUSED_BEFORE_FIRST_MATCH**. No production campaign, opening deal, learning
update, live rating or accepted match was produced. The historical mixed-policy
164-command game is unchanged and excluded from fresh learning.

The fresh runner connects aggressive Bot A, defensive Bot B, Bot C's redacted
views, board-impact colors, accurately labelled automated judge receipts and
persistent learning. No random reference player supplies these bots' choices.
Learning freezes within a game and updates explicitly after eligible completion.

## Evidence

- `verification.json`: final 155 focused checks, review and scope.
- `private-setup-proof.json`: separate five-command private integration proof.
- `private-opening-fixture.json.gz`: three private opening commands.
- `private-resumed-fixture.json.gz`: unchanged prefix plus two automatic phase
  commands. These are test fixtures, not campaign games or learned evidence.
- `private-fixture-replay.json`: exact replay of both records without player
  reselection; policy RNG and saved choices preserved.
- `verify-private-setup.py`: the fixture producer, using exclusive output files.
  It refuses to overwrite evidence. To reproduce, copy the script into a new
  dated artifact directory at the same depth in a matching source checkout.
- `criteria-manifest.json`: pinned provisional scoring criteria/source identity.
- `source-manifest.json` and `source-checkpoint.tar.gz`: all 112 Python source
  files, with exact byte hashes, including the final 32-test learner.
- `pause-control.json`: current disabled production-run control record.

The private proof also rejects an unfinished-game learning commit, verifies the
model is unchanged, and confirms the historical record and source bytes are
unchanged. Procedural steps retain measured board colors but receive no learning
credit. Unit tests separately exercise completed-game updates using synthetic
private data; those updates are not production training.

## Limits

Resume requires the **same software build**. Source repairs currently invalidate
the record's pins; verified cross-build migration remains future work. Preserve
the original seed, state and selected action when adding that capability.
Judge receipts are experimental automated checks, without independent semantic
or full-game certification. Colors are observed board-effect heuristics, not
win probabilities or approved roadmaps. Selected-card coverage, 60 valid matches,
roadmap readiness, final freeze and 10,000 matches remain incomplete.
