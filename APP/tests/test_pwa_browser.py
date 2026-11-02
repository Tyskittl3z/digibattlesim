"""Real Chromium acceptance tests for storage, evidence and offline operation."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import hashlib, json, re, unittest
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]

class PwaTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  class Quiet(SimpleHTTPRequestHandler):
   def log_message(self,*_):pass
   def do_GET(self):
    if getattr(self.server,'fail_asset',False) and self.path.endswith('/chunks/AD1.json'):
     self.send_error(404);return
    super().do_GET()
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'APP')))
  cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.url=f'http://127.0.0.1:{cls.server.server_port}/index.html'
  cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 @classmethod
 def tearDownClass(cls):
  cls.browser.close();cls.pw.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join()
 def setUp(self):
  self.assertTrue((ROOT/'APP/index.html').exists(), 'PWA entry point must exist')
  self.context=self.browser.new_context(accept_downloads=True,viewport={'width':1440,'height':1000});self.page=self.context.new_page();self.errors=[]
  self.page.on('pageerror',lambda e:self.errors.append(str(e)));self.page.goto(self.url)
  self.page.get_by_role('button',name='Load sample decks').wait_for()
  self.page.wait_for_function('window.appReady === true')
 def tearDown(self):
  self.assertEqual(self.errors,[]);self.context.close()
 def samples(self):
  self.page.get_by_role('button',name='Load sample decks').click();self.page.wait_for_function('window.currentReport?.statistics?.A?.main_count === 50')
 def test_samples_export_and_no_invented_results(self):
  self.samples();self.assertEqual(self.page.locator('#card-rows tr').count(),41)
  with self.page.expect_download() as event:self.page.get_by_role('button',name='Download after-report').click()
  s=Path(event.value.path()).read_text();report=json.loads(re.search(r'id="report-data">(.*?)</script>',s,re.S)[1]);self.assertEqual(report['simulation']['matches_played'],0);self.assertIsNone(report['simulation']['win_rate']);self.assertEqual(report['catalog_snapshot']['card_count'],4481);self.assertIn('legality',report)
  self.page.screenshot(path=str(ROOT/'work/pwa-desktop.png'),full_page=True)
 def test_file_bytes_persist_and_restore_after_reload(self):
  self.samples();raw=b'\xef\xbb\xbf4 BT1-010\r\n'
  self.page.locator('#fileA').set_input_files({'name':'exact.txt','mimeType':'text/plain','buffer':raw});self.page.wait_for_function("window.currentReport?.inputs.A.filename === 'exact.txt'")
  self.page.locator('#workspace-name').fill('Exact workspace');self.page.get_by_role('button',name='Save workspace',exact=True).click();self.page.wait_for_function("document.querySelector('#storage-status').textContent.includes('Saved')")
  self.page.reload();self.page.wait_for_function('window.appReady === true');self.page.get_by_role('button',name='Workspaces',exact=True).click();self.page.get_by_role('button',name='Restore Exact workspace').click();self.page.wait_for_function("window.currentReport?.inputs.A.filename === 'exact.txt'")
  report=self.page.evaluate('window.currentReport');self.assertEqual(report['inputs']['A']['raw_text'],'\ufeff4 BT1-010\r\n');self.assertEqual(report['inputs']['A']['original_file_sha256'],hashlib.sha256(raw).hexdigest())
 def test_real_indexeddb_abort_rolls_back_and_stale_saves_preserve_previous(self):
  result=self.page.evaluate('''async()=>{const db=await BrowserDB.open('abort-test'); const s=new WorkspaceStorage.Workspaces(db);await s.save({id:'x',name:'First',expectedRevision:0,report:{identity:'a'}});
   let conflict=false;try{await s.save({id:'x',name:'Stale',expectedRevision:0,report:{identity:'b'}});}catch(e){conflict=e.message.includes('changed');}
   let abort=false;try{await db.run('readwrite',async tx=>{await tx.put('reports',{id:'aborted',body:'should not persist'});throw Error('intentional abort');});}catch(e){abort=true;}
   const absent=await db.run('readonly',tx=>tx.get('reports','aborted')); const restored=await s.restore('x');db.close();return {conflict,abort,absent:!absent,name:restored.workspace.name};}''')
  self.assertEqual(result,{'conflict':True,'abort':True,'absent':True,'name':'First'})
 def test_offline_reload_and_uncached_prefix_import(self):
  self.page.wait_for_function("document.querySelector('#offline-status').textContent === 'Ready offline'",timeout=60000)
  self.page.reload();self.page.wait_for_function('window.appReady === true');self.context.set_offline(True);self.page.reload();self.page.wait_for_function('window.appReady === true')
  self.page.locator('#textA').fill('4 BT1-010');self.page.locator('#textB').fill('4 ST1-03');self.page.wait_for_function('window.currentReport?.statistics?.A?.unknown_count === 0 && window.currentReport?.statistics?.B?.unknown_count === 0')
  self.assertEqual(self.page.evaluate('window.currentReport.statistics.A.total'),4)
 def test_identity_and_generic_bot_labels_follow_pair(self):
  self.samples();old=self.page.evaluate('window.currentReport.identity');self.page.get_by_role('button',name='Swap A and B').click();self.page.wait_for_function('(old)=>window.currentReport?.identity !== old',arg=old)
  self.page.locator('#textA').fill('4 BT1-010');self.page.wait_for_function('window.currentReport?.simulation.bots[0].deck === null')
  self.assertIsNone(self.page.evaluate('window.currentReport.simulation.bots[1].deck'))
 def test_mobile_markup_and_catalog_browsing(self):
  self.page.set_viewport_size({'width':390,'height':844});self.page.locator('#textA').fill('4 <img src=x onerror=alert(1)> BT1-010');self.page.locator('#textB').fill('4 XX1-099');self.page.wait_for_function('window.currentReport !== null')
  self.assertEqual(self.page.locator('img').count(),0);self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
  self.page.get_by_role('button',name='Catalog',exact=True).click();self.page.locator('#catalog-prefix').select_option('BT1');self.page.locator('#catalog-query').fill('Agumon');self.page.locator('#catalog-results article').first.wait_for();self.assertIn('Agumon',self.page.locator('#catalog-results').inner_text());self.page.screenshot(path=str(ROOT/'work/pwa-mobile.png'),full_page=True)
 def test_portable_html_has_full_catalog_without_runtime_requests(self):
  self.assertTrue((ROOT/'APP/DigiBattle-DeckLab.html').exists(),'portable app exists')
  requests=[]
  page=self.context.new_page();page.on('request',lambda r:requests.append(r.url));page.goto(self.url.replace('index.html','DigiBattle-DeckLab.html'));page.wait_for_function('window.appReady === true')
  page.locator('#textA').fill('4 BT1-010');page.locator('#textB').fill('4 EX2-046');page.wait_for_function('window.currentReport?.statistics?.A?.unknown_count === 0 && window.currentReport?.statistics?.B?.unknown_count === 0')
  self.assertEqual([u for u in requests if not u.endswith('DigiBattle-DeckLab.html')],[])
  self.assertEqual(page.evaluate('window.currentReport.catalog_snapshot.card_count'),4481)
 def test_two_file_drop_archive_and_real_concurrent_storage(self):
  a=(ROOT/'DECKS/JUPITERMON.txt').read_text();b=(ROOT/'DECKS/AMATERASUMON_TOHO.txt').read_text()
  self.page.evaluate('''([a,b])=>{const dt=new DataTransfer();dt.items.add(new File([a],'a.txt'));dt.items.add(new File([b],'b.txt'));document.querySelector('.drop-target').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));}''',[a,b])
  self.page.wait_for_function("window.currentReport?.inputs.A.filename === 'a.txt' && window.currentReport?.inputs.B.filename === 'b.txt'")
  self.assertEqual(self.page.evaluate('window.currentReport.statistics.A.main_count'),50)
  result=self.page.evaluate('''async()=>{const db=await BrowserDB.open('concurrent-test'),s=new WorkspaceStorage.Workspaces(db);const saves=await Promise.allSettled([s.save({id:'x',name:'First',expectedRevision:0,report:{identity:'a'}}),s.save({id:'x',name:'Second',expectedRevision:0,report:{identity:'b'}})]);const w=(await s.list())[0];await s.archive('x',w.revision);const loaded=await s.restore('x');db.close();return {winners:saves.filter(r=>r.status==='fulfilled').length,archived:loaded.workspace.archived,revision:loaded.workspace.revision};}''')
  self.assertEqual(result,{'winners':1,'archived':True,'revision':2})
 def test_late_restore_does_not_replace_newer_typing(self):
  self.samples();self.page.locator('#workspace-name').fill('Saved');self.page.get_by_role('button',name='Save workspace',exact=True).click();self.page.wait_for_function("document.querySelector('#storage-status').textContent.includes('Saved Saved')")
  self.page.evaluate('''()=>{const original=WorkspaceStorage.Workspaces.prototype.restore;WorkspaceStorage.Workspaces.prototype.restore=async function(id){const result=await original.call(this,id);await new Promise(resolve=>window.releaseRestore=resolve);window.restoreFinished=true;return result;};}''')
  self.page.get_by_role('button',name='Workspaces',exact=True).click();self.page.get_by_role('button',name='Restore Saved').click();self.page.wait_for_function('typeof window.releaseRestore === "function"')
  self.page.get_by_role('button',name='Deck comparison',exact=True).click();self.page.locator('#textA').fill('4 BT1-010');self.page.evaluate('window.releaseRestore()');self.page.wait_for_function('window.restoreFinished === true');self.page.wait_for_function('window.currentReport !== null')
  self.assertEqual(self.page.locator('#textA').input_value(),'4 BT1-010')
 def test_late_save_as_new_keeps_subsequently_restored_selection(self):
  self.samples();self.page.locator('#workspace-name').fill('First');self.page.get_by_role('button',name='Save workspace',exact=True).click();self.page.wait_for_function("document.querySelector('#storage-status').textContent.includes('Saved First')")
  self.page.evaluate('''()=>{const original=WorkspaceStorage.Workspaces.prototype.save;let once=true;WorkspaceStorage.Workspaces.prototype.save=async function(args){const result=await original.call(this,args);if(once){once=false;await new Promise(resolve=>window.releaseSave=resolve);}return result;};}''')
  self.page.locator('#workspace-name').fill('Second');self.page.get_by_role('button',name='Save as new',exact=True).click();self.page.wait_for_function('typeof window.releaseSave === "function"');self.page.get_by_role('button',name='Workspaces',exact=True).click();self.page.get_by_role('button',name='Restore First').click();self.page.wait_for_function("document.querySelector('#storage-status').textContent.includes('Restored First')")
  self.page.evaluate('window.releaseSave()');self.page.wait_for_function("!document.querySelector('#save-workspace').disabled")
  self.page.locator('#workspace-name').fill('Third');self.page.get_by_role('button',name='Save workspace',exact=True).click();self.page.wait_for_function("document.querySelector('#storage-status').textContent.includes('Saved Third')")
  saved=self.page.evaluate('''async()=>{const db=await BrowserDB.open(),s=new WorkspaceStorage.Workspaces(db);const list=await s.list();db.close();return list.map(w=>({name:w.name,revision:w.revision}));}''')
  self.assertIn({'name':'Second','revision':1},saved);self.assertIn({'name':'Third','revision':2},saved)
 def test_failed_offline_install_is_reported(self):
  self.server.fail_asset=True;c=self.browser.new_context();p=c.new_page()
  try:
   p.goto(self.url);p.wait_for_function('window.appReady === true');p.wait_for_function("document.querySelector('#offline-status').textContent === 'Offline access unavailable'",timeout=8000)
  finally:c.close();self.server.fail_asset=False
if __name__=='__main__':unittest.main()
