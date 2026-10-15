import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('winapp',Path(__file__).parents[1]/'scripts/winapp.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)

class Arguments(unittest.TestCase):
    def test_no_implicit_prefix(self):
        with self.assertRaisesRegex(ValueError,'no implicit'):
            w.context(types.SimpleNamespace(prefix=None,wine=None))
    def test_windows_path_and_escaping(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);f=p/'drive_c'/'Program Files (x86)'/'literal $name.exe'
            f.parent.mkdir(parents=True);f.touch()
            self.assertEqual(w.winpath(f,p),'C:\\Program Files (x86)\\literal $name.exe')
            with self.assertRaises(ValueError):w.winpath(p/'outside.exe',p)
    def test_staging_preserves_bytes_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);src=p/'original.exe';src.write_bytes(b'original\0bytes')
            out,digest=w.stage(src,p/'prefix','installers')
            self.assertEqual(out.read_bytes(),src.read_bytes())
            out.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'digest mismatch'):w.stage(src,p/'prefix','installers')
    def test_private_display_reused_pid_refused(self):
        import json,os
        with tempfile.TemporaryDirectory() as d:
            Path(d,'ready.json').write_text(json.dumps({'kind':'linux-windows-apps-private-display-v1','uid':os.getuid(),'pid':os.getpid(),'proc_start':'wrong'}))
            with self.assertRaisesRegex(ValueError,'PID was reused'):w.private_receipt(d)
    def test_shell_metacharacters_are_arguments(self):
        with patch.object(w.subprocess,'run') as run:
            w.run(['app','literal $(touch bad) `id`'])
            self.assertEqual(run.call_args.args[0],['app','literal $(touch bad) `id`'])
            self.assertNotIn('shell',run.call_args.kwargs)

if __name__=='__main__':unittest.main()
