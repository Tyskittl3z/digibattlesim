# Game 0050: two inherited return replacements

The V1 styled campaign completed Games 0000–0049 on the original fixed source. Game 0050 reached a judge halt after 153 accepted commands at seed 968916522565182642. The saved segment and exact replay remain unchanged at `game-0050/segment-0000.json.gz` and `replay-0000.json`. The original build is pinned at Git tag `styled-50-halt-v1`.

The selected action was Bot B's BT11-032 unsuspend return targeting `A:BT22-023#1`. That stack had EX13-017 and BT22-022 beneath it, and was unsuspended. Both inherited texts offer a once-per-turn suspension to prevent this Digimon from leaving by an opponent effect. The old BT11-032 handler called a helper that halts when two such sources are present.

The source repair queues both printed inherited effects for Bot A. Under Comprehensive Rules v4.3 sections 15-4-3-4 and 15-4-3-5, simultaneous effects are chosen one at a time by their controller. If either replacement suspends the Digimon, the return is prevented and the other pending replacement is cancelled. If both are declined, the return completes. Focused tests cover either acceptance, both declines, and the BT12-029 return path. The printed card text is in the locked official cardlist snapshots for EX13-017 and BT22-022.

`game-0050/source-repair-0001-migrated.json.gz` records the exact accepted-prefix migration and source hashes. `source-repair-0001-retried.json.gz` records the original failed choice succeeding as command 154, with both replacement choices pending. `source-repair-0001-receipt.json` ties the records to the original tag and exact replay. These are software repair records, not a rules certification or completed V1 Game 0050.

The repaired source changes the V1 fixed build. V1 remains archived at 50 completed software games plus this halt. The new `ARTIFACTS/styled-prospective-60-2026-11-22-v2/` campaign starts from an empty model under a new seed schedule and repaired source lock. Its games cannot be mixed with V1 to make a 60-game total.
