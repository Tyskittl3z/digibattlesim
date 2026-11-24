# Plug and play judge boundary

An imported `MatchContext` can now carry `rules.official_source` with an
official Digimon HTTPS URL, a local file under `RULES/`, and its SHA-256. Its
card definitions carry the same kind of pinned official source. The generic
context preflight verifies those files and their hashes. Existing saved
contexts keep their historical experimental locks.

`fresh_learning_campaign.run_game(..., rules_mode='STRICT')` uses a separate
semantic gate before executing each proposed command. It checks a copy of the
runtime and commits that copy only after the gate verifies the transition and
the existing transaction judge accepts it. If no checker is installed for the
encountered command or effect, the game records `RULE_CHECK_NOT_INSTALLED`
and halts on its original seed without changing the live state. The receipt
classifies this as `SOFTWARE_GAP`, not an illegal or red play. Saved strict
attempts replay their gate decisions.

The installed algorithmic checks cover opening setup, redraw, quiet phase
transitions, hatching or skipping breeding, printed breeding digivolution
routes, and quiet pass or turn-end transitions. A live effect, unsupported
printed route, modified board, or other uncovered action pauses the game.
These checks are reusable across imported matchups. Card-specific rule
checks can be added to `SemanticGate` as encountered mechanics are reviewed;
the runner does not need a deck-specific route list. A source hash match or an
algorithmic check alone does not authenticate an official ruling or grant
independent rules certification. New matchup deck restrictions, additional
generic action checks, card effect checks, a verified source-change resume
path, and the separate rules review
remain required before a full strict game can receive certified credit.

The pinned November 20, 2026 Comprehensive Rules v4.4 PDF is stored under
`RULES/official/`. The selected official rules file determines whether
receipts say v4.3 or v4.4. A strict game rejects a manual hash whose version
has not been reviewed. The current official rules page also lists November 20
card Q&A and errata updates; the selected card snapshots still need a freshness
review before a new cohort can be certified.

The completed V2 60-game software cohort is pinned by tag
`styled-60-software-v2`. It used the earlier experimental judge and retains
zero rules-certified credit. This new mode has not run a new cohort or final
evaluation.
