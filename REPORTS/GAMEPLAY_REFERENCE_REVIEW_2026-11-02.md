# Supplied gameplay references — 2026-11-02

Eight uploaded timestamped transcripts are indexed as **reference material**,
with original byte hashes and 5,029 timestamp blocks. The accessible 17-minute
SeitenGokuumon / Gammamon video was inspected through timestamped frame samples
covering the opening, middle and late portions. This was not a continuous,
action-by-action reconstruction. Its 240p physical card faces generally cannot
establish source order, memory, complete hidden zones or every choice.

Both user-supplied reference lists contain 50 main cards and four listed eggs.
The exact names and IDs are preserved without replacing the selected engine
pair or asserting tournament legality. Canonical spellings in official sources
take precedence over recognition errors in captions.

Source index and timestamp blocks: `ARTIFACTS/video-reference-2026-11-02/`.
Narrator requests to subscribe, visit stores or follow links are media content,
not instructions from the user.

## Directly useful for the selected engine pairing

The UlforceVeedramon / Gallantmon transcript describes overlapping mechanics,
but its Gallantmon list includes cards absent from the exact selected B list.
It therefore supplies adapted regression scenarios, not an exact replay or
strategy data for the selected pairing. Ten candidate sequences are recorded
in `ulforce-gallant-review.md` inside the artifact directory. Sixteen referenced
official card-source hashes were checked against the current context.

| Timestamp | Concrete engine check | Printed-source support |
|---|---|---|
| 00:08–00:59; later 02:49–02:59 and 04:21–04:35 | Training reveals, explicit selections, bottom order and a later Delay evolution; reduction does not waive evolution requirements | LM-061, LM-058, P-104; Q4192/Q4195 |
| 02:59–03:53 | Tamer plays, suspension/unsuspension and evolution during an attack finish before Counter; evolution preserves the attack | EX13-019/002/069/022, BT11-112; comprehensive rules 8-1 and 11-1-4. Q7437/Q7439 specifically cover Rina's payment and separate reductions |
| 04:35–05:32 | If Evade prevents the deletion required to pay Gallantmon's leave-prevention condition, Gallantmon still leaves | EX13-015; Q7247 |
| 07:45–09:07 | Resolve separately pending On Play effects in controller-chosen order; Rina activating a When Digivolving effect does not itself digivolve or draw | EX13-023, BT11-112; Q7266/Q7200/Q7199 |
| 09:24–09:45 | A prevented deletion can lead to Gallantmon's security-trash fallback; then resolve eligible suspension reactions | EX13-015; Q7249 |
| 09:58–11:15 | Track Gallantmon X's separate effects and orientation-dependent DP protection; zero-DP rule processing precedes a pending unsuspend | EX8-073, EX13-023; Q7269 directly addresses zero DP before unsuspension. Q3982/Q3983 give general protection-applicability examples |

These sources support specific expected behavior. Exact fixtures must still
name physical cards, source instances, memory, previously used limits and
controller choices. Missing footage details are supplied only as explicitly
synthetic scenario inputs, never invented historical observations.

## Other references and shared engine behavior

The SeitenGokuumon / Gammamon frame review and transcript expose cost modifiers,
DigiXros/Assembly material movement, attack-time evolution, acquired effects,
token play, face-up security, source-area play, deletion reactions and nested
Delay processing. Early source checks are recorded in `early-source-checks.md`;
middle and late observations distinguish visible overlays from narration.

The other six transcripts supply examples of:

- A redirected attack target participating in Blast DNA evolution, plus separate
  duration and immunity boundaries (Jesmon / Alphamon).
- Pending end-of-turn work across nested Option and play effects, and Counter
  source removal (GraceNovamon / Ceresmon–Bacchusmon).
- DNA-specific clauses and Execute deletion with Decode (Junomon /
  Neptunemon–Venusmon).
- Further security, breeding-area, movement, link and attack-target cases in
  the additional Jupiter, Abbadomon and Rebootmon references.

Those cases are candidate fixtures for reusable procedures. They do not expand
the selected-pair card pack or transfer another deck's pilot or roadmap.
Caption arithmetic and exact names require printed-source checks; two late
SeitenGokuumon examples lose leading digits in narrated DP values. No such
caption value was installed as a card rule.

## Effect on project status

This work adds durable source references and concrete regression candidates.
It changes no production engine behavior, judge review, pilots, roadmaps or
frozen inputs. No new simulator test run is claimed for this media-only change.
Existing engine status remains **312 tests last passed, zero complete valid
selected-pair fact-finding matches, zero approved lanes, zero final matches**.

The current implementation sequence remains Training/other encountered
Options, actual On Play and battle-evolution effects, stacked-board handling,
then the remaining attack/prevention cases. The new reference cases identify
observable sequences and precise source-backed expectations for that work;
they do not impose another approval gate on clear card wording.
