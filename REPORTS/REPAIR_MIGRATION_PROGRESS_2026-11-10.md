# Engine repair migration progress — November 10, 2026

Fresh-game checkpoints now have an explicit repair path that preserves the same
seed, complete board/hidden audit state, engine and policy RNG, player identities,
learning model and previously selected actions. The original record is retained
inside a hashed lineage; its successful prefix must produce identical earlier
outcomes under the repaired build. Migration returns at the saved boundary and
does not retry the failed action, choose again or update learning.

Both builds load Python source directly in isolated workers. This closes an
independently reproduced case where Python's cached code could hide a changed
earlier result. Migrated replay/resume uses the same verified-source path and
keeps the model frozen. Normal source checks stay strict. Unlisted or protected
changes, changed rules/context/model and changed earlier outcomes are rejected.

Final focused checks: **173 passed in 73.877 seconds**, including 18 cross-build
migration tests. Tests cover repeated repairs, pending saved choices, real
mechanic receipt/observer-chain changes, stale caches, already imported modules,
dynamic handlers and tampered lineage. Independent scoped rereview found the
cache defect addressed and no new blocker.

A separate private 4.920-second proof authenticated archived original sources,
injected an old-only redraw gap, preserved its stopped checkpoint through an
exactly pinned repair, and resolved its selected redraw with a one-command retry
without reselection. Migrated and retried logs replay exactly. The parent, model,
historical production record and source bytes stayed unchanged. All 114 current
Python sources and the private original build are archived with hashes at
`ARTIFACTS/repair-migration-2026-11-10/`.

Actual matches remain paused. Production fresh games, training updates, live
ratings, valid fact-finding and final matches are all zero. The two player bots
remain aggressive A and defensive B, with Bot C tracking the field. No random
reference policy or historical mixed-game learning was substituted. Source-only
replay proves software integrity, not independent rules certification or full
selected-card coverage. Approved roadmaps and the final freeze/evaluation remain
future work.
