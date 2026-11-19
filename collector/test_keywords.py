import json, os, tempfile, unittest
from collector import keywords
class T(unittest.TestCase):
    def test_mock(self):
        d = tempfile.mkdtemp()
        json.dump({'schema': 'GUNGRI_FEED_V1', 'places': [{'feedId': 'TA-1', 'n': '은행나무길 공원', 'ar': '경기', 'r': '구리시', 'why': '가을 단풍과 은행나무가 아름다운 곳입니다. 야경도 좋습니다.', 'summary': '주차장이 있어 편합니다.', 'parking': '주차 가능'}]}, open(os.path.join(d, 'gungri_feed.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        self.assertEqual(keywords.main(['--mock', '--out', d, '--max', '2000']), 0)
        f = json.load(open(os.path.join(d, 'gungri_keywords.json'), encoding='utf-8'))
        self.assertEqual(f['schema'], 'GUNGRI_KW_V1')
        ks = {x['k']: x for x in f['items']['TA-1']}
        self.assertIn('단풍', ks); self.assertIn('은행나무', ks); self.assertIn('야경', ks); self.assertIn('주차 편함', ks)
        self.assertNotIn('없는키워드', ks); self.assertNotIn('반려견 동반', ks)       # 목록 밖·근거 없는 편의 정보 제거
        self.assertFalse(ks['단풍']['est'])
        # 두 번째 실행: 바뀐 게 없으면 다시 읽지 않는다
        before = json.load(open(os.path.join(d, 'kw_state.json'), encoding='utf-8'))
        calls = []
        orig = keywords.call_api
        keywords.call_api = lambda *a, **k: calls.append(1) or '[]'
        try:
            keywords.main(['--mock', '--out', d, '--max', '2000'])
        finally:
            keywords.call_api = orig
        self.assertEqual(calls, [])                                                    # 바뀐 장소가 없으면 AI를 부르지 않는다
        self.assertEqual(before, json.load(open(os.path.join(d, 'kw_state.json'), encoding='utf-8')))
    def test_parse(self):
        self.assertEqual(keywords.parse('설명 [{"id":"1","kw":[]}] 끝'), [{'id': '1', 'kw': []}])
        self.assertEqual(keywords.parse('엉망'), [])
if __name__ == '__main__': unittest.main()
