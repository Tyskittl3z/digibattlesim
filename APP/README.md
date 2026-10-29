# Open the app

Download/open **DeckCompare.html** in a modern desktop browser. No installation,
terminal, server, account or Internet connection is required to use it.

1. Drop one UTF-8 text decklist into each panel, drop two files together, or paste both lists.
2. Compare their contents, quantities and available card statistics automatically.
3. Click **Save after-report** to download a readable, self-contained HTML report.

**Try the sample decks** loads the exact supplied Jupitermon and Amaterasumon/Toho
lists. Browse, paste, swap, clear, search and differences-only filtering are also
available. The interface uses Digimon TCG-inspired blue/orange card frames and a
digital playmat background; no remote assets or card images are requested.

## Current capabilities and limitations

- Comparison accepts arbitrary well-formed printed card-code lists. The bundled
  metadata covers **41 IDs from the supplied matchup**. Other IDs retain their
  exact names/quantities and show missing data; their types, eggs, colors, costs
  and effects are not guessed. Main/egg totals remain unclassified while unknown
  cards exist. Printed-cost averages use known main cards only.
- Typical lines: `4 Elecmon BT24-031`, `4 BT24-031`, `BT24-031 x4`.
  Comments and main/Digi-Egg section headings are accepted. Invalid/ambiguous
  rows prevent comparison instead of being silently dropped. Keep files under 1 MB.
- All processing stays in the browser. Uploaded files are read, never changed.
  Reports are saved only when you click the report button. Refreshing/closing the
  app clears unsaved inputs.
- **Head-to-head simulation is not operational.** Its tab reports the pairing's
  unverified/unsupported status. Existing engine rules defects, legal verification,
  pilots, roadmaps and the frozen runner still need completion. No wins, losses,
  estimated win rates or past matchup results are substituted.

## What the after-report saves

The readable HTML report also embeds complete JSON in `script#report-data`:
original texts/filenames, input kind, original uploaded-file SHA-256, preserved-text
and canonical composition hashes, all entries and parse errors, full unfiltered
statistics/differences, unknown IDs, data/app source hashes, limitations and
simulation fields. UTF-8 BOM and CRLF are retained for unedited uploaded files;
editing changes the input to pasted/edited text and clears the old file hash.
If Web Crypto is unavailable, hashes are explicitly unavailable rather than invented.

Current simulation fields are matches 0, wins/losses/rate null, seeds/logs empty.
They are unavailable results, not a zero-percent win rate. A new deck never inherits
another pairing's results or pilots.

## Development

```bash
python APP/build.py
node --test --test-isolation=none --test-reporter=spec APP/tests/compare.test.cjs
python -m unittest discover -s APP/tests -p 'test_build.py' -q
python -m unittest discover -s APP/tests -p 'test_browser.py' -q
```

Browser tests use development-only Playwright plus system Chromium. In this managed
environment, file URLs are blocked by browser policy, so those tests serve the exact
single HTML internally on loopback. The product itself has no server/network dependency.
Browser tests require the process permissions needed to launch Chromium. Python engine
tests remain under `SOURCE/` and no engine/deck files were changed for this interface.
