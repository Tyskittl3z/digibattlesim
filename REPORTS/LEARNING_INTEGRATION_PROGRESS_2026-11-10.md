# Learning integration progress — November 10, 2026

The fresh-game runner connects Bot A aggressive, Bot B defensive, Bot C's field
tracking, observed board/tempo scoring, automated judge receipts and persistent
learning. Players use their own hand and public field information. A game's
learning model remains fixed; only eligible completed games update it, once per
logical game identity. Historical mixed-policy games supply no fresh training.

The final focused run passed 155 tests in 35.346 seconds. Component reviews found
no remaining blockers. A separate five-command private opening/phase fixture
passed exact replay and resume, preserved saved choices and policy RNG, and
correctly rejected training from an unfinished game. The reference player was
disabled in that proof. The model, historical record and source bytes remained
unchanged. All 112 Python sources are archived with hashes alongside the proof
at `ARTIFACTS/learning-integration-2026-11-10/`.

Actual matches remain paused before the first fresh game. Production campaigns,
fresh games, learning updates, live ratings, valid fact-finding and final matches
are all zero. No production schedule is locked. The 10,000 evaluation stays off.

The remaining resume limitation is concrete: saved games currently require the
same software build. A verified migration step is needed to preserve a stopped
game across an engine repair. Existing source checks reject changed builds;
do not bypass those checks or reroll seeds. Selected-card coverage and rules
certification are also incomplete. Automated judge receipts remain experimental,
and observed color scores do not establish approved strategic roadmaps.
