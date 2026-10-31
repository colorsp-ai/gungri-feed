"""100세누리(노인일자리여기) 구인정보 → 궁리 일자리 피드(GUNGRI_JOBS_V1).
공공데이터포털 15015153 · 한국노인인력개발원 · 이용허락범위 제한 없음.
사용:  SENURI_KEY=발급키 python -m collector.senuri --out feed        (실제 호출)
       python -m collector.senuri --mock --out feed                    (키 없이 시험)
       SENURI_KEY=... python -m collector.senuri --probe               (응답 항목 이름 확인 — 처음 1회 권장)
※ 호출 주소의 작업 이름(목록/상세)은 포털 '활용신청' 화면의 명세와 다를 수 있어 config.json 의 senuri 항목으로 바꿀 수 있습니다."""
import argparse, datetime, json, os, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9))
BASE = 'https://apis.data.go.kr/B552474/SenuriService'
DEF = {'listOp': '/getJobList', 'detailOp': '/getJobInfo', 'pages': 20, 'rows': 100,
       'regionWords': ['구리', '남양주'], 'maxDetails': 60,
       'badWords': ['선입금', '수수료', '보증금', '다단계', '투자', '입회비', '교육비 납부', '가입비', '물품 구입']}
# 응답 태그 이름이 명세와 조금 달라도 읽도록 후보를 둔다
T = {'id': ['jobId', 'jobid', 'id'], 'title': ['recrtTitle', 'jobTitle', 'title', 'wantedTitle', 'subject'],
     'kind': ['emplymShpNm', 'emplyForm', 'empType', 'employType'], 'job': ['jobclsNm', 'jobCls', 'occupation'],
     'place': ['workPlaceNm', 'workPlace', 'workPlcNm', 'workplace'], 'org': ['acptInstNm', 'cmpnyNm', 'company', 'orgName', 'plbizNm'],
     'method': ['acptMthd', 'acptMthdNm', 'receiptMethod'], 'status': ['acptState', 'acptStts', 'receiptState', 'closeYn'],
     'start': ['frAcptDd', 'startDate', 'acptBgnDd', 'beginDate'], 'end': ['toAcptDd', 'endDate', 'acptEndDd', 'closeDate'],
     'age': ['age', 'ageLmt', 'ageRange', 'recrtAge'], 'count': ['clltPrnnum', 'recruitNum', 'headcount'],
     'body': ['detailContent', 'content', 'recrtCn'], 'addr': ['plbizAddr', 'workplaceAddr', 'addr', 'address'],
     'home': ['homepage', 'homepageUrl', 'url']}


def load_cfg():
    try:
        c = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf-8'))
    except Exception:
        c = {}
    return {**DEF, **c.get('senuri', {})}, c


def _tag(e):
    return e.tag.split('}')[-1]


def items(xml_text):
    root = ET.fromstring(xml_text)
    code = ''
    for e in root.iter():
        if _tag(e).lower() in ('resultcode', 'returnreasoncode') and e.text:
            code = e.text.strip()
    if code and code not in ('00', '0', '000', 'NORMAL_CODE', 'NORMAL SERVICE.'):
        msg = next((e.text for e in root.iter() if _tag(e).lower() in ('resultmsg', 'returnauthmsg', 'errmsg') and e.text), '')
        raise RuntimeError(f'API 오류 {code} {msg}')
    out = []
    for it in root.iter():
        if _tag(it).lower() in ('item', 'items_item', 'row'):
            out.append({_tag(c): (c.text or '').strip() for c in it})
    total = next((int(e.text) for e in root.iter() if _tag(e).lower() == 'totalcount' and (e.text or '').strip().isdigit()), None)
    return out, total


def pick(d, key):
    low = {k.lower(): v for k, v in d.items()}
    for n in T[key]:
        v = low.get(n.lower())
        if v:
            return v
    return ''


def parse_date(s):
    m = re.search(r'(\d{4})\D?(\d{2})\D?(\d{2})', s or '')
    return f'{m[1]}-{m[2]}-{m[3]}' if m else ''


def region_hit(text, words):
    return any(w in (text or '') for w in words)


def bad(text, words):
    return any(w in (text or '') for w in words)


