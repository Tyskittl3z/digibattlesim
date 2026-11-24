"""Resolve pinned Comprehensive Rules for the active imported matchup."""
import json
from pathlib import Path

from context_runtime import OfficialEvidence
from match_context import require


_LEGACY_INDEX = 'RULES/matchups/123129-vs-124303/SOURCE_INDEX.json'
_VERSIONS = {
    'a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271': '4.3',
    '4c1c601dd9309772a4c97285f443e0c72065246bd4198931c5c06cd3fb0913c1': '4.4',
}


def rules_version(context):
    source = context.to_dict()['rules'].get('official_source')
    return _VERSIONS.get(source.get('sha256')) if isinstance(source, dict) else '4.3'


def versioned_locator(context, locator):
    version = rules_version(context)
    if version and isinstance(locator, str):
        return locator.replace('Comprehensive rules v4.3:',
                               'Comprehensive rules v' + version + ':')
    return locator


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
    return OfficialEvidence.from_bytes(source['url'], path.read_bytes(), source['sha256'],
                                       versioned_locator(context, locator) if context is not None else locator)
