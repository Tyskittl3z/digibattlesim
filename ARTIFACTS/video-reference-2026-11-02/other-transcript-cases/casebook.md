# Transcript-derived timing cases

Status: six candidate regression scenarios from user-supplied timestamped transcripts. No video frames were reviewed for this casebook. None of these claims establishes a rule, card identity, legality, strategy result, or completed simulator match. Production code was not changed. Use the exact official card wording/ruling before implementing the proposed assertions. No deck-specific pilot or result data transfers to the selected imported matchup.

`source-manifest.json` pins the original transcript bytes; the three `*.segments.json` files preserve timestamped text with whitespace normalized. Quotations below preserve the wording of the corresponding transcript segments, including apparent recognition mistakes.

## Jesmon / Alphamon

### J1 — Redirected target replaced by Blast DNA Digivolution

- Transcript range: **12:21–13:19**. At 12:24–12:28 the inherited effect is described as: “when one of your opponent's Digimon attacks, you may change the attack target to this Digimon.” After Counter / Blast DNA Digivolution, 13:05–13:15 says: “was blast DNA digivol, which is considered as a new Digimon. Therefore, Jesson's attack that was redirected ... There are no targets to attack. As the attack process will reach towards its end step”.
- Narration claim: an attacking-trigger redirection finishes before Counter; the redirected target participates in Blast DNA, yielding a new Digimon; the old target is absent when the attack resumes, and the attack reaches its end without a security check. The narrator then passes turn at 13:17–13:19.
- Candidate assertions, after official verification: retain attack-target instance identity through Counter; do not retarget automatically to the DNA product or player; resolve the attack-end procedures and queued effects; defer the turn change until attack/effect processing finishes.
- Unresolved: exact IDs and stacking inputs for the inheritable redirection and ACE are not supplied here. “Orium”, “Greymon”, and other names fluctuate. Reconstruct actual stack identity, exact DNA requirements, memory changes and any intervening attack-end effects before making an executable fixture.

### J2 — Timed DP modifier while Digimon-effect immunity is active

- Transcript range: **16:34–17:34**. At 16:38–16:46: “Even though Genkan is currently unaffected by the opponent's Digimon effects, the DP reduction effect lingers until the end of opponent's turn, meaning it will still be applied as soon as it loses its protection effect.” At 17:27–17:32: “because Genkum's protection effect is no longer there, it will have his DP reduced by a total of 16,000 putting it down to zero”.
- Narration claim: two timed −8,000 DP modifiers are described during immunity; an immunity expires at the earlier boundary; the remaining modifiers then apply, leading to a zero-DP rule deletion.
- Candidate assertions, **only if official wording/rulings confirm this model**: track each modifier's duration and immunity duration independently; expiration of immunity does not necessarily discard a still-live modifier; recompute DP and perform rule processing at the appropriate boundary before any subsequent turn action.
- Unresolved: this is particularly rules-sensitive. Exact granting source, duration endpoints, modifier targeting wording and the active player's turn must be pinned. The transcript alone cannot establish that a previously ineffective modifier will subsequently apply, nor that all cited durations differ as narrated.

## GraceNovamon / Ceresmon–Bacchusmon

### G1 — End-of-turn effect cascade and pending work across nested effects

- Transcript range: **10:24–13:04**. At 10:27–10:40 a tamer suspends to use an Option with reduced cost. At 11:12–11:20: “reversal of the dead option card will arts digivolve. Instead of trashing after use, your cards may dig evolve into this card without paying the cost”. At 12:54–13:04: “With all pending effects activated and resolved, we now go back to Dan and Cananan's end of your turn effect that triggered prior”.
- Narration claim: one end-of-turn activation uses an Option; that resolution generates leave-area, play, digivolution, inherited and on-play effects; a separately pending end-of-turn tamer effect remains available later in the cascade.
- Candidate assertions, after official verification: crossing memory into the opponent's side does not immediately switch turns; maintain independently pending end-of-turn activations across nested Option / play / digivolution effects; re-evaluate source validity when a pending activation is selected; resume the turn-end process only after all required work resolves.
- Unresolved: the transcript compresses resolution and activation ordering, and switches between “Penyuki” and “Dan and Cananan”. Do not infer that one effect was interrupted mid-sentence or that a specific queue order is mandatory. Identify both tamers, the dual card's Arts Digivolution text and all source-incarnation changes before an executable fixture.

