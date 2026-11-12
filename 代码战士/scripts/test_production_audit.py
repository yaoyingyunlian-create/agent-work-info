"""Check dangerous false-positive cases with disposable release fixtures."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone
from production_audit import CORE, STORY_CHECKS, release_check, task_check

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.p = Path(self.temp.name)
        for name in CORE + ['验收材料/对白.lrc','验收材料/分镜.md','质检证据/frame.jpg']:
            p = self.p/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('fixture', encoding='utf-8')
        (self.p/'标签.txt').write_text('#阳新 #剧情',encoding='utf-8')
        qa = {'publish_review_passed':True, 'checks':{'manual':{'status':'PASS'}},
              'technical':{'FAIL':[],'WARN':[]}, 'real_frame_paths':[str(self.p/'质检证据/frame.jpg')],
              'video_sha256':hashlib.sha256((self.p/'视频.mp4').read_bytes()).hexdigest(),
              'release_file_hashes':{n:hashlib.sha256((self.p/n).read_bytes()).hexdigest() for n in CORE[:-1]}}
        (self.p/'视觉质检.json').write_text(json.dumps(qa),encoding='utf-8')
        (self.p/'a.txt').touch()
    def tearDown(self):self.temp.cleanup()
    def test_consistent_evidence(self):
        self.assertTrue(release_check(self.p)['qualified'])
    def test_changed_video_cannot_keep_pass(self):
        (self.p/'视频.mp4').write_bytes(b'new version')
        self.assertFalse(release_check(self.p)['qualified'])
        self.assertEqual((self.p/'a.txt').stat().st_size,0) # read-only, never silently removes it
    def test_too_many_tags(self):
        (self.p/'标签.txt').write_text(' '.join('#'+str(i) for i in range(6)),encoding='utf-8')
        self.assertIn('tags_must_be_one_line_at_most_5',release_check(self.p)['issues'])
    def test_new_release_requires_story_evidence(self):
        path = self.p/'视觉质检.json'
        qa = json.loads(path.read_text(encoding='utf-8'))
        qa['creation_date'] = '2026-11-11'
        qa['checks'][STORY_CHECKS[0]] = {'status': 'PASS', 'evidence': '  '}
        path.write_text(json.dumps(qa), encoding='utf-8')
        self.assertFalse(release_check(self.p)['qualified'])
        for name in STORY_CHECKS:
            qa['checks'][name] = {'status': 'PASS', 'evidence': '00:08 画面证据'}
        path.write_text(json.dumps(qa), encoding='utf-8')
        self.assertTrue(release_check(self.p)['qualified'])
    def test_stalled_task_no_regeneration(self):
        result=task_check({'status':'processing','phase':'persisting','created_at':'2026-11-05T00:00:00+00:00'},datetime(2026,11,5,1,tzinfo=timezone.utc))
        self.assertEqual(result['action'],'technical_escalation_same_task_no_new_generation')
    def test_unknown_submission_same_request(self):
        result=task_check({'status':'submission_unknown','created_at':'2026-11-05T00:00:00+00:00'},datetime(2026,11,5,1,tzinfo=timezone.utc))
        self.assertEqual(result['action'],'recover_same_request_id_only')

if __name__=='__main__':unittest.main()
