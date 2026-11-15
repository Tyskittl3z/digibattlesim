# Game0000: saved return resolved

Original seed: 12017913134550805276. Historical random-reference choices are preserved.
Only the saved return was newly resolved; no player policy was invoked. All match/bot credits: 0.
Paused at B turn10, memory -1, END_OF_TURN. No ratings assigned.

| Step | Turn | Player | Command / saved choice | Memory before | Observed result |
|---:|---:|---|---|---:|---|
|0|0|A|BEGIN_PREPARATION {}|0|EXPERIMENTAL_RESOLVED|
|1|0|A|REDRAW_CHOICE {"redraw": true}|0|INITIAL_HANDS|
|2|0|B|REDRAW_CHOICE {"redraw": false}|0|START_OF_TURN|
|3|1|A|ADVANCE_PHASE {}|0|TURN_START_EFFECTS|
|4|1|A|ADVANCE_PHASE {}|0|DRAW|
|5|1|A|ADVANCE_PHASE {}|0|BREEDING|
|6|1|A|BREEDING_CHOICE {"action": "skip", "kind": "BREEDING_CHOICE"}|0|MAIN|
|7|1|A|PLAY_CARD {"hand_key": "A:BT11-112#2", "kind": "PLAY_CARD", "legality": "PRINTED_PAYABLE_NOT_FULL_LEGALITY", "printed_cost": 3}|0|EXPERIMENTAL_RESOLVED|
|8|1|A|RESOLVE_PENDING {"choice": null, "pending_id": "effect-1"}|-3|NO_ELIGIBLE_TARGET|
|9|1|A|FINISH_TURN {}|-3|START_OF_TURN|
|10|2|B|ADVANCE_PHASE {}|3|TURN_START_EFFECTS|
|11|2|B|ADVANCE_PHASE {}|3|DRAW|
|12|2|B|ADVANCE_PHASE {}|3|BREEDING|
|13|2|B|BREEDING_CHOICE {"action": "skip", "kind": "BREEDING_CHOICE"}|3|MAIN|
|14|2|B|PLAY_CARD {"hand_key": "B:EX13-022#3", "kind": "PLAY_CARD", "legality": "PRINTED_PAYABLE_NOT_FULL_LEGALITY", "printed_cost": 7}|3|EXPERIMENTAL_RESOLVED|
|15|2|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-2"}|-4|OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION|
|16|2|B|FINISH_TURN {}|-4|START_OF_TURN|
|17|3|A|ADVANCE_PHASE {}|4|TURN_START_EFFECTS|
|18|3|A|ADVANCE_PHASE {}|4|DRAW|
|19|3|A|ADVANCE_PHASE {}|4|BREEDING|
|20|3|A|BREEDING_CHOICE {"action": "skip", "kind": "BREEDING_CHOICE"}|4|MAIN|
|21|3|A|USE_OPTION {"hand_key": "A:LM-028#1", "kind": "UNKNOWN_OPTION_ACTION", "legality": "UNVERIFIED_OPTION_ACTION", "printed_cost": 2}|4|EXPERIMENTAL_RESOLVED|
|22|3|A|RESOLVE_PENDING {"choice": null, "pending_id": "effect-3"}|2|EXPERIMENTAL_RESOLVED|
|23|3|A|PLAY_CARD {"hand_key": "A:BT12-029#2", "kind": "PLAY_CARD", "legality": "PRINTED_PAYABLE_NOT_FULL_LEGALITY", "printed_cost": 12}|2|EXPERIMENTAL_RESOLVED|
|24|3|A|FINISH_TURN {}|-10|START_OF_TURN|
|25|4|B|ADVANCE_PHASE {}|10|TURN_START_EFFECTS|
|26|4|B|ADVANCE_PHASE {}|10|DRAW|
|27|4|B|ADVANCE_PHASE {}|10|BREEDING|
|28|4|B|BREEDING_CHOICE {"action": "hatch", "kind": "BREEDING_CHOICE"}|10|MAIN|
|29|4|B|BREEDING_EVOLUTION {"basis": "PRINTED_NORMAL", "cost": 0, "definition_sha256": "1f8d254a3e180ff961836b2ccf2217cdd7fa207e58ddef3b8c03ba9279e73b41", "hand_key": "B:EX1-013#3", "kind": "BREEDING_EVOLUTION", "legality": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY", "printed_condition": "Blue 0 from Lv.2", "route_index": 0, "source_key": "B:EX13-002#1", "status": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY"}|10|MAIN|
|30|4|B|PLAY_CARD {"hand_key": "B:EX13-022#1", "kind": "PLAY_CARD", "legality": "PRINTED_PAYABLE_NOT_FULL_LEGALITY", "printed_cost": 7}|10|EXPERIMENTAL_RESOLVED|
|31|4|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-4"}|3|OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION|
|32|4|B|PLAY_CARD {"hand_key": "B:EX13-069#4", "kind": "PLAY_CARD", "legality": "PRINTED_PAYABLE_NOT_FULL_LEGALITY", "printed_cost": 3}|3|EXPERIMENTAL_RESOLVED|
|33|4|B|RESOLVE_PENDING {"choice": "A:BT12-029#2", "pending_id": "effect-6"}|0|RESTRICTION_APPLIED|
|34|4|B|RESOLVE_PENDING {"choice": "A:BT12-029#2", "pending_id": "effect-5"}|0|RESTRICTION_APPLIED|
|35|4|B|PLAY_CARD {"hand_key": "B:BT11-023#2", "kind": "PLAY_CARD", "legality": "PRINTED_PAYABLE_NOT_FULL_LEGALITY", "printed_cost": 3}|0|EXPERIMENTAL_RESOLVED|
|36|4|B|RESOLVE_PENDING {"choice": {"bottom_order": ["B:EX13-069#2"], "selected": ["B:BT22-023#1", "B:BT11-112#3"]}, "pending_id": "effect-7"}|-3|EXPERIMENTAL_RESOLVED|
|37|4|B|FINISH_TURN {}|-3|START_OF_TURN|
|38|5|A|ADVANCE_PHASE {}|3|TURN_START_EFFECTS|
|39|5|A|RESOLVE_PENDING {"choice": {"activate": false}, "pending_id": "effect-8"}|3|DELAY_DECLINED|
|40|5|A|ADVANCE_PHASE {}|3|DRAW|
|41|5|A|ADVANCE_PHASE {}|3|BREEDING|
|42|5|A|BREEDING_CHOICE {"action": "hatch", "kind": "BREEDING_CHOICE"}|3|MAIN|
|43|5|A|USE_OPTION {"hand_key": "A:LM-034#1", "kind": "USE_OPTION", "legality": "UNVERIFIED_OPTION_ACTION", "printed_cost": 3}|3|EXPERIMENTAL_RESOLVED|
|44|5|A|RESOLVE_PENDING {"choice": {"bottom_order": ["A:EX1-013#3", "A:EX13-022#2"], "selected": ["A:EX13-022#1"]}, "pending_id": "effect-9"}|0|EXPERIMENTAL_RESOLVED|
|45|5|A|BREEDING_EVOLUTION {"basis": "PRINTED_NORMAL", "cost": 0, "definition_sha256": "1f8d254a3e180ff961836b2ccf2217cdd7fa207e58ddef3b8c03ba9279e73b41", "hand_key": "A:EX1-013#2", "kind": "BREEDING_EVOLUTION", "legality": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY", "printed_condition": "Blue 0 from Lv.2", "route_index": 0, "source_key": "A:EX13-002#2", "status": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY"}|0|MAIN|
|46|5|A|PLAY_CARD {"hand_key": "A:EX13-022#1", "kind": "PLAY_CARD", "legality": "PRINTED_PAYABLE_NOT_FULL_LEGALITY", "printed_cost": 7}|0|EXPERIMENTAL_RESOLVED|
|47|5|A|RESOLVE_PENDING {"choice": null, "pending_id": "effect-10"}|-7|OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION|
|48|5|A|FINISH_TURN {}|-7|START_OF_TURN|
|49|6|B|ADVANCE_PHASE {}|7|TURN_START_EFFECTS|
|50|6|B|ADVANCE_PHASE {}|7|DRAW|
|51|6|B|ADVANCE_PHASE {}|7|BREEDING|
|52|6|B|BREEDING_CHOICE {"action": "promote", "kind": "BREEDING_CHOICE"}|7|MAIN|
|53|6|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-11"}|7|EXPERIMENTAL_RESOLVED|
|54|6|B|BATTLE_EVOLUTION {"basis": "PRINTED_NORMAL", "cost": 2, "definition_sha256": "024e9c9291e563b9559205619fd19560f627ba0a22973f21707b08b45aba8dad", "hand_key": "B:BT22-022#1", "kind": "BATTLE_EVOLUTION", "legality": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY", "printed_condition": "Blue 2 from Lv.3", "route_index": 0, "source_key": "B:EX1-013#3", "status": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY"}|8|EXPERIMENTAL_RESOLVED|
|55|6|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-12"}|6|OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION|
|56|6|B|BATTLE_EVOLUTION {"basis": "PRINTED_NORMAL", "cost": 3, "definition_sha256": "65bfa05c9838899ee391c5168eff33a01cbabfc29e6611b08b8cb3b280715c85", "hand_key": "B:BT22-023#1", "kind": "BATTLE_EVOLUTION", "legality": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY", "printed_condition": "Blue 3 from Lv.4", "route_index": 0, "source_key": "B:BT22-022#1", "status": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY"}|6|EXPERIMENTAL_RESOLVED|
|57|6|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-13"}|3|NO_ELIGIBLE_TARGET|
|58|6|B|DECLARE_ATTACK {"attacker": "B:EX13-022#1", "kind": "DECLARE_ATTACK", "target": "PLAYER"}|3|EXPERIMENTAL_RESOLVED|
|59|6|B|RESOLVE_PENDING {"choice": "B:EX13-069#3", "pending_id": "effect-14"}|3|TAMER_PLAYED_WITHOUT_PAYING_COST|
|60|6|B|RESOLVE_PENDING {"choice": false, "pending_id": "effect-17"}|3|OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION|
|61|6|B|RESOLVE_PENDING {"choice": "A:EX13-022#1", "pending_id": "effect-16"}|3|RESTRICTION_APPLIED|
|62|6|B|RESOLVE_PENDING {"choice": "A:BT12-029#2", "pending_id": "effect-15"}|3|RESTRICTION_APPLIED|
|63|6|A|COUNTER_CHOICE {"card": null, "status": "EXPLICIT_DECLINE"}|3|EXPERIMENTAL_RESOLVED|
|64|6|A|BLOCK_CHOICE {"card": null, "status": "EXPLICIT_NO_BLOCK_IN_PLAIN_SCOPE"}|3|EXPERIMENTAL_RESOLVED|
|65|6|B|CONFIRM_ATTACK {}|3|EXPERIMENTAL_RESOLVED|
|66|6|B|END_ATTACK {}|3|EXPERIMENTAL_RESOLVED|
|67|6|B|DECLARE_ATTACK {"attacker": "B:BT11-023#2", "kind": "DECLARE_ATTACK", "target": "PLAYER"}|3|EXPERIMENTAL_RESOLVED|
|68|6|A|COUNTER_CHOICE {"card": null, "status": "EXPLICIT_DECLINE"}|3|EXPERIMENTAL_RESOLVED|
|69|6|A|BLOCK_CHOICE {"card": null, "status": "EXPLICIT_NO_BLOCK_IN_PLAIN_SCOPE"}|3|EXPERIMENTAL_RESOLVED|
|70|6|B|CONFIRM_ATTACK {}|3|EXPERIMENTAL_RESOLVED|
|71|6|B|END_ATTACK {}|3|EXPERIMENTAL_RESOLVED|
|72|6|B|DECLARE_ATTACK {"attacker": "B:EX13-022#3", "kind": "DECLARE_ATTACK", "target": "PLAYER"}|3|EXPERIMENTAL_RESOLVED|
|73|6|B|RESOLVE_PENDING {"choice": "B:BT11-112#3", "pending_id": "effect-18"}|3|TAMER_PLAYED_WITHOUT_PAYING_COST|
|74|6|B|RESOLVE_PENDING {"choice": "B:EX13-022#3", "pending_id": "effect-19"}|3|GRANT_APPLIED|
|75|6|A|COUNTER_CHOICE {"card": null, "status": "EXPLICIT_DECLINE"}|3|EXPERIMENTAL_RESOLVED|
|76|6|A|BLOCK_CHOICE {"card": null, "status": "EXPLICIT_NO_BLOCK_IN_PLAIN_SCOPE"}|3|EXPERIMENTAL_RESOLVED|
|77|6|B|CONFIRM_ATTACK {}|3|EXPERIMENTAL_RESOLVED|
|78|6|A|RESOLVE_PENDING {"choice": "B:EX13-022#3", "pending_id": "effect-20"}|3|RESTRICTION_APPLIED|
|79|6|B|END_ATTACK {}|3|EXPERIMENTAL_RESOLVED|
|80|6|B|PLAY_CARD {"hand_key": "B:EX13-019#1", "kind": "PLAY_CARD", "legality": "PRINTED_PAYABLE_NOT_FULL_LEGALITY", "printed_cost": 6}|3|EXPERIMENTAL_RESOLVED|
|81|6|B|FINISH_TURN {}|-3|END_OF_TURN|
|82|6|B|RESOLVE_PENDING {"choice": "B:EX13-022#3", "pending_id": "effect-21"}|-3|UNSUSPEND_SELECTED|
|83|6|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-24"}|-3|EXPERIMENTAL_RESOLVED|
|84|6|B|RESOLVE_PENDING {"choice": false, "pending_id": "effect-22"}|-2|SUSPENSION_DECLINED|
|85|6|B|RESOLVE_PENDING {"choice": false, "pending_id": "effect-23"}|-2|SUSPENSION_DECLINED|
|86|6|B|FINISH_TURN {}|-2|START_OF_TURN|
|87|7|A|ADVANCE_PHASE {}|2|TURN_START_EFFECTS|
|88|7|A|RESOLVE_PENDING {"choice": {"activate": true, "play_key": null, "return_key": "A:P-138#4"}, "pending_id": "effect-25"}|2|DELAY_ACTIVATED|
|89|7|A|ADVANCE_PHASE {}|2|DRAW|
|90|7|A|ADVANCE_PHASE {}|2|BREEDING|
|91|7|A|BREEDING_CHOICE {"action": "skip", "kind": "BREEDING_CHOICE"}|2|MAIN|
|92|7|A|RESOLVE_PENDING {"choice": null, "pending_id": "effect-26"}|2|EXPERIMENTAL_RESOLVED|
|93|7|A|BATTLE_EVOLUTION {"basis": "PRINTED_NORMAL", "cost": 4, "definition_sha256": "ff783d6b6371c763e5febbd614131de15f69a0293a7603b05f73a2b0c785ad5b", "hand_key": "A:BT11-032#1", "kind": "BATTLE_EVOLUTION", "legality": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY", "printed_condition": "Blue 4 from Lv.5", "route_index": 0, "source_key": "A:EX13-022#1", "status": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY"}|3|EXPERIMENTAL_RESOLVED|
|94|7|A|RESOLVE_PENDING {"choice": "A:BT11-112#3", "pending_id": "effect-27"}|-1|TAMER_PLAYED_WITHOUT_PAYING_COST|
|95|7|A|RESOLVE_PENDING {"choice": "A:BT12-029#2", "pending_id": "effect-28"}|-1|GRANT_APPLIED|
|96|7|A|RESOLVE_PENDING {"choice": null, "pending_id": "effect-29"}|-1|MANDATORY_SELF_UNSUSPEND|
|97|7|A|FINISH_TURN {}|-1|START_OF_TURN|
|98|8|B|ADVANCE_PHASE {}|1|TURN_START_EFFECTS|
|99|8|B|ADVANCE_PHASE {}|1|UNSUSPEND|
|100|8|B|RESOLVE_PENDING {"choice": false, "pending_id": "effect-31"}|1|SUSPENSION_DECLINED|
|101|8|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-32"}|1|EXPERIMENTAL_RESOLVED|
|102|8|B|RESOLVE_PENDING {"choice": true, "pending_id": "effect-30"}|2|DRAW_COMPLETE_EVOLUTION_PENDING|
|103|8|B|RESOLVE_PENDING {"choice": {"hand_key": "B:EX13-023#1", "route_index": 0, "source_key": "B:BT22-023#1"}, "pending_id": "effect-33"}|2|AFTER_DRAW_EVOLUTION_COMPLETE|
|104|8|B|RESOLVE_PENDING {"choice": "B:EX13-023#1", "pending_id": "effect-34"}|1|EXPERIMENTAL_RESOLVED|
|105|8|B|RESOLVE_PENDING {"choice": true, "pending_id": "effect-36"}|1|OPTIONAL_UNSUSPEND_SELECTED|
|106|8|B|RESOLVE_PENDING {"choice": false, "pending_id": "effect-38"}|1|SUSPENSION_COST_NOT_PAYABLE|
|107|8|B|RESOLVE_PENDING {"choice": true, "pending_id": "effect-39"}|1|DRAW_COMPLETE_EVOLUTION_PENDING|
|108|8|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-40"}|1|AFTER_DRAW_EVOLUTION_COMPLETE|
|109|8|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-37"}|1|RINA_REACTIVATION_DECLINED|
|110|8|B|RESOLVE_PENDING {"choice": false, "pending_id": "effect-35"}|1|OPTIONAL_RETURN_DECLINED|
|111|8|B|ADVANCE_PHASE {}|1|DRAW|
|112|8|B|ADVANCE_PHASE {}|1|BREEDING|
|113|8|B|BREEDING_CHOICE {"action": "skip", "kind": "BREEDING_CHOICE"}|1|MAIN|
|114|8|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-42"}|1|EXPERIMENTAL_RESOLVED|
|115|8|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-41"}|2|EXPERIMENTAL_RESOLVED|
|116|8|B|BATTLE_EVOLUTION {"basis": "PRINTED_NORMAL", "cost": 4, "definition_sha256": "ff783d6b6371c763e5febbd614131de15f69a0293a7603b05f73a2b0c785ad5b", "hand_key": "B:BT11-032#1", "kind": "BATTLE_EVOLUTION", "legality": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY", "printed_condition": "Blue 4 from Lv.5", "route_index": 0, "source_key": "B:EX13-022#1", "status": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY"}|3|EXPERIMENTAL_RESOLVED|
|117|8|B|RESOLVE_PENDING {"choice": "B:BT11-112#2", "pending_id": "effect-43"}|-1|TAMER_PLAYED_WITHOUT_PAYING_COST|
|118|8|B|RESOLVE_PENDING {"choice": false, "pending_id": "effect-46"}|-1|OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION|
|119|8|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-47"}|-1|MANDATORY_SELF_UNSUSPEND|
|120|8|B|RESOLVE_PENDING {"choice": "A:BT12-029#2", "pending_id": "effect-45"}|-1|RESTRICTION_APPLIED|
|121|8|B|RESOLVE_PENDING {"choice": "B:EX13-022#3", "pending_id": "effect-44"}|-1|GRANT_APPLIED|
|122|8|B|FINISH_TURN {}|-1|START_OF_TURN|
|123|9|A|ADVANCE_PHASE {}|1|TURN_START_EFFECTS|
|124|9|A|ADVANCE_PHASE {}|1|DRAW|
|125|9|A|ADVANCE_PHASE {}|1|BREEDING|
|126|9|A|BREEDING_CHOICE {"action": "promote", "kind": "BREEDING_CHOICE"}|1|MAIN|
|127|9|A|RESOLVE_PENDING {"choice": null, "pending_id": "effect-48"}|1|EXPERIMENTAL_RESOLVED|
|128|9|A|BATTLE_EVOLUTION {"basis": "PRINTED_NORMAL", "cost": 2, "definition_sha256": "024e9c9291e563b9559205619fd19560f627ba0a22973f21707b08b45aba8dad", "hand_key": "A:BT22-022#1", "kind": "BATTLE_EVOLUTION", "legality": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY", "printed_condition": "Blue 2 from Lv.3", "route_index": 0, "source_key": "A:EX1-013#2", "status": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY"}|2|EXPERIMENTAL_RESOLVED|
|129|9|A|RESOLVE_PENDING {"choice": null, "pending_id": "effect-49"}|0|CONDITION_NOT_MET|
|130|9|A|PASS_TURN {"kind": "PASS_TURN"}|0|END_OF_TURN|
|131|9|A|FINISH_TURN {}|-3|START_OF_TURN|
|132|10|B|ADVANCE_PHASE {}|3|TURN_START_EFFECTS|
|133|10|B|ADVANCE_PHASE {}|3|DRAW|
|134|10|B|ADVANCE_PHASE {}|3|BREEDING|
|135|10|B|BREEDING_CHOICE {"action": "hatch", "kind": "BREEDING_CHOICE"}|3|MAIN|
|136|10|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-51"}|3|EXPERIMENTAL_RESOLVED|
|137|10|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-50"}|4|EXPERIMENTAL_RESOLVED|
|138|10|B|BREEDING_EVOLUTION {"basis": "PRINTED_NORMAL", "cost": 0, "definition_sha256": "2b087e49a70979928e01b0527f9ce8533b55114ae4323024f62e643b90108fa9", "hand_key": "B:BT11-023#4", "kind": "BREEDING_EVOLUTION", "legality": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY", "printed_condition": "Blue 0 from Lv.2", "route_index": 0, "source_key": "B:EX13-002#3", "status": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY"}|5|MAIN|
|139|10|B|DECLARE_ATTACK {"attacker": "B:BT11-032#1", "kind": "DECLARE_ATTACK", "target": "PLAYER"}|5|EXPERIMENTAL_RESOLVED|
|140|10|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-53"}|5|RINA_REACTIVATION_DECLINED|
|141|10|B|RESOLVE_PENDING {"choice": "BT11-032.play_blue_tamer", "pending_id": "effect-54"}|5|RINA_WHEN_DIGIVOLVING_REACTIVATED|
|142|10|B|RESOLVE_PENDING {"choice": null, "pending_id": "effect-55"}|5|OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION|
|143|10|B|RESOLVE_PENDING {"choice": false, "pending_id": "effect-52"}|5|OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION|
|144|10|A|COUNTER_CHOICE {"card": null, "status": "EXPLICIT_DECLINE"}|5|EXPERIMENTAL_RESOLVED|
|145|10|A|BLOCK_CHOICE {"card": null, "status": "EXPLICIT_NO_BLOCK_IN_PLAIN_SCOPE"}|5|EXPERIMENTAL_RESOLVED|
|146|10|B|CONFIRM_ATTACK {}|5|EXPERIMENTAL_RESOLVED|
|147|10|B|END_ATTACK {}|5|EXPERIMENTAL_RESOLVED|
|148|10|B|PLAY_CARD {"hand_key": "B:BT11-023#3", "kind": "PLAY_CARD", "legality": "PRINTED_PAYABLE_NOT_FULL_LEGALITY", "printed_cost": 3}|5|EXPERIMENTAL_RESOLVED|
|149|10|B|RESOLVE_PENDING {"choice": {"bottom_order": ["B:P-138#3"], "selected": ["B:EX13-022#4", "B:BT22-085#1"]}, "pending_id": "effect-56"}|2|EXPERIMENTAL_RESOLVED|
|150|10|B|BATTLE_EVOLUTION {"basis": "PRINTED_SPECIAL", "cost": 3, "definition_sha256": "65bfa05c9838899ee391c5168eff33a01cbabfc29e6611b08b8cb3b280715c85", "hand_key": "B:BT22-023#2", "kind": "BATTLE_EVOLUTION", "legality": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY", "printed_condition": "[Digivolve] Lv.4 w/[CS] trait: Cost 3", "route_index": 1, "source_key": "B:EX13-019#1", "status": "PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY"}|2|EXPERIMENTAL_RESOLVED|
|151|10|B|RESOLVE_PENDING {"choice": "A:BT22-022#1", "pending_id": "effect-57"}|-1|RETURNED_TO_DECK_BOTTOM; BT22-022 to A deck bottom; EX13-002 and EX1-013 to A trash; opens END_OF_TURN|
