# Game0 segment02 prefix review

No concrete defect found in the **33 newly resolved commands, zero-based indices21–53**. Seed **12017913134550805276**, first player A, exact deck context and earlier decisions remain preserved. The halted BT22-022 evolution at index54 is excluded; its unimplemented effect remains the next encountered task.

The review reapplied all54 successful saved commands using the **86 hash-verified SOURCE files from this segment's archive**, rather than the changing working source. Every saved public view and result matched. `runtime.verify()` passed after each command, and an independent inventory counted the same108 unique physical cards after each command, including resolving Options. Final physical state and RNG equal the saved pre-halt checkpoint. None of the33 new commands changed game RNG. Source and record hashes, per-command checks and the reproducible verification command are in [segment02-prefix-audit.json](segment02-prefix-audit.json).

| Actual encounter | Assessment against pinned official text and CRv4.3 |
| --- | --- |
| LM-028 Main,21–22 | Blue Rina satisfies the Option color requirement. A has no Digimon base, so paying2, omitting optional evolution and then placing Blue Scramble is correct. CR4-22-2,9-1-4,1-3-2; official Q4040. |
| BT12-029 hardplay,23 | Cost12 from memory2 reaches-10 legally. Its When Digivolving and becomes-unsuspended text does not trigger on ordinary unsuspended play. CR7-1,15-16-3. |
| EX13-022 hardplays,30–31/46–47 | Both actual On Play effects were queued; each controller explicitly declined optional free-Tamer play. Per-copy once-per-turn activation was recorded. CR15-4,15-7,15-14-1. |
| EX13-069 hardplay,32–34 | Both B Aero copies correctly observe B's Tamer play. B may resolve either first and choose A's same Ulforce twice. Both restrictions last through A's turn5. No Rina start-Main effect occurs when she enters midway through turn4. CR15-4-3,15-10-2-1,15-14-1-3. |
| BT11-023 search,35–36 | Pending search correctly finishes despite negative memory. BT22-023 is the chosen Veedramon-named Digimon; BT11-112 is the chosen blue Tamer. The remaining EX13-069 goes to deck bottom. CR6-1-3,6-1-4-1,15-15-3. |
| LM-028 start A turn5,38–40 | Opponent Digimon exist and placement was turn3. Delay is optional: A explicitly declined before unsuspend; the Option remains. CR6-2-1-1,15-8-3-9,16-17. |
| LM-034 Main search,43–44 | Blue field cards meet color requirements; cost3 changes memory3 to0. A reveals the actual top3, takes one blue AeroVeedramon, returns exactly the other2 in the recorded bottom order, then places Wisteria. Same-turn Delay is excluded. Its official PNG confirms OPTION despite the HTML type error. CR3-1-3-4,4-22-2,9-1-4,15-10-2-1,15-15-3,16-17-3. |
| Breeding evolution/promotion and EX13 Rina,29/45/52–53 | Both EX1-013 evolutions meet Blue Lv2/cost0 and draw the actual deck top. B promotes its Lv3 in turn6. Rina's start-Main condition is met by B's battle Digimon with Veemon/Veedramon names, so memory7 becomes8. CR6-4,8-1-3,15-16-13. |

No attack was chosen in this interval. Saved turn5 candidate lists exclude attacks by A's Ulforce under the cannot-suspend grants; no LM-028 Main Delay or same-turn Wisteria Delay appears. All battle Digimon were already unsuspended at the reviewed unsuspend steps, so no becomes-unsuspended observer was omitted. Breeding inherited effects did not observe battle events while their sources remained in breeding.

This is a source-backed prefix review and software verification. It grants **zero completed matches, zero accepted fact-finding credit and zero final-evaluation credit**. No SOURCE files or saved gameplay records were edited.
