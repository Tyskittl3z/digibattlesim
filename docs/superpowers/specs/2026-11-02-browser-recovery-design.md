# Browser/catalog recovery

User authorized rebuilding the missing browser/PWA work from the available a5cd54e snapshot and screenshots. The original 0dc5d4e and c2444df objects are unavailable. This is a reconstruction, never a claim to have recovered those commits.

Use the existing plain JavaScript and Python build tools on an isolated general-browser-simulator worktree. Do not change engine, evaluation, gameplay rules or deck files. Restore an official-English catalog with source HTML hashes and deterministic chunks, exact-input deck comparison, conservative legality checks, dependency/seat-specific identities, transactional IndexedDB workspaces and an offline PWA. Provide downloadable exact-input reports and explicit locked evidence stages (mechanics, 60 reviewed matches, routes, freeze, 10,000 matches). No inferred win rates, card recommendations or invented certification.

Approaches: recover old files (attempted; absent locally/remotely); reconstruct within existing app (selected by user); replace stack (unnecessary migration). Keep legacy single-file app as fallback, add served/installable index.html. Browser catalog loads by code prefix; installation caches all chunks so arbitrary imports work offline. Use no remote runtime dependencies. Pin current fetched official sources and report actual counts rather than claiming the historical 4,481 count.

Legality: exactly 50 main cards, 0–5 eggs, default four copies unless explicit official card text permits more; unknown/non-deck codes, banned/restricted/pair violations remain explicit. Missing format/date/restriction verification prevents a final LEGAL claim. Rules and strategy certification stay separate. Catalog metadata is not executable card mechanics.

Storage: immutable hash-keyed reports and identity-bound workspaces in one atomic transaction; expected-revision conflict leaves prior workspace and records intact. Quota/abort errors surface to user. Save is explicit, archived workspaces remain accessible, dependencies invalidate reuse. File BOM/CRLF and original byte hashes survive save/restore/report.

Acceptance: parser fixtures, deterministic catalog verifier, Node behavior tests, real Chromium IndexedDB abort/conflict tests, offline reload/arbitrary-card imports, mobile/keyboard/drop/report flows, regression suite. Deliver a project archive with commits and one-command local launcher; keep a durable progress ledger.
