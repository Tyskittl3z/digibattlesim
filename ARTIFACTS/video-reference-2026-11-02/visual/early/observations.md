# Opening frame samples and printed-source checks

Reference video: the uploaded 240p SeitenGokuumon / Gammamon game. Source
transcript: file_000000003e6881f5b5fbf8ba1da32506. These are synthetic regression
candidates, not a continuous replay, rules certification or strategy evidence.

## 00:07–00:24 — Saneiketsu Invitation use and conditional processing

At exact 00:10, the enlarged overlay visibly names Saneiketsu Invitation.
The transcript describes using its SW-trait requirement with a breeding-area
card, trashing Gokuumon, drawing two and placing the Option in the battle area.
The physical card identities, draw count and memory payment are not established
by the still frame.

Official EX12-071 text confirms a three-cost Option, Use Req. (SW trait),
and `[Main] By trashing 1 [SW] trait card from your hand, Draw 2. After,
place this card in the battle area.` Its official Q&A explicitly says that
without the trash condition the part after `After` cannot place it there.
This yields a precise paired fixture: successful payment permits draw/place;
failure to pay must not place the Option. The video is an example of the
successful branch, not evidence of all legal choices.

## 00:40–01:12 — Face-up security movement, play, then search

At exact 00:46, the enlarged overlay names Genshi Continent & Ashino Island
and highlights its Use Req. clause. The transcript describes bottom security
to hand, placement of this Option face up at the bottom of security, then a
discounted Kamemon play and its search before the turn passes. Hidden card
identities and exact payment cannot be confirmed from this sample.

Official EX12-074 confirms the separate Main, face-up-security persistent
attack trigger, and Security effect. These must remain distinct engine
locations/timings. Its Q&A also permits using Main with no security: the
impossible addition is skipped and the Option is placed in security. A fixture
should exercise this zero-security boundary separately from the video state.

## 02:47–03:40 — Attack-triggered evolution and acquired effects

Exact 03:00 shows the Hiro Amanokawa overlay and its Your Turn attack trigger.
Exact 03:26 shows Regulusmon's acquired-effects text. The transcript describes
BetelGammamon attacking, Hiro suspending to evolve it to Regulusmon, the latter
gaining effects from Gammamon-named sources, and a later reduced-cost play.
The earlier security check, complete source ordering and once-per-turn history
are not reconstructible from these frames alone.

Official EX12-066 confirms suspension as the condition for choosing an
evolution or Option-use branch, with different reductions. EX12-013 confirms
BetelGammamon's Main play/use reduction. RB1-030 confirms that Regulusmon
gains effects of Gammamon-named source cards; its Q&A distinguishes main effects
gained this way from the source cards' inherited effects. A fixture must track
the acquired effect's identity and usage history explicitly; the transcript
does not by itself certify an extra use or reset.

## Source and visual limits

Five official source pages were fetched and hashed: EX12-071, EX12-074,
EX12-066, EX12-013 and RB1-030. Their bytes and extraction are preserved with
the artifact. HTML extraction can lose angle-bracket keyword names in some
Q&A answers; raw source and official card images take precedence. The shared
Use Req. definition is in pinned comprehensive rules 16-42; it refers to
specified cards on the field. This review does not substitute a still image
for proving all breeding-area eligibility conditions in the actual game.

The transcript's names are preserved in the timestamp index. Canonical card
names/IDs above are from the supplied lists and exact official pages. No full
match credit, outcome or implementation claim is made.
