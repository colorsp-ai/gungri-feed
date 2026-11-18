import json, os, tempfile, unittest
from collector import orgs
class T(unittest.TestCase):
    def test_mock(self):
        d = tempfile.mkdtemp()
        self.assertEqual(orgs.main(['--mock', '--out', d]), 0)
        with open(os.path.join(d, 'gungri_orgs.json'), encoding='utf-8') as fh:
            f = json.load(fh)
        self.assertEqual(f['schema'], 'GUNGRI_ORGS_V1')
        self.assertEqual([o['name'] for o in f['orgs']], ['예시 구리시니어클럽', '예시 남양주시니어클럽'])
        self.assertEqual(f['orgs'][0]['tel'], '031-000-0000')
if __name__ == '__main__': unittest.main()
