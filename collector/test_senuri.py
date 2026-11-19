import json, os, tempfile, unittest
from collector import senuri
class T(unittest.TestCase):
    def test_mock(self):
        d = tempfile.mkdtemp()
        self.assertEqual(senuri.main(['--mock', '--out', d, '--today', '2026-10-30']), 0)
        f = json.load(open(os.path.join(d, 'gungri_jobs.json'), encoding='utf-8'))
        self.assertEqual(f['schema'], 'GUNGRI_JOBS_V1')
        ids = [j['jobId'] for j in f['jobs']]
        self.assertEqual(sorted(ids), ['K1'])                  # 마감·위험문구·중복 제외
        self.assertEqual(f['dropped'], {'마감': 1, '위험문구': 1, '지역밖': 0, '중복공고': 0, '조회실패': 0})
        j1 = f['jobs'][0]
        self.assertEqual(j1['place'], '경기 구리시'); self.assertEqual(j1['kind'], ''); self.assertEqual(j1['end'], '2099-12-31'); self.assertEqual(j1['org'], '예시경비')
    def test_error(self):
        with self.assertRaises(RuntimeError):
            senuri.items('<response><header><resultCode>30</resultCode><resultMsg>SERVICE KEY ERROR</resultMsg></header></response>')
if __name__ == '__main__': unittest.main()
