import importlib.util,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
SCRIPT=Path(__file__).resolve().parents[1]/'checksums.py'
class ChecksumTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  subprocess.run(['git','init','-q',str(self.root)],check=True)
  (self.root/'one.txt').write_text('one');subprocess.run(['git','add','one.txt'],cwd=self.root,check=True)
  spec=importlib.util.spec_from_file_location('checksums',SCRIPT);self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m);self.m.ROOT=self.root;self.m.MANIFEST=self.root/'CURRENT_SHA256SUMS.txt'
 def tearDown(self):self.temp.cleanup()
 def check(self):
  with patch.object(sys,'argv',['checksums.py','--check']):self.m.main()
 def test_rejects_empty_or_duplicate_inventory(self):
  line=self.m.digest(self.root/'one.txt')+'  one.txt\n'
  for text in ['',line+line]:
   with self.subTest(text=text):
    self.m.MANIFEST.write_text(text)
    with self.assertRaises(SystemExit):self.check()
 def test_rejects_new_tracked_file_missing_from_manifest(self):
  self.m.MANIFEST.write_text(self.m.digest(self.root/'one.txt')+'  one.txt\n')
  (self.root/'two.txt').write_text('two');subprocess.run(['git','add','two.txt'],cwd=self.root,check=True)
  with self.assertRaises(SystemExit):self.check()
