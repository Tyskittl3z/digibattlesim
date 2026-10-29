"""Build the offline, single-file comparison app using only supplied metadata."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / 'APP'


def build():
    manifest = json.loads((ROOT / 'SOURCE/EXACT_CARD_MANIFEST.json').read_bytes())
    costs = json.loads((ROOT / 'SOURCE/LOADED_EXACT_COSTS.json').read_bytes())
    catalog = {}
    for deck in manifest['decks'].values():
        for card in deck['card_manifest']:
            catalog[card['card_number']] = {key: card.get(key) for key in ('name', 'type', 'level', 'colors')}
            catalog[card['card_number']]['play_cost'] = costs[card['card_number']]['play_cost']
    sources = ['SOURCE/EXACT_CARD_MANIFEST.json', 'SOURCE/LOADED_EXACT_COSTS.json',
               'DECKS/JUPITERMON.txt', 'DECKS/AMATERASUMON_TOHO.txt']
    sources += ['APP/compare.js', 'APP/ui.js', 'APP/style.css', 'APP/template.html', 'APP/build.py']
    metadata = {'version': '0.2.0', 'catalog': catalog,
                'source_files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources},
                'samples': {
                    'A': {'name': 'Jupitermon', 'text': (ROOT / sources[2]).read_text()},
                    'B': {'name': 'Amaterasumon · Toho', 'text': (ROOT / sources[3]).read_text()},
                }}
    parts = {
        '/* APP_STYLE */': (APP / 'style.css').read_text(),
        '/* APP_DATA */': json.dumps(metadata, ensure_ascii=False).replace('<', '\\u003c'),
        '/* APP_CORE */': (APP / 'compare.js').read_text(),
        '/* APP_UI */': (APP / 'ui.js').read_text(),
    }
    html = (APP / 'template.html').read_text()
    for marker, value in parts.items():
        if html.count(marker) != 1:
            raise ValueError('Missing or duplicate app marker: ' + marker)
        if marker in ('/* APP_CORE */', '/* APP_UI */'):
            # The HTML parser sees script-end tags even inside JS strings.
            value = re.sub(r'</script', lambda _: r'<\/script', value, flags=re.I)
        html = html.replace(marker, value)
    output = APP / 'DeckCompare.html'
    output.write_text(html, encoding='utf-8')
    return output


if __name__ == '__main__':
    output = build()
    print(f'Built {output} ({output.stat().st_size:,} bytes). Open it directly in a browser.')
