# Battle-simulation preparation — November 2, 2026

## Delivered

The accepted browser UI now has a concrete, versioned bridge to the existing Python
engine. **Export simulation request** preserves the exact seated inputs, UTF-8
file/text/composition hashes, browser-independent matchup identity, catalog and
restriction snapshots, current engine-source binding and request hash.

`python TOOLS/engine/request.py <request.json>` independently reparses the raw lists
and validates their hashes and dependencies. It rejects tampered entries, false
original-file hashes, stale engine/app data, swapped/unsupported pairings, execution
requests, unknown fields and client certification claims. A valid matching request
returns `request_valid: true`, `status: BLOCKED`, `can_execute: false`, exit **2**.
No path in this preparation bridge invokes a gameplay runner.

**Match evidence** now reflects an actual source-bound readiness snapshot rather
than only static UI blockers. Only the exact ordered Jupitermon A / Amaterasumon-Toho
B pairing receives its old diagnostic counts. Other decks receive no borrowed
records. The source snapshot is included in portable/PWA builds, after-reports and
workspace identities; changed dependencies invalidate previous workspace evidence.

The actual current cohort remains **60 older attempts, 29 software completions,
31 HALTs, 0 independently reviewed valid matches**, stale after source changes.
The readiness snapshot has **39 blockers**, including the exact HALT indices/reasons,
unmodeled optional effects, missing independent reviews, unverified rules, incomplete
coverage, unapproved roadmaps and **one metadata drift**: EX12-062 colors in the
older engine snapshot include Green/Purple; the pinned official record is Purple.
Gameplay/card data was not silently changed to remove this blocker.

Added a one-command software verification harness, GitHub Actions workflow,
configurable Chromium executable, current tracked-file checksum refresh/check,
and source/verification ZIP packaging without nested prior backup ZIPs. Root README
now points to the full-catalog portable app rather than the older 41-ID fallback.
`docs/ENGINE_HANDOFF.md` defines the contract and exact remaining engine-lane work.

## Tool-executed checks

| Suite | Passed |
|---|---:|
| Existing SOURCE engine regression tests | 148 |
| Node app/core/storage/catalog/identity tests | 21 |
| Official catalog fixtures | 8 |
| Actual JS-to-Python protocol tests | 11 |
| App checks (20 Chromium + 1 legacy inline-build check) | 21 |
| Checksum inventory regression tests | 2 |
| **Total automated tests** | **211** |

Catalog integrity, engine-readiness freshness, full PWA/portable release verification,
byte-identical readiness/app rebuild and Git whitespace checks also pass. Readiness
view was checked at desktop and 390px mobile width. Existing engine/deck/rules/
roadmap/evaluation files are unchanged by this preparation work.

Independent code review identified acceptance of client certification fields;
that was reproduced before the fix, then closed with exact dependency schema and
UNVERIFIED-field validation. The reviewer independently reran the then-current ten
protocol regressions successfully. A later original-file-byte-hash regression is
also green. The checksum helper's omitted/duplicate inventory issue was reproduced
and fixed with two regression tests and exact agreement against Git's tracked files.

## Remaining boundary

This is integration readiness, not a completed battle simulator. No new diagnostic
or final matches were played. No rules, strategic lanes or win rates were certified.
The separate engine lane must reconcile official data, implement/verify encountered
mechanics and choices, obtain a fresh minimum balanced 60 full reviewed matches,
close coverage and approve routes, freeze exact inputs, then actually play 10,000
matches. A future execution adapter needs its own explicit eligible/frozen contract;
version 1 preparation requests remain non-executing.
