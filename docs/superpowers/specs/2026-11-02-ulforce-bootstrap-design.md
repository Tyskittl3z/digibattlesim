# Distinct-list Ulforce bootstrap

The user delegated the starting matchup on November 2: it need not be Ulforce
versus Gallantmon; choose what works best. Development priority moves to the
two exact workbook lists 123129 (Federico Nine) and 122110 (Bern). They are
different 50+4 lists, with 22 distinct source-pinned cards and 79 printed units,
compared with 45 cards and 150 units in the original pairing. This is a smaller
implementation surface, not a prediction of deck strength or completion time.

Alternatives considered: retaining the original pair preserves every diagnostic
seed but requires both card families; changing to another cross-archetype pair
saves at most five source-covered printed units; a distinct-list Ulforce mirror
retains the generic mechanics and official definitions with a substantially
smaller card set. The mirror is the implementation choice made under the user's
delegation. The randomized evaluation queue is preserved unchanged.

This increment pins the mirror inputs, replaces three duplicated one-pair
capability checks with one exact-context capability check, and lets diagnostic
commands select a saved context. It does not implement missing card effects.
Both the original and mirror contexts remain supported only for the existing
explicit basic capabilities. An arbitrary input path, edited source ID, changed
deck count, changed card definition or changed rules snapshot grants no support.

Mirror context ID:
`9dd326339d64f263c7570a33b03e4ab9d57c1cd466ec0fddffcec4d7ea5bcd8d`.
Mirror file: `ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json`.

Fresh pilots, seeds, diagnostics and provenance bind to the new context. No
training data, roadmaps, match results or certification transfer. The original
runner defaults remain the original context for backward compatibility. Replay
loads the context recorded in that attempt and refuses changed source bytes.
Diagnostic cohorts may not overwrite an output directory or mix contexts.

The source-pinned English worldwide rules already retrieved for the original
pair remain shared rules evidence. Official card sources retain their exact
original paths/hashes; their location under the original pair's directory does
not authorize its decks, pilots or results in the new pair.

Verification requires real mirror ordinary play, search, breeding evolution,
source-loss guards, source/definition/context tamper rejection, fresh pilots and
same-context replay, followed by the full existing suite. Then run a new balanced
diagnostic cohort, preserving every halt. Such attempts earn zero accepted-match
credit until the existing full-match and rules-evidence requirements are met.
