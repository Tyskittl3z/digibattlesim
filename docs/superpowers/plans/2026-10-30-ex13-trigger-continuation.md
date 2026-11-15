# EX13 trigger continuation

User instruction: do the next steps; execute inline under the approved explicit
context design. No further permission checkpoint is needed. Existing global
constraints and full-match evidence gates remain unchanged.

## Source authority

Pinned comprehensive rules v4.3, 15-3-1/3, 15-4-2 through 15-4-5,
15-14-1; EX13-023 Q7266/Q7269 and EX1-013 Q3203. Exact inherited text
from EX13-022, BT22-023, P-138 and EX1-013 official pages.

## Implementation sequence

1. Add source-instance-bound pending effect records and deterministic IDs.
   Scheduler chooses from the highest derived-trigger group, turn player before
   non-turn player. The controller explicitly selects each effect and processing
   choice. Canceled/lost sources and exhausted OPT effects cannot resolve.
2. Extend transactional dispatch to consume only an eligible pending record and
   retain derived effects. Direct dispatch remains blocked while effects are
   pending. Invalid actions/unsupported dependencies preserve complete traces.
3. Add exact-text inherited unsuspend (EX13-022/BT22-023) and memory gain
   (P-138/EX1-013), with proper trigger/processing conditions and OPT consumption.
   Orientation changes emit reactions only after an actual change; declined or
   prohibited changes emit none. Unsupported Tamer/other reactions still halt.
4. Add explicit opening-hand/re-draw/security preparation and phase metadata as
   a source-backed setup primitive, without pretending setup is a full match.
5. Update readiness inventory and save fresh versioned scenario evidence. Run
   focused red/green regressions, the full suite and independent code review.

## Failure cases to prove

Wrong controller/order; derived-trigger priority; source removed/re-entered or
lost inherited effect; simultaneous duplicate physical sources; second OPT use;
no automatic optional decline; memory bounds; no phantom unsuspend reactions;
atomic rollback and complete audit records; deterministic replay; stale pack or
source identity; after-terminal/pending guards; fresh setup and hidden security.

This continuation does not relax judge review or claim full gameplay coverage.
Actual fact-finding, strategic evidence and final evaluation follow only after
the remaining loaded effects and complete phase/security/attack handling exist.
