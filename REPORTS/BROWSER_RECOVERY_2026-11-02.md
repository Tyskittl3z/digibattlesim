# Browser/catalog reconstruction — 2026-11-02

## What was recovered and rebuilt

The available repository and both advertised GitHub branches contained only
`a5cd54e`. The screenshots referenced `c2444df`, `0dc5d4e`, and a partially written
PWA in a deleted cloud build; those commits and files were unavailable locally and
could not be fetched by the supplied short reference. This branch reconstructs
the requested browser/catalog scope from the available baseline. It does not claim
to contain the original lost commits.

Implementation is isolated on `general-browser-simulator`. No `SOURCE/`, `DECKS/`,
`EVALUATION/`, `RULES/` or `ROADMAPS/` files changed. No shared branch was pushed
or merged. The engine's existing verification blockers remain unresolved.

## Delivered behavior

- Official English catalog: **4,481 unique canonical cards, 72 category sources,
  68 hash-verified prefix chunks**, zero conflicting base records. All 41 IDs in
  the supplied decks resolve. Alternate art does not replace base text.
- Official restriction snapshot: **57 banned/restricted IDs**, **three banned
  pairs**, effective September 1, 2026, pinned as of November 2, 2026. Current-list
  parsing excludes historical restrictions. Official errata source is pinned;
  before/after text is attached to 33 affected catalog records and shown separately.
- General import/comparison: exact quantities, unknown codes, parse errors, known
  metadata statistics and unfiltered reports. Uploaded BOM/CRLF text and original
  file-byte SHA-256 survive save/restore until editing.
- Construction checks: 50 main cards, 0–5 eggs, four-copy defaults, printed high-copy
  exceptions, shared card-number limits, restrictions and banned pairs. Passing
  these checks does not certify event/release eligibility or gameplay rules.
- Exact-seat and dependency-specific identities; generic bots follow the actual
  imported pairing. No previous pairing's simulation results or pilots are reused.
- Persistent IndexedDB workspaces and immutable hash-addressed report records,
  atomic updates, stale-revision refusal, archive/restore, explicit save errors,
  and protection against delayed restore/save overwriting newer input/selection.
- Vivid blue/orange responsive UI, official catalog browser, exact missing-mechanics
  list and locked evidence stages. Justitia, Dike and Týr remain separate layers.
- Installable static PWA caches all 85 release assets, including every catalog
  chunk. Cache installation verifies bytes and fails atomically. Failed installation
  is reported explicitly; an update never forcibly reloads an open editor.
- Portable `DigiBattle-DeckLab.html` embeds the same application and full catalog;
  no runtime HTTP requests are required. Stable localhost PWA launchers are also
  included. Browser support for local-file persistence varies.

The official page describes EX12-062 as **Purple**, whereas the older supplied
metadata listed Purple/Green. The reconstructed browser uses the pinned official
page; engine metadata was left untouched. Nonnumeric printed costs such as `D`
remain explicit and do not enter numerical cost averages. Hybrid printed types
remain visible and are accepted as main-deck cards.

## Tool-executed verification

| Check | Result |
|---|---:|
| Existing engine Python regression tests | 148 passed |
| Node comparison, legality, identity and storage tests | 18 passed |
| Official-parser fixture tests | 7 passed |
| App Python suite | 18 passed (17 Chromium checks + 1 inline-build check) |
| Catalog source/chunk/coverage/restriction verifier | Passed |
| PWA + portable release verifier | Passed |
| Deterministic rebuild of catalog, restrictions, release, worker and portable HTML | Byte-identical |
| Local launcher | HTTP 200 on loopback |
| Git whitespace verification | Passed |

**191 automated tests passed** across the four suites. Chromium checks include
legacy flows, actual two-file drag/drop, exact-byte report/restore, real IndexedDB
abort rollback and concurrent-save conflicts, archive, offline reload and a card
prefix not previously requested by the page, mobile layout, uploaded markup safety,
portable full-catalog operation with zero runtime requests, delayed restore/save
races, and failed offline installation. Quota refusal is tested by the memory
adapter's injected refusal; native browser quota was not exhausted.

A fresh reviewer reproduced the two input-selection races and failed offline
installation before fixes, then independently reran all three added regressions:
**3 passed**, no remaining material findings in the reviewed fixes. The release
verifier rejected an intentionally altered portable executable. It binds generated
worker/HTML hashes and compares embedded portable code, styles and data to sources.
Desktop and mobile screenshots were inspected; no horizontal document overflow
remained in the tested mobile flow.

## What remains locked

This app plays **zero** matches. No verified mechanics are supplied by this branch.
Reviewed valid fact-finding evidence loaded into the browser: **0**. Approved
routes: **0**. Final evaluation: **0/10,000**, rates unavailable. Existing diagnostic
engine records are not promoted to independently certified evidence.

The separate engine lane must verify loaded-deck mechanics and official rules,
produce at least 60 complete independently reviewed matches with balanced starts,
close coverage and approve evidence-backed conditional routes, then freeze the
exact inputs and actually play 10,000 final matches. Changes to frozen inputs
invalidate previous final results. No card/slot recommendations are generated.