def fetch(url, opener=None):
    req = urllib.request.Request(url, headers={'User-Agent': 'GUNGRI-collector/1.0'})
    with (opener or urllib.request.urlopen)(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')


def build(it, cfg, today, detail=None):
    d = {**it, **{k: v for k, v in (detail or {}).items() if v}}
    if it.get('jobId'):
        d['jobId'] = it['jobId']          # 상세 응답이 달라도 목록의 공고ID를 유지
    end = parse_date(pick(d, 'end'))
    return {
        'jobId': pick(d, 'id'), 'title': pick(d, 'title'), 'kind': pick(d, 'kind'), 'job': pick(d, 'job'),
        'place': pick(d, 'place') or pick(d, 'addr'), 'org': pick(d, 'org'), 'method': pick(d, 'method'),
        'start': parse_date(pick(d, 'start')), 'end': end, 'age': pick(d, 'age'), 'count': pick(d, 'count'),
        'summary': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', pick(d, 'body'))).strip()[:300],
        'link': pick(d, 'home'),
        'source': '한국노인인력개발원 노인일자리여기(100세누리) · 공공데이터포털',
    }


def collect(cfg, key, today, fetcher=fetch):
    kept, seen, drop = [], set(), {'지역밖': 0, '마감': 0, '위험문구': 0}
    for page in range(1, int(cfg['pages']) + 1):
        q = urllib.parse.urlencode({'serviceKey': key, 'pageNo': page, 'numOfRows': cfg['rows']})
        rows, total = items(fetcher(f"{BASE}{cfg['listOp']}?{q}"))
        if not rows:
            break
        for it in rows:
            j = build(it, cfg, today)
            if not j['jobId'] or j['jobId'] in seen:
                continue
            seen.add(j['jobId'])
            if not region_hit(j['place'] + ' ' + j['title'] + ' ' + j['org'], cfg['regionWords']):
                drop['지역밖'] += 1; continue
            if j['end'] and j['end'] < today.isoformat():
                drop['마감'] += 1; continue
            if bad(j['title'] + ' ' + j['summary'], cfg['badWords']):
                drop['위험문구'] += 1; continue
            kept.append((it, j))
        if total is not None and page * int(cfg['rows']) >= total:
            break
    out = []
    for n, (it, j) in enumerate(kept):
        if n < int(cfg['maxDetails']):
            try:
                dq = urllib.parse.urlencode({'serviceKey': key, 'id': j['jobId']})
                drows, _ = items(fetcher(f"{BASE}{cfg['detailOp']}?{dq}"))
                if drows:
                    j = build(it, cfg, today, drows[0])
                    if bad(j['title'] + ' ' + j['summary'], cfg['badWords']):
                        drop['위험문구'] += 1; continue
            except Exception:
                pass
        out.append(j)
    out.sort(key=lambda x: (x['end'] or '9999', x['title']))
    return out, drop


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.environ.get('GUNGRI_FEED_DIR', 'feed'))
    ap.add_argument('--mock', action='store_true')
    ap.add_argument('--probe', action='store_true')
    ap.add_argument('--today', default=None)
    a = ap.parse_args(argv)
    cfg, _ = load_cfg()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.datetime.now(KST).date()
    key = os.environ.get('SENURI_KEY', '')
    fetcher = fetch
    if a.mock:
        from .senuri_mock import mock_fetch
        fetcher, key = mock_fetch, 'MOCK'
    if not key:
        print('SENURI_KEY(공공데이터포털 인증키)가 없습니다.', file=sys.stderr); return 2
    if a.probe:
        q = urllib.parse.urlencode({'serviceKey': key, 'pageNo': 1, 'numOfRows': 2})
        print(fetcher(f"{BASE}{cfg['listOp']}?{q}")[:1500]); return 0
    try:
        jobs, drop = collect(cfg, key, today, fetcher)
    except Exception as e:
        print('수집 실패:', e, file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True)
    feed = {'schema': 'GUNGRI_JOBS_V1', 'generatedAt': datetime.datetime.now(KST).isoformat(timespec='seconds'),
            'source': {'name': '한국노인인력개발원 100세누리 구인정보', 'page': 'https://www.data.go.kr/data/15015153/openapi.do'},
            'regionWords': cfg['regionWords'], 'dropped': drop, 'jobs': jobs}
    json.dump(feed, open(os.path.join(a.out, 'gungri_jobs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'일자리 {len(jobs)}건 저장 · 제외 {drop}'); return 0


if __name__ == '__main__':
    sys.exit(main())
