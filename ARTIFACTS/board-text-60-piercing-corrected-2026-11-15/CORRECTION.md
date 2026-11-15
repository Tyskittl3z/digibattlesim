# Piercing tracker correction

The published `board-text-60-2026-11-11` campaign remains an immutable
diagnostic archive. In eight games, a successful BT20-102 Piercing check
removed a Security card during `RESOLVE_PENDING`, while Bot C counted only
checks made during `CONFIRM_ATTACK`. The scorer also rejected a valid counter
increase during `RESOLVE_PENDING`. This affected the recorded tempo and could
affect later choices learned from it.

This campaign uses the same context, campaign ID, two initial game histories,
and locked 60-seed schedule in a separate directory. It uses corrected tracker
and scorer source. Results and learning updates from the earlier campaign are
not reused. The first corrected game completed in software with exact replay;
its seed is 16664364153905075627, first player A, winner B, and 139 accepted
actions. Independent judge certification and final evaluation credit remain
zero. The 10,000-match evaluation has not begun.
