# Bot C field tracker

The user explicitly authorized work on Bot C while actual matches stay paused.
Implement the tracker only. Keep the existing rules engine, player policies,
learning/scoring, judges and fresh-game runner unchanged. Private unit fixtures
and replaying stored commands for verification create zero new match credit.

Bot C observes committed before/after snapshots and retains a private audit
ledger. It does not choose plays or resolve card wording. Count all physical
cards exactly once across deck, eggs, hand, security, trash, battle stacks,
breeding and the transient resolving Option. Reject context/inventory/schema
corruption, stale before snapshots and changed game seed/first player. Stable
entity IDs preserve stack identity through evolution; reanchoring is not a
false departure of every lower card. Track orientation, statuses, counts and
private zone movements.

Player views must exactly match ContextRuntime.public_view: own hand and public
field/trash/breeding, count-only decks/eggdecks/security/opponent hand. No audit
RNG or private movements enter these views. Public metrics expose body counts,
stack/source sizes and cumulative completed successful Security checks. Require
actual consistent CONFIRM-to-END card movement; declarations, canceled checks,
direct wins and failed commands add no successful check. Failed observations
require unchanged physical state/RNG and are unrated.

Version/hash the tracker and chain each observation with command/result/judge
and full normalized before/after state hashes. Ignore only engine execution_id
and normalize legacy resolving_option=None for comparisons across intentional
engine repairs. All outputs are detached. Do not claim detection of every
identical no-op retry without an external command index. No strategic colors,
weights, learning updates, independent-rules certificates or actual game run.

Use the existing snapshot schema. A separate observer fits the tracker role;
changing the authoritative rules state or adding an LLM resolver would mix
responsibilities and is outside this request. This component can be verified
against archived recorded commands without advancing those games.
