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
DEF = {'listOp': '/getJobList', 'detailOp': '/getJobInfo', 'pages': 8, 'rows': 100,
       'areas': [{'q': '구리', 'label': '경기 구리시'},
                 {'q': '하남', 'label': '경기 인근',
                  'hint': ['구리', '남양주', '하남', '다산', '별내', '진접', '오남', '호평', '평내', '마석', '화도', '와부', '덕소', '미사', '감일', '위례', '풍양', '양정', '퇴계원', '수동', '조안']}],
       'regionWords': ['구리', '하남'], 'maxDetails': 40,
       'badWords': ['선입금', '수수료', '보증금', '다단계', '투자', '입회비', '교육비 납부', '가입비', '물품 구입']}
# 응답 태그 이름이 명세와 조금 달라도 읽도록 후보를 둔다
T = {'id': ['jobId', 'jobid', 'id'], 'title': ['recrtTitle', 'jobTitle', 'title', 'wantedTitle', 'subject'],
     'kind': ['emplyShpText', 'emplymShpNm', 'emplyForm', 'empType', 'employType'], 'job': ['jobclsNm', 'jobCls', 'occupation'],
     'place': ['workPlaceNm', 'workPlace', 'workPlcNm', 'workplace'], 'org': ['oranNm', 'acptInstNm', 'cmpnyNm', 'company', 'orgName', 'plbizNm'],
     'method': ['acptMthd', 'acptMthdNm', 'receiptMethod'], 'status': ['acptState', 'acptStts', 'receiptState', 'closeYn'],
     'start': ['frDd', 'frAcptDd', 'startDate', 'acptBgnDd', 'beginDate'], 'end': ['toDd', 'toAcptDd', 'endDate', 'acptEndDd', 'closeDate'],
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


def fetch(url, opener=None, tries=4):
    import time
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'GUNGRI-collector/1.0'})
            with (opener or urllib.request.urlopen)(req, timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:      # 일시적 접속 지연(SSL 시간초과 등)은 쉬었다가 다시 시도
            last = e
            time.sleep(3 * (n + 1))
    raise last


def build(it, cfg, today, detail=None):
    d = {**it, **{k: v for k, v in (detail or {}).items() if v}}
    if it.get('jobId'):
        d['jobId'] = it['jobId']          # 상세 응답이 달라도 목록의 공고ID를 유지
    end = parse_date(pick(d, 'end'))
    return {
        'jobId': pick(d, 'id'), 'title': pick(d, 'title'), 'kind': ('' if re.fullmatch(r'[A-Z]{2}\d+', pick(d, 'kind')) else pick(d, 'kind')), 'job': pick(d, 'job'),
        'place': pick(d, 'place') or pick(d, 'addr'), 'org': pick(d, 'org'), 'method': pick(d, 'method'),
        'start': parse_date(pick(d, 'start')), 'end': end, 'age': pick(d, 'age'), 'count': pick(d, 'count'),
        'summary': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', pick(d, 'body'))).strip()[:300],
        'link': pick(d, 'home'),
        'source': '한국노인인력개발원 노인일자리여기(100세누리) · 공공데이터포털',
    }


def collect(cfg, key, today, fetcher=fetch):
    """지역 이름 조건(workPlcNm)으로 서버에서 먼저 거른 뒤, 접수 중인 공고만 남긴다."""
    kept, seen, drop = [], set(), {'마감': 0, '위험문구': 0, '지역밖': 0, '중복공고': 0, '조회실패': 0}
    for area in cfg['areas']:
        for page in range(1, int(cfg['pages']) + 1):
            q = urllib.parse.urlencode({'serviceKey': key, 'pageNo': page, 'numOfRows': cfg['rows'], 'workPlcNm': area['q']})
            try:
                rows, total = items(fetcher(f"{BASE}{cfg['listOp']}?{q}"))
            except Exception as e:
                print('  목록 조회 실패:', area['q'], page, e, file=sys.stderr); drop['조회실패'] += 1; break
            if not rows:
                break
            active = 0
            for it in rows:
                j = build(it, cfg, today)
                if not j['jobId'] or j['jobId'] in seen:
                    continue
                seen.add(j['jobId'])
                closed = (it.get('deadline') == '마감') or (j['end'] and j['end'] < today.isoformat())
                if closed:
                    drop['마감'] += 1; continue
                if bad(j['title'] + ' ' + j['org'], cfg['badWords']):
                    drop['위험문구'] += 1; continue
                if area.get('hint') and not region_hit(j['title'] + ' ' + j['org'] + ' ' + j['place'], area['hint']):
                    drop['지역밖'] += 1; continue        # 이 코드에는 다른 지역 공고가 섞여 있어 제목·기관에 동네 이름이 있는 것만 남긴다
                active += 1
                j['place'] = j['place'] or area['label']
                j['area'] = area['label']
                kept.append((it, j))
            if active == 0 or (total is not None and page * int(cfg['rows']) >= total):
                break
    out, detail_ok = [], True
    for n, (it, j) in enumerate(kept):
        if detail_ok and n < int(cfg['maxDetails']):
            try:
                dq = urllib.parse.urlencode({'serviceKey': key, 'id': j['jobId']})
                drows, _ = items(fetcher(f"{BASE}{cfg['detailOp']}?{dq}"))
                if drows:
                    area, place = j['area'], j['place']
                    j = build(it, cfg, today, drows[0]); j['area'] = area; j['place'] = j['place'] or place
                    if bad(j['title'] + ' ' + j['summary'], cfg['badWords']):
                        drop['위험문구'] += 1; continue
            except Exception:
                detail_ok = False        # 상세 조회 주소가 맞지 않으면 한 번 실패한 뒤 더 시도하지 않는다
        out.append(j)
    best = {}
    for j in out:                         # 같은 기관이 같은 제목으로 여러 번 올린 공고는 마감이 가장 늦은 1건만 남긴다
        k = (re.sub(r'\s+', '', j['title']), re.sub(r'\s+', '', j['org']))
        if k in best:
            drop['중복공고'] += 1
            if (j['end'] or '') > (best[k]['end'] or ''):
                best[k] = j
        else:
            best[k] = j
    out = list(best.values())
    out.sort(key=lambda x: (x['end'] or '9999', x['title']))
    return out, drop


def probe2(cfg, key, fetcher):
    """지역 필터가 되는지, 목록이 최신순인지 알아보는 진단. 로그를 읽고 설정을 정한다."""
    def get(extra, rows=100, page=1):
        q = {'serviceKey': key, 'pageNo': page, 'numOfRows': rows}; q.update(extra)
        return items(fetcher(f"{BASE}{cfg['listOp']}?{urllib.parse.urlencode(q)}"))
    rows, total = get({})
    print('전체 건수', total, '· 1쪽', len(rows), '건')
    print('접수시작일 앞/뒤:', rows[0].get('frDd'), rows[-1].get('frDd'), '· 마감일 앞/뒤:', rows[0].get('toDd'), rows[-1].get('toDd'))
    seen = {}
    for p in (1, 2, 3):
        for it in get({}, 100, p)[0]:
            seen[it.get('workPlc', '')] = it.get('workPlcNm', '')
    print('근무지 코드 예:', list(seen.items())[:12])
    hit = {c: n for c, n in seen.items() if region_hit(n, cfg['regionWords'])}
    print('구리/남양주 코드(앞 3쪽):', hit)
    base = rows[0].get('workPlc', '')
    for pname in ('workPlc', 'workPlcCd', 'workPlace', 'region', 'sido', 'areaCd'):
        try:
            r, t = get({pname: base}, 20)
            same = all(x.get('workPlc') == base for x in r)
            print(f'필터 {pname}={base}: 건수 {t} · 모두 같은 지역 {same}')
        except Exception as e:
            print(f'필터 {pname}: 오류 {e}')
    for pname in ('workPlcNm', 'keyword', 'srchWord', 'searchWord', 'recrtTitle', 'jobNm'):
        try:
            r, t = get({pname: '구리'}, 20)
            print(f'검색 {pname}=구리: 건수 {t} · 예 {[x.get("workPlcNm") for x in r[:3]]}')
        except Exception as e:
            print(f'검색 {pname}: 오류 {e}')
    for pre in ('01', '010', '0100', '41', '31'):
        try:
            r, t = get({'workPlc': pre}, 5)
            print(f'접두 workPlc={pre}: 건수 {t} · 예 {[x.get("workPlcNm") for x in r[:3]]}')
        except Exception as e:
            print(f'접두 {pre}: 오류 {e}')


def probe3(cfg, key, fetcher):
    """workPlcNm 조건으로 지역 걸러내기가 되는지, 응답이 어떻게 생겼는지 원문으로 확인."""
    for w in ('구리', '남양주', '경기 구리시', '경기 남양주시'):
        q = urllib.parse.urlencode({'serviceKey': key, 'pageNo': 1, 'numOfRows': 3, 'workPlcNm': w})
        txt = fetcher(f"{BASE}{cfg['listOp']}?{q}")
        rows, total = items(txt)
        print(f'--- workPlcNm={w} · 전체 {total}건 · 받은 {len(rows)}건')
        print(txt[:1100])
        print('가져온 항목 이름들:', sorted({k for r in rows for k in r}))
    q = urllib.parse.urlencode({'serviceKey': key, 'pageNo': 1, 'numOfRows': 100, 'workPlcNm': '구리'})
    rows, total = items(fetcher(f"{BASE}{cfg['listOp']}?{q}"))
    from collections import Counter
    print('구리 1쪽 접수상태:', Counter(r.get('deadline') for r in rows))
    print('구리 1쪽 근무지:', Counter((r.get('workPlc'), r.get('workPlcNm')) for r in rows).most_common(6))
    print('구리 1쪽 접수시작일 앞/뒤:', rows[0].get('frDd') if rows else None, rows[-1].get('frDd') if rows else None)


def probe4(cfg, key, fetcher):
    from collections import Counter
    def get(extra, rows=100, page=1):
        q = {'serviceKey': key, 'pageNo': page, 'numOfRows': rows}; q.update(extra)
        return items(fetcher(f"{BASE}{cfg['listOp']}?{urllib.parse.urlencode(q)}"))
    for w in ('구리시', '남양주시', '남양주', '하남', '하남시', '030090', '남양', '양주', '구리 ', '경기'):
        try:
            r, t = get({'workPlcNm': w}, 50)
            print(f'workPlcNm={w!r}: {t}건 · 지역코드 {Counter(x.get("workPlc") for x in r).most_common(3)} · 접수중 {sum(1 for x in r if x.get("deadline") != "마감")}/{len(r)}')
        except Exception as e:
            print(f'workPlcNm={w!r}: 오류 {e}')
    codes = {}
    for p in range(1, 41):
        try:
            r, t = get({}, 100, p)
        except Exception as e:
            print('쪽', p, '오류', e); break
        for x in r:
            n = x.get('workPlcNm', '')
            if n:
                codes.setdefault(n, set()).add(x.get('workPlc'))
    print('경기 지역 이름→코드:', {n: sorted(c) for n, c in codes.items() if n.startswith('경기')})
    print('구리/남양주 포함 이름:', {n: sorted(c) for n, c in codes.items() if '구리' in n or '남양주' in n})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.environ.get('GUNGRI_FEED_DIR', 'feed'))
    ap.add_argument('--mock', action='store_true')
    ap.add_argument('--probe', action='store_true')
    ap.add_argument('--probe2', action='store_true')
    ap.add_argument('--probe3', action='store_true')
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
    if a.probe3:
        probe3(cfg, key, fetcher); return 0
    if a.probe2:
        probe4(cfg, key, fetcher); return 0
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
