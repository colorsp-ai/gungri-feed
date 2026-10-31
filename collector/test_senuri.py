import json, os, tempfile, unittest
from collector import senuri
class T(unittest.TestCase):
    def test_mock(self):
        d = tempfile.mkdtemp()
        self.assertEqual(senuri.main(['--mock', '--out', d, '--today', '2026-10-30']), 0)
        f = json.load(open(os.path.join(d, 'gungri_jobs.json'), encoding='utf-8'))
        self.assertEqual(f['schema'], 'GUNGRI_JOBS_V1')
        ids = [j['jobId'] for j in f['jobs']]
        self.assertEqual(sorted(ids), ['J1', 'J2'])            # 서울·마감·위험문구·중복 제외
        self.assertEqual(f['dropped'], {'지역밖': 1, '마감': 1, '위험문구': 1})
        j1 = [j for j in f['jobs'] if j['jobId'] == 'J1'][0]
        self.assertIn('주 3일', j1['summary']); self.assertNotIn('<p>', j1['summary']); self.assertEqual(j1['age'], '60세 이상')
    def test_error(self):
        with self.assertRaises(RuntimeError):
            senuri.items('<response><header><resultCode>30</resultCode><resultMsg>SERVICE KEY ERROR</resultMsg></header></response>')
if __name__ == '__main__': unittest.main()
