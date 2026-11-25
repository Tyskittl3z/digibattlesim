# Plug and play rules gate

The engine already loads a `MatchContext` with two exact decks and card text,
but its comprehensive-rules source is selected from a fixed matchup folder.
The current judge checks transactions, conservation, and source identity after
the engine acts; it explicitly does not perform an independent semantic check.

New imported contexts may select their own pinned official comprehensive-rules
source. Existing saved contexts keep their historical fallback and remain
experimental. A new strict adjudication mode checks each proposed action
before applying it with a separate, reusable checker selected by the action
and encountered effect, then checks the resulting transition before committing
the candidate runtime state. A missing checker or unresolved rule halts the
original seed and records the proposed command. A failed transition check
must leave the live runtime unchanged. No selected-deck route is preloaded.

The first installed checker covers opening preparation and redraw from the
generic Comprehensive Rules. Card-specific effects initially remain unknown
to the strict gate until their encountered mechanics receive a separate
source-backed checker. The framework may run on any imported context with
complete pinned card definitions; this change does not claim arbitrary card
effects are already playable or independently certified. Existing V2 records
and their pinned source tag remain immutable. The 10,000-game gate stays off.