### G2 — Counter action using own source count, followed by attack termination

- Transcript range: **17:15–17:38**. At 17:23–17:35: “proceed towards the counter timing where Grace Novon has a counter effect. Once per turn for each of this Digimon digolution cards, you may trash any one Digolution card from your opponent's Digimon. Since Grace Novon has two sources, it will trash away Electmon and Wyomon”. At 17:38: “will end the attack”.
- Narration claim: ordinary attack-triggered effects finish before a Counter activation; two own sources permit removal of two opposing source cards; the attack then ends.
- Candidate assertions, after official verification: expose this activation in the Counter window; determine the allowed number and targets from the actual printed text and current sources; enforce once-per-turn usage against the correct Digimon instance; resolve attack termination without performing a security check.
- Unresolved: “for each” vs “up to” or mandatory selection is not safe to infer from captions. The printed effect may have additional conditions or clauses. Exact card ID, selection order, source-count timing and what happens with fewer opposing sources need separate source checks.

## Junomon / Neptunemon–Venusmon

### N1 — Same Digivolving effect, DNA-specific clause gated by evolution mode

- Transcript ranges: **09:34–10:01**, **10:55–11:09**, and **17:17–17:29**. At 09:53–09:57: “Then if DNA digolving trash both players top security card”. At 17:17–17:23: “place Magna Anjimon to the top of the security stack. However, it is not DNA digivolve. So both players will not trash the top card of their security.”
- Narration claim: the same named Shakkoumon's When Digivolving effect puts a card in security with either digivolution method; its subsequent security-trash clause applies only on DNA Digivolution.
- Candidate assertions, after official verification: record evolution method on the event rather than inferring DNA from the resulting card or its source composition; execute the common clause in both fixtures; execute the conditional clause only in the DNA fixture; process security-addition triggers and physical-card conservation correctly in both.
- Unresolved: exact Shakkoumon ID is narrated as BT25 but not independently verified here. A caption at 17:27 says “When security stack is added to Digivolve one” and is too garbled to establish the associated trigger or target. Do not encode that phrase as card text.

### N2 — Execute's own-effect deletion can offer Decode

- Transcript range: **13:20–14:09**. At 13:22–13:25: “At the end of your turn, this Digimon may attack, but at the end of the attack, delete this Digimon.” At 13:50–14:05: “at the end of attack, Junamon Hysteric Mo will delete itself from execute, but also has the keyword decode ... When this Digimon will leave the battle area other than by battle, you may play one specified Digimon card from his digion cards without paying the cost.”
- Narration claim: an Execute attack is made during end-of-turn processing; its delayed deletion happens at attack end; Decode offers a source-card play on that nonbattle leave event, and the narrator describes Junomon returning.
- Candidate assertions, after official verification: carry Execute's delayed deletion through the attack; distinguish effect deletion from battle deletion; offer a legal Decode selection before moving the original stack; preserve and move only the chosen physical source card; continue remaining deletion/On Deletion and turn-end work in the proper order.
- Unresolved: pin the exact Hysteric Mode card and Decode selector, the actual chosen source and relevant source-card effects. Do not transfer Partition's separate “other than by your effects” exclusion into Decode merely because both involve playing sources. The nearby 13:31–13:37 caption about an inherited once-per-turn reset is compressed; any reset fixture must locate the earlier DNA event and establish the resulting new Digimon instance explicitly.

## Caption-quality limits shared by these files

- Card names change spelling within a single sequence; set numbers and IDs must come from exact lists or official sources.
- Pronouns such as “it”, “their turn” and “this Digimon” are unreliable without a board reconstruction.
- Jesmon/Alphamon's 12:50 narration says “top security card”; around 18:08 it says “top three cards” for an apparently similar ACE line. This cannot establish a security-trash quantity; use the printed text, not a majority vote between captions.
- These are narrated branches, not a full inventory of legal alternatives. Optional activations shown in one game are not defaults for a bot.
- Reported video outcomes count as zero simulator matches and do not certify interaction legality.
