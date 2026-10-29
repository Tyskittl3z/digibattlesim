# Final evaluation preparation

This directory does not contain final results or a frozen evaluation.

From `SOURCE/`, after producing a **new** current cohort:

```bash
python -m match_evidence --out ../ARTIFACTS/current-YYYY-MM-DD-NN --count 60
python -m evaluation_gate --cohort ../ARTIFACTS/current-YYYY-MM-DD-NN
```

The gate exits **2** while prerequisites are missing. It rejects missing reviews,
altered records, stale source/decks, incomplete or unbalanced cohorts, unresolved
halts, unmodeled optional attacking choices, and unapproved roadmaps.

Candidate roadmap generation is explicit and refuses to overwrite existing
maps. Version old maps before regenerating:

```bash
python -m evaluation_gate --cohort ../ARTIFACTS/current-YYYY-MM-DD-NN --candidate-roadmaps
python -m evaluation_gate --cohort ../ARTIFACTS/current-YYYY-MM-DD-NN --prepare ../EVALUATION/preparation-YYYY-MM-DD-NN
```

The preparation output reserves 10,000 distinct deterministic seeds outside
fact-finding indexes 0–59, with 5,000 starts per seat. It reports played matches
as zero and `frozen: false`. This is not a checkpoint/resume implementation.
The actual frozen runner and resume implementation must wait until eligibility
passes. Preparation lists the remaining execution work explicitly.

An independent review file passed with `--review` is an external attestation;
the gate can validate its bindings, but cannot authenticate judge qualifications.
Never generate a favorable review file to bypass a blocked gate. Official
evidence and human/rules review must precede any certification claim.
