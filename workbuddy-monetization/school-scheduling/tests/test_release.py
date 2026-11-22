import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from package_release import validate_frontmatter
from common import VERSION


class Release(unittest.TestCase):
    def test_required_publishing_fields(self):
        content = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        fields = validate_frontmatter(content)
        self.assertEqual(fields['version'], VERSION)
        for key in ['version', 'display_name', 'display_name_en', 'description_zh', 'description_en']:
            with self.subTest(key=key):
                invalid = '\n'.join(line for line in content.split('\n') if not line.startswith(key + ':'))
                with self.assertRaises(ValueError):
                    validate_frontmatter(invalid)
        with self.assertRaises(ValueError):
            validate_frontmatter(content.replace('version:', '  version:', 1))
        with self.assertRaises(ValueError):
            validate_frontmatter(content.replace(VERSION, '0.0.0', 1))

    def test_workbuddy_depth_and_extracted_template_paths(self):
        with tempfile.TemporaryDirectory(prefix='排课上传验证') as folder:
            target = Path(folder)
            archive_path = target / 'skill.zip'
            result = subprocess.run(
                [sys.executable, '-X', 'utf8', str(ROOT / 'scripts/package_release.py'),
                 '--output', str(archive_path)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            extracted = target / 'school-scheduling'
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertIn('SKILL.md', names)
                fields = validate_frontmatter(archive.read('SKILL.md').decode('utf-8'))
                self.assertEqual(fields['version'], VERSION)
                self.assertTrue(all(len(Path(name).parts) <= 2 for name in names), names)
                self.assertIsNone(archive.testzip())
                archive.extractall(extracted)
            cli = extracted / 'scripts/cli.py'
            result = subprocess.run([sys.executable, '-S', '-X', 'utf8', str(cli)],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)['questions']), 3)
            for profile in ['primary', 'junior', 'senior', 'training']:
                output = target / (profile + '.xlsx')
                result = subprocess.run(
                    [sys.executable, '-X', 'utf8', str(cli), 'template', '--profile', profile,
                     '--output', str(output)], capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(output.is_file())


if __name__ == '__main__':
    unittest.main()
