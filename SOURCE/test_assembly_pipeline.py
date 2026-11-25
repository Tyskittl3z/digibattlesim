"""A live Assembly choice stays visible and auditable across bot and judge."""
import unittest

from board_text_player import BoardTextPlayerBot
from context_runtime import ContextRuntime
from field_tracker import FieldTracker
from imported_attempts import main_candidates,_apply
from interaction_learning import LearningState,verify_decision_input
from judge_ledger import judge_action
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class AssemblyPipelineTests(unittest.TestCase):
    def test_current_trash_assembly_choice_passes_bot_and_judge(self):
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime=ContextRuntime(context,22,'A',build_selected_registry(context,ROOT),allow_experimental=True)
        runtime.state.phase='MAIN';runtime.state.turn=3;runtime.state.memory=4
        def move(number,zone):
            deck=runtime.state.zones['A']['deck']
            card=next(card for card in deck if card.card_number==number)
            deck.remove(card);runtime.state.zones['A'][zone].append(card)
            return card.key
        top=move('EX13-023','hand')
        materials=[move(number,'trash') for number in ('EX13-017','P-138','BT22-023')]
        candidates=main_candidates(runtime,'A',ROOT)
        action=next(choice for choice in candidates if choice['kind']=='ASSEMBLY_PLAY'
                    and choice['hand_key']==top and choice['materials']==materials)
        before=runtime.snapshot();tracker=FieldTracker(context);tracker.start(before)
        bot=BoardTextPlayerBot(context,'A',LearningState(),25,None)
        selected=bot.choose(runtime.public_view('A'),[action],decision={'kind':'MAIN_ACTION'})
        self.assertEqual(selected,action)
        self.assertTrue(verify_decision_input(bot.decision_log[-1],runtime.public_view('A'),
                                              context,bot.manifest()))
        result=_apply(runtime,'ASSEMBLY_PLAY','A',action,ROOT)
        receipt=judge_action(runtime,{'command':'ASSEMBLY_PLAY','seat':'A','args':action,
            'status':'EXPERIMENTAL_RESOLVED'},before,runtime.snapshot(),result,root=ROOT,
            tracker=tracker)
        self.assertTrue(receipt['accepted'],receipt)
        runtime.verify()


if __name__=='__main__':unittest.main()
