"""python -m unittest collector.test_collector"""
import json, os, tempfile, unittest, datetime
from . import mapping, run
from .tourapi import TourAPI, TourAPIError, QuotaExceeded


class T(unittest.TestCase):
    def run_mock(self, out, *extra):
        self.assertEqual(run.main(['--mock', '--out', out] + list(extra)), 0)
        return json.load(open(os.path.join(out, 'gungri_feed.json'), encoding='utf-8'))

    def test_feed_shape_and_rules(self):
        with tempfile.TemporaryDirectory() as d:
            f = self.run_mock(d)
            self.assertEqual(f['schema'], 'GUNGRI_FEED_V1')
            names = [p['n'] for p in f['places']]
            self.assertIn('국립현대미술관 청주', names)
            self.assertFalse(any('키즈' in n for n in names), '제외 키워드')
            self.assertEqual([e['name'] for e in f['events']], ['구리 코스모스 축제'], '끝난 행사 제외')
            p = next(x for x in f['places'] if x['n'] == '국립현대미술관 청주')
            self.assertEqual(p['hours'], '10:00~18:00 / (입장마감 17:00)')
            self.assertEqual(p['ar'], '충청')
            self.assertTrue(p['sourceUrl'].startswith('https://'))
            self.assertTrue(all(ph['url'].startswith('https://') for ph in p['photos']))
            mk = next(x for x in f['places'] if x['n'] == '구리전통시장')
            self.assertFalse(mk['photos'][0]['usable'], '저작권 유형 없는 사진은 사용 불가')
            self.assertNotIn('fee', mk, '없는 값은 넣지 않음')

    def test_incremental(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_mock(d)
            f = self.run_mock(d)
            self.assertEqual(f['stats']['newPlaces'], 0)
            self.assertEqual(f['stats']['places'], 5, '이전 피드 유지')

    def test_budget(self):
        with tempfile.TemporaryDirectory() as d:
            f = self.run_mock(d, '--max-details', '2')
            self.assertEqual(f['stats']['newPlaces'] + f['stats']['newEvents'], 2)

    def test_order_events_first_then_mixed_regions(self):
        with tempfile.TemporaryDirectory() as d:
            f = self.run_mock(d, '--max-details', '3')
            self.assertEqual(f['stats']['newEvents'], 1, '행사를 먼저 받음')
            self.assertEqual(len({p['ar'] for p in f['places']}), 2, '장소는 권역을 번갈아 받음')

    def test_region_filter_and_photo_cap(self):
        from . import mock
        mock.FESTIVALS.append({'contentid': '900103', 'title': '부산 바다축제', 'addr1': '부산광역시 해운대구', 'lDongRegnCd': '26', 'eventstartdate': mock.D(5), 'eventenddate': mock.D(9), 'modifiedtime': '20260925090000'})
        mock.COMMON['900103'] = {'overview': '부산 행사', 'firstimage': '', 'cpyrhtDivCd': ''}
        try:
            with tempfile.TemporaryDirectory() as d:
                self.assertEqual(run.main(['--mock', '--out', d]), 0)
                f = json.load(open(os.path.join(d, 'gungri_feed.json'), encoding='utf-8'))
                self.assertEqual([e['name'] for e in f['events']], ['구리 코스모스 축제'], '권역 밖 행사 제외')
            cfg = {'maxPhotos': 2}
            rec = [{'photos': [{'usable': False}, {'usable': True, 'u': 1}, {'usable': True, 'u': 2}]}]
            run.slim(rec, cfg)
            self.assertEqual([p.get('u') for p in rec[0]['photos']], [1, 2], '사용 가능한 사진 우선 · 최대 장수')
        finally:
            mock.FESTIVALS[:] = [x for x in mock.FESTIVALS if x['contentid'] != '900103']

    def test_exclude_ids(self):
        with tempfile.TemporaryDirectory() as d:
            f = self.run_mock(d)
            pid = f['places'][0]['feedId']; eid = f['events'][0]['feedId']
            ex = os.path.join(os.path.dirname(run.__file__), 'exclude.json')
            old = open(ex, encoding='utf-8').read()
            try:
                open(ex, 'w', encoding='utf-8').write(json.dumps({'excludeIds': [pid, eid]}))
                f2 = self.run_mock(d)
                self.assertNotIn(pid, [x['feedId'] for x in f2['places']], '폐기한 장소는 피드에서 빠짐')
                self.assertNotIn(eid, [x['feedId'] for x in f2['events']], '폐기한 행사는 피드에서 빠짐')
            finally:
                open(ex, 'w', encoding='utf-8').write(old)

    def test_errors(self):
        self.assertRaises(TourAPIError, TourAPI, '')
        api = TourAPI('K', opener=lambda u: '<OpenAPI_ServiceResponse><cmmMsgHeader><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg></cmmMsgHeader></OpenAPI_ServiceResponse>', sleep=0)
        with self.assertRaisesRegex(TourAPIError, 'SERVICE_KEY_IS_NOT_REGISTERED'):
            api.call('areaBasedList2')
        api = TourAPI('K', budget=1, opener=lambda u: '{"response":{"header":{"resultCode":"0000"},"body":{"items":"","totalCount":0}}}', sleep=0)
        self.assertEqual(api.call('x')['items'], [])
        self.assertRaises(QuotaExceeded, api.call, 'x')

    def test_key_encoding(self):
        a = TourAPI('abc+/=', sleep=0); self.assertIn('serviceKey=abc%2B%2F%3D', a._url('op', {}))
        b = TourAPI('abc%2B', sleep=0); self.assertIn('serviceKey=abc%2B&', b._url('op', {}))

    def test_curation_tag(self):
        recs = [{'name': '2026 진주남강유등축제'}, {'n': '서울숲'}]
        self.assertEqual(run.curation_tag(recs), 1)
        self.assertEqual(recs[0]['curation'], ['로컬100'])

    def test_clean(self):
        self.assertEqual(mapping.clean('a<br>b &amp; c'), 'a / b & c')
        self.assertEqual(mapping.href('<a href="https://x.kr/y">x</a>'), 'https://x.kr/y')


if __name__ == '__main__':
    unittest.main()
