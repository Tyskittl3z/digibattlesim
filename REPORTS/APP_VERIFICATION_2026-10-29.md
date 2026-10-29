# Drag/drop app verification — 2026-10-29

The new entry point is **APP/DeckCompare.html**, an offline, single-file browser
app. The user requested Both (deck statistics and head-to-head), important
information saved in the after-report, and Digimon TCG-inspired visuals.

## Delivered

- Drag one UTF-8 deck file into each panel, drag two together, browse, or paste.
- Automatic card/quantity comparison; main/egg totals when metadata is complete;
  distinct counts, average known printed play costs, type/level distributions,
  full differences, search/filter, swap and clear.
- Blue/orange card frames and a digital playmat background, responsive desktop/
  mobile layout, keyboard-accessible inputs/tabs and inline vector icons.
- **Save after-report** downloads readable HTML containing exact input text,
  filename and source kind, original-file and preserved-text SHA-256, canonical
  composition hashes, all unfiltered statistics/card rows, missing card IDs,
  source/app hashes, limitations and simulation state. Complete JSON is embedded.
- UTF-8 BOM and Windows CRLF are retained until an input is edited. Unsupported
  encodings are rejected rather than silently changed. Edited text clears the
  old original-file hash. If browser crypto is absent, hashes are marked missing.
- A head-to-head tab states whether the pairing is the original supported-scope
  pair or another unsupported pair, with unresolved verification blockers.

## Not delivered or claimed

Actual playable head-to-head simulation remains blocked by the existing engine's
unresolved rules, required verification and missing frozen runner. The app plays
**zero** matches, reports unavailable wins/losses/rates, and never borrows old
match results or pilots. The Both request is therefore **partially fulfilled**:
statistics/report UI is operational; live head-to-head results are not.

The supplied card metadata covers **41 IDs**, not the whole Digimon card pool.
Unknown IDs preserve their exact quantities/names and data gaps. Their egg status,
cost, level, color, effects and format legality are not invented. Main/egg totals
remain unclassified if any unknown cards are present. No deck advice is given.

## Executed checks

| Check | Actual result |
|---|---:|
| Node core/parser/report tests | 9 passed |
| Built inline-script syntax test | 1 passed |
| Chromium import/interaction/report/mobile tests | 6 passed |
| Existing Python engine tests | 128 passed |

Browser checks exercise native two-file drag/drop, file chooser, pasted edits,
swap/clear, keyboard tabs, unknown and malformed lists, full report export despite
table filtering, exact BOM/CRLF/original byte hashes, literal uploaded markup and
mobile overflow. Each test also verifies no page JS errors or external HTTP(S)
requests. No installation or network is needed by the delivered app.

Managed Chromium blocks file:// navigation and the normal process sandbox blocks
its socket setup. Tests ran Chromium with the supported elevated process flow and
a temporary loopback-only static server, closed after testing. Direct file URL
navigation could not be tested in this environment. The artifact embeds all CSS,
JS and data, with no fetch, module imports, fonts or other network dependencies.

Code review identified ambiguous quantity/code parsing and BOM-byte loss. Focused
regressions reproduced these and passed after fixes. Browser/build tests also
caught an inline script-end-tag packaging error and CRLF normalization; both were
fixed and verified. Current test outputs are in `ARTIFACTS/app-2026-10-29/`.

Existing SOURCE/ engine files and decklists are unchanged by the interface work. No new fact-finding
matches, judge certificates, strategic approvals or final evaluation results are
claimed. The existing gameplay work remains in STATUS/WORKFLOW and its artifacts.
