# Selected EX13 engine intake

This is an experimental input/evidence snapshot, not match results or a freeze.

- Queue order 1: UlforceVeedramon/Federico Nine (DigiLab 123129), Gallantmon/RTA
  (124303). Both exact source pages supplied 50 main cards and 4 Digi-Eggs.
- The queue preserves the original random seed and all 1,431 unique unordered
  entry pairs. Every entry occurs 53 times in the full queue; same-archetype
  variants can meet, an entry never meets itself. This is queue ordering, not
  a frozen gameplay schedule or a claim that all queued pairs were evaluated.
- Source-index retrieval statuses are the initial workbook-wide fetch. The
  first Gallantmon URL was initially unavailable and subsequently retrieved;
  its actual source bytes are preserved under the selected rules snapshot.
- `context.json` binds the selected compositions, official printed definitions
  and provisional rules selections. `deck-A.json`/`deck-B.json` retain source
  and composition hashes. A retrieved source is not a judge certificate.
- Official card pages, Q&A, rules, restrictions, errata and three inspected
  official images are under `RULES/matchups/123129-vs-124303/`.
- LM-027, LM-028 and LM-034 have conflicting HTML type labels; their official
  images visibly say OPTION. Both assertions, image hashes and the selected
  image value are retained for independent review.
- Printed evolution candidates cover the selected normal and special syntax;
  they do not decide live-action legality, restrictions, payment or triggers.
- The orientation pack implements only closed-scenario EX13-023 processing.
  It refuses unimplemented reactions and DP/status dependencies. It is
  EXPERIMENTAL_UNREVIEWED and requires an explicit experimental flag.

From SOURCE, inspect current readiness without generating games:

```sh
python -m matchup_readiness
```

Expected: exit 2/BLOCKED. Use `--out` with a NEW filename to save the full
inventory. It lists remaining mechanics and review requirements. It is not the
legacy `evaluation_gate`, which remains tied to the old loaded-pair engine.

Current played/certified full matches: 0. Approved strategic lanes: 0.
Final evaluation matches: 0/10,000 for this pairing. Scenarios count as zero.
