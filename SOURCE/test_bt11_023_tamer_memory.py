"""Encountered BT11-023 inherited trigger when its owner plays a blue Tamer."""
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _load_context_selection
from main_actions import choose_play
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage


class BT11023TamerMemoryTests(unittest.TestCase):
    def test_inherited_veemon_gains_memory_once_after_own_blue_tamer_play(self):
        context, _, _ = _load_context_selection(
            ROOT, 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 23011, 'B', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        stage(runtime, 'B', ['BT11-023', 'EX13-022'])
        card = next(card for card in runtime.state.zones['B']['deck']
                    if card.card_number == 'BT11-112')
        runtime.state.zones['B']['deck'].remove(card)
        runtime.state.zones['B']['hand'].append(card)
        runtime.state.phase = 'MAIN'
        runtime.state.memory = 6

        choose_play(runtime, 'B', card.key, ROOT)
        self.assertEqual(runtime.state.memory, 3)
        effect = next(item for item in pending_options(runtime, 'B')
                      if item['effect_id'] == 'BT11-023.blue_tamer_memory')
        self.assertEqual((effect['seat'], effect['field'], effect['trigger']['played_card']),
                         ('B', 'inherited_text', card.key))
        result = resolve_pending(runtime, 'B', effect['id'], None)
        self.assertEqual((result['memory_before'], result['memory_after']), (3, 4))
        self.assertEqual(runtime.state.memory, 4)
        self.assertFalse(any(item['effect_id'] == 'BT11-023.blue_tamer_memory'
                             for item in pending_options(runtime, 'B')))
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
