# Prepare the browser for battle simulation

User authorized the necessary changes and a GitHub update, after accepting the
browser/catalog UI. Continue on the isolated general-browser-simulator branch.
No newer engine branch is advertised on GitHub. Preserve engine/gameplay/deck files.

Selected approach: add a small versioned, file-based browser/engine handoff to the
existing Python/JavaScript stack. Replacing the engine or enabling unverified runs
would violate the evidence workflow. A server-execution API is premature while
mechanics and review gates remain blocked.

Build a deterministic read-only readiness snapshot from current engine provenance,
the existing eligibility validator and pinned official-vs-engine card metadata.
Separate stale diagnostic attempts, software completions, HALTs and valid reviewed
matches. Never present historic attempts as certified or infer final results. Expose
precise blockers and metadata drift only for the matching ordered loaded decks;
other decks remain unsupported, with no borrowed diagnostics.

Export a versioned preparation request from the browser containing exact inputs,
raw/composition/matchup hashes, current catalog/restriction/readiness bindings and
explicit non-execution intent. A Python validator reparses raw input, validates every
hash and current dependency, enforces exact A/B deck scope and returns a blocked
preflight with the actual gate blockers. It never runs a match, accepts client claims
of certification, or lets changed decks inherit evidence. Stable ASCII card-code
ordering must agree across JS/Python and browser locales.

Automate build/verification in a single local command and GitHub Actions. Exercise
actual browser-to-Python request interchange, tampering, stale bindings, unsupported
and swapped decks, empty/invalid input and offline/portable readiness. Rebuild and
verify release files, refresh the downloadable project backup, push the branch.
Document the integration contract and exact remaining engine work for the next lane.
