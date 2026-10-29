# Frozen evaluation runner verification — 2026-10-29

The frozen runner is implemented for the exact loaded Jupitermon versus
Amaterasumon/Toho matchup. This is software verification, not Digimon rules
certification and not a gameplay result. The real final evaluation remains
**0/10,000**, with no win rate available.

## Required order of work

1. Produce at least **60 valid full fact-finding matches**, balanced 30/30 by
   starting deck and independently reviewed. HALTs and targeted scenarios receive
   zero full-match credit.
2. Use those exact traces to classify legal routes as **GREEN (best), YELLOW
   (medium), or RED (worst)** under the preregistered comparison and uncertainty
   criteria. Rules legality and strategy effectiveness require separate reviews.
3. Freeze the decks, rules/format snapshot, pilots, criteria, approved roadmaps
   and a disjoint balanced schedule.
4. Play 10,000 frozen matches, with 5,000 starts per deck and no learning or
   replacement seeds.

The current diagnostic cohort contains 60 attempts and a 30/30 start split, but
only 29 software completions and 31 HALTs. It has **0 independently judge-valid
matches**. Current roadmaps therefore remain 609 UNKNOWN groups for A and 427
UNKNOWN groups for B, with no GREEN/YELLOW/RED approvals.

## Runner behavior verified

- Freeze creation re-runs the live eligibility gate, binds all seven frozen
  components and refuses a stale preparation. The preparation's cohort and
  provenance identities must match the live gate, and every current fact-finding
  seed is checked against the final schedule.
- The schedule must contain exactly 10,000 unique deterministic seeds with 5,000
  starts per seat. A changed seed, duplicate, imbalance or compressed-file hash
  mismatch fails closed.
- Each completed match is written as deterministic gzip evidence. A canonical
  receipt binds the record and compressed-file hashes; every receipt advances a
  cumulative SHA-256 checkpoint chain. Record plus receipt tampering is rejected
  before another match can run and during finalization.
- Infrastructure interruption replays the same schedule position and requires an
  identical record. Atomic writes use unique temporary files and remove a failed
  temporary, so an interrupted replace cannot permanently block resume.
- Rules and integrity HALTs are retained as diagnostic envelopes with the exact
  scheduled match, raw attempt and validation error. A HALT written before an
  interrupted checkpoint is recovered and blocks resume; it is never skipped or
  replaced.
- Finalization requires exactly 10,000 record/receipt pairs, no HALT files, the
  original frozen hashes and a matching checkpoint chain. Existing final files
  are compared byte for byte and are never silently republished from changed
  evidence.

The two pilots remain Bot A/Jupitermon and Bot B/Amaterasumon-Toho. The audit
layers are **Justitia** for runtime integrity, **Dike** for independent rules
review and **Týr** for final evidence audit.

## Review findings and fix pass

The fresh code review reported no Critical findings and five Important findings.
All five received focused failing regressions before the fixes:

| Finding | Verified repair |
|---|---|
| Credited hashes were not durably bound; changed evidence could be summarized again | Per-record receipts, a cumulative checkpoint hash chain and immutable final-file comparison now reject changed record/receipt/final bytes. |
| A HALT written before checkpoint interruption could be ignored | Resume recovers the orphan HALT at the exact current seed and writes a blocking checkpoint before any runner call. |
| A fixed `.tmp` path could block every later resume | Atomic writes use a unique temporary and clean it after failure. |
| Physical-integrity failures could be rejected before their trace was saved | Integrity and judge-HALT attempts are saved as blocking diagnostic envelopes without match credit. |
| A stale preparation was not bound to an expanded fact-finding cohort | Freeze creation binds preparation to the live cohort/provenance and rejects overlap with every current cohort seed. |

The review's Minor app finding is retained as a known presentation limitation:
an arbitrary unsupported deck comparison still carries the supported reference
Bot A/B roster in its machine-readable simulation block. It receives no support
status or results, but the roster should later be labeled explicitly as reference
scope or omitted for unsupported inputs.

Official card rulings, reviewer qualifications and strategy effectiveness were
outside code review and remain external evidence gates. Protection against a
coordinated rewrite of every local artifact would require a trusted signature or
external append-only anchor; none was specified. Concurrent writers to one run
directory are also outside the single-runner contract.

## Executed verification

| Check | Actual result |
|---|---:|
| Frozen-runner focused Python tests | 20 passed |
| Full Python suite | 148 passed |
| Node parser/comparison/report tests | 9 passed |
| Built single-file app test | 1 passed |
| Chromium interaction/download/mobile tests | 6 passed |
| Synthetic full runner exercise | 10,000 records + 10,000 receipts; completed |

The synthetic full-path exercise used lightweight fixture records and patched
fixture validation. It verified the entire 10,000-position schedule, 5,000/5,000
start balance, receipt/checkpoint chain, final aggregation, idempotent completed
resume and rejection of an altered `FINAL_RESULTS.json`. Its artificial 6,000/4,000
winner split is test data and is not a matchup result.

A real freeze CLI invocation exited **2**, reported the current blockers and
created no run directory. The official site request to
`https://world.digimoncard.com/faq/` still returned proxy CONNECT **403** after
the environment restart.

## Remaining gates

The environment configuration must publish access to `world.digimoncard.com`,
and the intended format, region and language must be selected rather than
inferred. After retrieving and hashing the official rules/card Q&A, the remaining
interactions and optional choices can be implemented and the full fact-finding
cohort rerun from zero. Dike must then review every complete match, the separate
strategy review must approve evidence-backed GREEN/YELLOW/RED routes, and only
then can a new preparation be frozen for the real 10,000-match run.
