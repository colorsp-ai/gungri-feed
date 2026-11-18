"""노인일자리 수행기관(시니어클럽 등) → 궁리 문의처 목록(GUNGRI_ORGS_V1).
공공데이터포털 15056961 · 한국노인인력개발원.
사용:  SENURI_KEY=발급키 python -m collector.orgs --probe     (응답 앞부분만 보기 — 처음 1회)
       SENURI_KEY=발급키 python -m collector.orgs --out feed   (구리·남양주 기관만 저장)
호출 주소는 환경변수 ORGS_URL 또는 config.json 의 orgs.url 로 바꿀 수 있어요(포털 '요청주소' 그대로)."""
import argparse, datetime, json, os, re, sys, urllib.parse
from . import senuri

DEF = {'url': 'https://apis.data.go.kr/B552474/JobBsnInfoService/getJobOperInsttList',
       'pages': 5, 'rows': 100, 'extraParams': {},
       # 시군구 행정구역 코드(행정표준코드): 경기도 41, 구리시 41310, 남양주시 41360
       'queries': [{'label': '구리', 'dstrCd1': '4100000000', 'dstrCd2': '4131000000'},
                   {'label': '남양주', 'dstrCd1': '4100000000', 'dstrCd2': '4136000000'}]}
T = {'name': ['orgName', 'operOrgNm', 'operInsttNm', 'insttNm', 'jobOperInsttNm', 'oranNm', 'orgNm', 'instNm', 'name'],
     'addr': ['zipAddr', 'addr', 'address', 'insttAddr', 'operInsttAddr', 'locAddr', 'adres', 'workPlcNm'],
     'tel': ['telNum', 'telNo', 'tel', 'insttTelNo', 'phone', 'telno', 'reprsntTelno'],
     'kind': ['insttTypeNm', 'insttSeNm', 'operSeNm', 'kind', 'jobSeNm', 'bsnsNm'],
     'area': ['sidoNm', 'sigunguNm', 'areaNm', 'ctprvnNm', 'signguNm']}


def cfg():
    try:
        c = json.load(open(os.path.join(senuri.HERE, 'config.json'), encoding='utf-8')).get('orgs', {})
    except Exception:
        c = {}
    d = {**DEF, **c}
    if os.environ.get('ORGS_URL'):
        d['url'] = os.environ['ORGS_URL']
    return d


def pick(d, key):
    low = {k.lower(): v for k, v in d.items()}
    for n in T[key]:
        v = low.get(n.lower())
        if v and (key != 'tel' or re.search(r'\d', v)):     # 전화번호가 ******로 가려져 오면 비워 둔다
            return v
    if key == 'tel':
        return ''
    hints = {'name': ('name', 'nm'), 'addr': ('addr', 'adres'), 'tel': ('tel', 'phone'), 'kind': ('type', 'se'), 'area': ('sido', 'sigungu')}[key]
    for k, v in low.items():                     # 항목 이름이 달라도 이름 조각으로 한 번 더 찾는다
        if v and any(h in k for h in hints) and not (key == 'name' and 'proj' in k):
            return v
    return ''


def collect(c, key, fetcher=senuri.fetch):
    out, seen, got = [], set(), 0
    for qd in c['queries']:
        for page in range(1, int(c['pages']) + 1):
            q = {'serviceKey': key, 'pageNo': page, 'numOfRows': c['rows'], **{k: v for k, v in qd.items() if k != 'label'}, **(c.get('extraParams') or {})}
            try:
                rows, total = senuri.items(fetcher(f"{c['url']}?{urllib.parse.urlencode(q)}"))
            except Exception as e:
                print('  조회 실패:', qd.get('label'), page, e, file=sys.stderr); break
            if not rows:
                break
            for r in rows:
                got += 1
                o = {'name': pick(r, 'name'), 'addr': pick(r, 'addr'), 'tel': pick(r, 'tel'), 'kind': '', 'area': qd.get('label', '')}
                k = (o['name'], o['addr'])
                if not o['name'] or k in seen:
                    continue
                seen.add(k); out.append(o)
            if total is not None and page * int(c['rows']) >= total:
                break
    return out, got


def main(argv=None, fetcher=senuri.fetch):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='feed'); ap.add_argument('--probe', action='store_true'); ap.add_argument('--mock', action='store_true')
    a = ap.parse_args(argv)
    c = cfg(); key = os.environ.get('SENURI_KEY', '')
    if a.mock:
        from .orgs_mock import mock_fetch
        fetcher, key = mock_fetch, 'MOCK'
    if not key:
        print('SENURI_KEY(공공데이터포털 인증키)가 없습니다.', file=sys.stderr); return 2
    if a.probe:
        try:
            print('주소:', c['url'])
            for qd in c['queries']:
                q = urllib.parse.urlencode({'serviceKey': key, 'pageNo': 1, 'numOfRows': 3, **{k: v for k, v in qd.items() if k != 'label'}, **(c.get('extraParams') or {})})
                print('---', qd.get('label')); print(fetcher(f"{c['url']}?{q}")[:1500])
        except Exception as e:
            print('조회 실패:', e, file=sys.stderr); return 2
        return 0
    try:
        orgs, scanned = collect(c, key, fetcher)
    except Exception as e:
        print('수집 실패:', e, file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True)
    feed = {'schema': 'GUNGRI_ORGS_V1', 'generatedAt': datetime.datetime.now(senuri.KST).isoformat(timespec='seconds'),
            'source': {'name': '한국노인인력개발원 노인일자리 수행기관', 'page': 'https://www.data.go.kr/data/15056961/openapi.do'}, 'orgs': orgs}
    if not orgs:
        print(f'기관 0건(받은 {scanned}건) — 파일을 새로 만들지 않습니다.'); return 0
    json.dump(feed, open(os.path.join(a.out, 'gungri_orgs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'기관 {len(orgs)}건 저장 (훑어 본 {scanned}건)'); return 0


if __name__ == '__main__':
    sys.exit(main())
