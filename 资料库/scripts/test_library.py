"""Portable integrity and packaging regression checks; standard library only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import library

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = library.PROJECT, library.ROOT
        library.PROJECT = Path(self.temp.name)
        library.ROOT = library.PROJECT / '资料库'
        for sub in ['原始资料', '索引', '素材库', '知识库']:
            (library.ROOT / sub).mkdir(parents=True)
        file = library.ROOT / '原始资料/中文 #1.txt'
        file.write_bytes('客户资料'.encode('utf-8'))
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        row = dict(id='A0001', name=file.name, path='原始资料/' + file.name, sha256=digest, kind='文字', bytes=file.stat().st_size, duplicate_of='', preview='', width='', height='', duration='', status='已归档')
        (library.ROOT / '索引/文件清单.json').write_text(json.dumps([row]), encoding='utf-8')
        (library.ROOT / '索引/素材标注.json').write_text('{}', encoding='utf-8')
        (library.PROJECT / 'index.html').write_text('<a href="资料库/素材库/index.html">入口</a>', encoding='utf-8')
        library.render()

    def tearDown(self):
        library.PROJECT, library.ROOT = self.old
        self.temp.cleanup()

    def test_repeated_render_and_unicode_links(self):
        before = (library.ROOT / '素材库/index.html').read_bytes()
        library.render()
        self.assertEqual(before, (library.ROOT / '素材库/index.html').read_bytes())
        self.assertTrue(library.verify())

    def test_tamper_and_unindexed_file_detected(self):
        (library.ROOT / '原始资料/中文 #1.txt').write_bytes(b'changed')
        self.assertFalse(library.verify())
        (library.ROOT / '原始资料/extra.txt').write_bytes(b'extra')
        self.assertFalse(library.verify())

    def test_escape_rejected(self):
        for path in ['../../outside.txt', 'C:/outside.txt', 'https://example.com/data']:
            with self.assertRaises(ValueError):
                library.local_path(library.ROOT, path)

    def test_package_exclusions_and_no_overwrite(self):
        for folder in ['.git', '.venv', 'tmp', 'dist']:
            p = library.PROJECT / folder / 'private.txt'
            p.parent.mkdir(exist_ok=True)
            p.write_bytes(b'excluded')
        (library.PROJECT / '.env').write_bytes(b'excluded')
        output = library.PROJECT / 'dist/test.zip'
        library.pack(output)
        with zipfile.ZipFile(output) as z:
            self.assertIsNone(z.testzip())
            self.assertFalse(any('private.txt' in n or '.env' in n for n in z.namelist()))
        with self.assertRaises(FileExistsError):
            library.pack(output)

if __name__ == '__main__':
    unittest.main()
