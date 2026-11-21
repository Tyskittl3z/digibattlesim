"""A source-only migration can review the encountered BT20-102 mechanic."""
import unittest

from context_runtime import RuntimeHalt
from fresh_repair_migration import _differences


OLD_MIGRATION = 'c95e2ce0998e8b5902063b35432a1cfaf94f4cd7ac0178437d98c09645346014'


class OmniMigrationScopeTests(unittest.TestCase):
    def test_only_encountered_omni_return_and_shared_return_are_allowed(self):
        before = {'fresh_repair_migration.py': OLD_MIGRATION,
                  'omni_return_effect.py': 'old-omni',
                  'return_effects.py': 'old-return'}
        after = {'fresh_repair_migration.py': 'new-migration',
                 'omni_return_effect.py': 'new-omni',
                 'return_effects.py': 'new-return'}
        changes = {name: {'before': before[name], 'after': after[name]} for name in before}
        self.assertEqual(_differences(before, after, changes), changes)
        before['interaction_learning.py'] = 'old-policy'
        after['interaction_learning.py'] = 'new-policy'
        changes['interaction_learning.py'] = {
            'before': 'old-policy', 'after': 'new-policy'}
        with self.assertRaisesRegex(RuntimeHalt, 'REPAIR_PROTECTED_SOURCE_CHANGE'):
            _differences(before, after, changes)


if __name__ == '__main__':
    unittest.main()
