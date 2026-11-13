# LM-028 actual-stop independent review

No concrete defect found in the reviewed branch. This is an encountered-interaction source/code review with focused software checks; it grants no full-match certification or match credit.

The preserved Game0 seed is **12017913134550805276**. At turn3 MAIN, A has memory4, only **A:BT11-112#2** (blue Tamer Rina) in the battle area, no breeding Digimon, and selected **A:LM-028#1**. B has **B:EX13-022#3**. Using Blue Scramble is legal: Rina meets its blue color requirement (CR4-22-2). Rina cannot be its evolution base (official Q4040), so the exact available evolution choice is `None`. Pay2, perform no evolution, then place Blue Scramble in the battle area; memory remains2 and phase MAIN. The official PNG explicitly labels it OPTION despite the official HTML type error.

Replayed every preceding saved command with the same seed, confirmed exact physical state and RNG at the original halt, used the selected card, and resolved `None`. Observed the expected placement at turn3/memory2; `runtime.verify()` passed and RNG stayed unchanged.

The narrow shared Delay review also found no defect: Delay is optional, unavailable on its placement turn, and needs an opponent Digimon when processed. Q4041 permits activation without a blue Digimon in trash; Q4042 requires returning one whenever possible. Current choices require return first, cannot also play the returned physical copy, and expose optional free play only when A has no battle Digimon and the remaining blue Digimon has at most2000 DP. The trash-play and reduced-evolution helpers require their active bound Option effect.

Four focused existing tests passed: actual saved Main encounter, negative-memory evolution/placement before derived effects, StartDelay recovery order, and unbound trash-helper rejection. Preliminary test runner class-name errors were corrected; no implementation test failed. Full command, observed results, rule locators, and SHA256 hashes of official evidence, saved state and reviewed source bytes are in [lm-028-actual-stop.json](lm-028-actual-stop.json).
