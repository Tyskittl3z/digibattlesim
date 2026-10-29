"""Execute syntax checks on the inline scripts in the real built artifact."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import unittest


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.current = {'attrs': dict(attrs), 'text': ''}

    def handle_data(self, text):
        if self.current is not None:
            self.current['text'] += text

    def handle_endtag(self, tag):
        if tag == 'script' and self.current is not None:
            self.scripts.append(self.current)
            self.current = None


class BuildTests(unittest.TestCase):
    def test_built_app_contains_executable_complete_inline_scripts(self):
        app = Path(__file__).resolve().parents[1] / 'DeckCompare.html'
        parser = Scripts()
        parser.feed(app.read_text())
        scripts = [s for s in parser.scripts if s['attrs'].get('type') != 'application/json']
        self.assertEqual(len(scripts), 2)
        for script in scripts:
            result = subprocess.run(['node', '--check'], input=script['text'], text=True,
                                    capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
