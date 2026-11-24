"""Resolve pinned Comprehensive Rules for the active imported matchup."""
import json
from pathlib import Path

from context_runtime import OfficialEvidence
from match_context import require


_LEGACY_INDEX = 'RULES/matchups/123129-vs-124303/SOURCE_INDEX.json'


def comprehensive_rules(context, root, locator):
    root = Path(root).resolve()
    raw = context.to_dict()['rules'] if context is not None else {}
    source = raw.get('official_source')
    if source is None:
        # Historical experimental contexts predate an explicit rules-source
        # selection. Strict adjudication never uses this compatibility path.
        index = json.loads((root / _LEGACY_INDEX).read_bytes())
        source = next(item for item in index['sources'] if item['id'] == 'rules')
    require(isinstance(source, dict), 'Official rules source required')
    for key in ('url', 'file', 'sha256'):
        require(isinstance(source.get(key), str) and source[key], 'Official rules ' + key + ' required')
    path = (root / source['file']).resolve()
    base = (root / 'RULES').resolve()
    require(path.is_relative_to(base) and base.is_relative_to(root), 'Official rules source escapes RULES')
    return OfficialEvidence.from_bytes(source['url'], path.read_bytes(), source['sha256'], locator)
