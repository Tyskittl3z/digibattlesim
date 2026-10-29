"""Real offline-browser checks; no network or simulator results are fabricated."""
import hashlib
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import unittest
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'APP/DeckCompare.html'


class BrowserAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This managed Chromium forbids file:// URLs. Serve the SAME single
        # HTML internally; no assets or external services are used by the app.
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(APP.parent)))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/DeckCompare.html'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(executable_path='/usr/bin/chromium',
                                                     headless=True, args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.context = self.browser.new_context(accept_downloads=True, viewport={'width': 1440, 'height': 1080})
        self.page = self.context.new_page()
        self.errors, self.external = [], []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('request', lambda request: self.external.append(request.url)
                     if request.url.startswith(('http:', 'https:')) and not request.url.startswith(self.url.rsplit('/', 1)[0] + '/') else None)
        self.page.goto(self.url)

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.assertEqual(self.external, [])
        self.context.close()

    def samples(self):
        self.page.get_by_role('button', name='Try the sample decks').click()
        self.page.locator('#card-rows tr').first.wait_for()

    def report(self):
        with self.page.expect_download() as event:
            self.page.get_by_role('button', name='Save after-report').click()
        downloaded = event.value
        text = Path(downloaded.path()).read_text()
        data = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', text, re.S)
        self.assertIsNotNone(data)
        return json.loads(data[1])

    def test_samples_compare_and_save_complete_after_report_despite_filter(self):
        self.samples()
        self.page.screenshot(path='/tmp/digimon-deck-app-desktop.png', full_page=True)
        self.assertEqual(self.page.locator('#card-rows tr').count(), 41)
        self.assertIn('50 main + 4 eggs', self.page.locator('#feedbackA').inner_text())
        self.page.get_by_role('searchbox', name='Search cards').fill('Elecmon')
        self.assertEqual(self.page.locator('#card-rows tr').count(), 2)
        report = self.report()
        self.assertEqual(len(report['statistics']['comparison']['rows']), 41)
        self.assertEqual(report['statistics']['A']['total'], 54)
        raw = (ROOT / 'DECKS/JUPITERMON.txt').read_text()
        self.assertEqual(report['inputs']['A']['raw_text'], raw)
        self.assertEqual(report['inputs']['A']['raw_sha256'], hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(report['simulation']['matches_played'], 0)
        self.assertIsNone(report['simulation']['win_rate'])
        self.assertEqual(report['simulation']['logs'], [])
        self.page.get_by_role('tab', name='Head-to-head').click()
        judge_text = self.page.locator('#judge-layers').inner_text()
        self.assertIn('Justitia', judge_text)
        self.assertIn('Dike', judge_text)
        self.assertIn('Týr', judge_text)

    def test_actual_two_file_drag_drop_and_swap(self):
        a = (ROOT / 'DECKS/JUPITERMON.txt').read_text()
        b = (ROOT / 'DECKS/AMATERASUMON_TOHO.txt').read_text()
        self.page.evaluate('''([a,b]) => {
          const dt = new DataTransfer();
          dt.items.add(new File([a], 'first.txt', {type:'text/plain'}));
          dt.items.add(new File([b], 'second.txt', {type:'text/plain'}));
          document.querySelector('.drop-target').dispatchEvent(new DragEvent('drop', {bubbles:true,cancelable:true,dataTransfer:dt}));
        }''', [a, b])
        self.page.wait_for_function("document.querySelector('#textB').value.includes('Amaterasumon')")
        self.assertEqual(self.page.locator('#card-rows tr').count(), 41)
        self.page.get_by_role('button', name='Swap A and B').click()
        self.assertEqual(self.page.locator('#textA').input_value(), b)
        self.assertEqual(self.page.locator('#metaA').inner_text(), 'second.txt')

    def test_unknown_data_and_broken_import_remain_explicit(self):
        self.samples()
        self.page.locator('#textA').fill('4 Agumon BT1-010')
        self.assertIn('BT1-010', self.page.locator('#data-note').inner_text())
        self.assertIn('4 without card data', self.page.locator('#feedbackA').inner_text())
        self.page.get_by_role('tab', name='Head-to-head').click()
        self.assertIn('not been verified', self.page.locator('#simulation-message').inner_text())
        self.page.locator('#textA').fill('not a valid deck row')
        report = self.report()
        self.assertEqual(report['simulation']['status'], 'INPUT_ERRORS')
        self.assertIsNone(report['statistics'])
        self.assertEqual(report['inputs']['A']['raw_text'], 'not a valid deck row')

    def test_keyboard_browse_tabs_clear_and_mobile_layout(self):
        with self.page.expect_file_chooser() as event:
            self.page.get_by_role('button', name='Choose or drop deck A text file').click()
        event.value.set_files(ROOT / 'DECKS/JUPITERMON.txt')
        self.page.wait_for_function("document.querySelector('#feedbackA').textContent.includes('54 cards')")
        self.samples()
        self.page.get_by_role('tab', name='Deck comparison').focus()
        self.page.keyboard.press('ArrowRight')
        self.assertEqual(self.page.locator('#tab-simulation').get_attribute('aria-selected'), 'true')
        self.page.keyboard.press('ArrowLeft')
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        self.page.screenshot(path='/tmp/digimon-deck-app-mobile.png', full_page=True)
        self.page.get_by_role('button', name='Clear deck A', exact=True).click()
        self.assertTrue(self.page.locator('#save-report').is_disabled())
        self.assertTrue(self.page.locator('#empty-state').is_visible())

    def test_uploaded_markup_stays_literal_text(self):
        self.samples()
        self.page.locator('#textA').fill('4 <img src=x onerror=alert(1)> BT1-010')
        self.assertEqual(self.page.locator('img').count(), 0)
        self.assertIn('<img', self.page.locator('#card-rows').inner_text())
        report = self.report()
        self.assertIn('<img', report['inputs']['A']['raw_text'])

    def test_uploaded_bom_and_original_byte_hash_are_preserved(self):
        self.samples()
        raw = b'\xef\xbb\xbf' + (ROOT / 'DECKS/JUPITERMON.txt').read_bytes().replace(b'\n', b'\r\n')
        self.page.locator('#fileA').set_input_files({'name': 'bom.txt', 'mimeType': 'text/plain', 'buffer': raw})
        self.page.wait_for_function("document.querySelector('#metaA').textContent === 'bom.txt'")
        report = self.report()
        self.assertTrue(report['inputs']['A']['raw_text'].startswith('\ufeff'))
        self.assertEqual(report['inputs']['A']['original_file_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(report['inputs']['A']['raw_sha256'], hashlib.sha256(raw).hexdigest())


if __name__ == '__main__':
    unittest.main()
