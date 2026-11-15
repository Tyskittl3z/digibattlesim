"""Exact experimental capability inputs, independent of the selected deck family.

A path or source ID alone cannot grant gameplay support. Each entry binds the
ordered source IDs and complete composition/definitions/rules identity to a
saved lock. This shares existing primitives, never another matchup's results.
"""
from pathlib import Path

from context_runtime import RuntimeHalt
from match_context import MatchContext


_CONTEXTS = {
    '53f4e043b49fca0bf6e691754098e73774995cfee182e7c8245cf446e2d70733':
        (('123129', '124303'), 'ARTIFACTS/ex13-engine-2026-10-30/context.json'),
    '9dd326339d64f263c7570a33b03e4ab9d57c1cd466ec0fddffcec4d7ea5bcd8d':
        (('123129', '122110'), 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'),
}


def require_selected_context(context, root):
    """Return the matching saved lock or reject before an action mutates state."""
    from matchup_readiness import load_context_file

    try:
        if type(context) is not MatchContext:
            raise ValueError('Validated exact context required')
        context_id = context.matchup_id
        source_ids, relative = _CONTEXTS[context_id]
        if (context.deck_a.source_id, context.deck_b.source_id) != source_ids:
            raise ValueError('Ordered source identities changed')
        root = Path(root).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Context lock escapes root')
        locked = load_context_file(path)
        if (locked.matchup_id != context_id
                or (locked.deck_a.source_id, locked.deck_b.source_id) != source_ids):
            raise ValueError('Saved context lock changed')
        return locked
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
        raise RuntimeHalt('BASIC_BOARD_SELECTED_CONTEXT_REQUIRED') from exc
