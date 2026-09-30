"""궁리 자동 수집기 — 하루 한 번 실행해 feed/gungri_feed.json 을 만듭니다.

사용법
  python -m collector.run                 # 환경변수 TOURAPI_KEY 필요
  python -m collector.run --mock          # 인증키 없이 예시 자료로 동작 확인
  python -m collector.run --max-details 50

원칙
  - 수집기는 '자동 후보'만 만듭니다. 공개는 앱에서 스텝 검수 → 대표 공개로만 합니다.
  - 바뀐 것만 상세를 다시 받습니다(feed/state.json 에 contentId별 수정일 기록).
  - 하루 호출 예산(config.dailyCallBudget)을 넘기지 않습니다. 넘기면 멈추고 다음 날 이어서 받습니다.
"""
import argparse, datetime, json, os, sys, time

from . import mapping
from .tourapi import TourAPI, QuotaExceeded, TourAPIError

HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9))


def load(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, data):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def excluded(title, cfg):
    return any(k in (title or '') for k in cfg.get('excludeTitleKeywords', []))


def exclude_ids(here=HERE):
    """폐기한 항목(feedId) 목록 — collector/exclude.json {"excludeIds": ["TA-126508", "TA-E-2933421"]}. 다시 받지 않고 피드에서도 뺍니다."""
    d = load(os.path.join(here, 'exclude.json'), {})
    return {str(x).strip() for x in (d.get('excludeIds') or []) if str(x).strip()}


def is_excluded_id(kind, cid, cfg):
    ex = cfg.get('_exclude') or set()
    return ('TA-E-' if kind == 'EVENT' else 'TA-') + str(cid) in ex


def region_labels(cfg):
    """설정한 시·도 코드 → 피드에 쓰는 권역 이름(예: 11→서울)"""
    return {mapping.REGION[c] for c in cfg['regions'] if c in mapping.REGION}


def photo_rights():
    """대표 결정(collector/photo_rights.json): rejectUrls = 철회(피드에서 뺌), verifyUrls = 수동 확인 완료"""
    d = load(os.path.join(HERE, 'photo_rights.json'), {})
    return set(d.get('rejectUrls') or []), set(d.get('verifyUrls') or [])


def apply_photo_rights(recs, rej, ver):
    n = 0
    for r in recs:
        ph = r.get('photos')
        if not ph:
            continue
        keep = []
        for x in ph:
            u = x.get('url')
            if u in rej:
                n += 1; continue
            if x.get('usable') and not x.get('rights'):  # 이전에 받은 사진: 사용권 문구로 규칙 적용
                lic = str(x.get('license') or '')
                x['rights'] = 'AUTO' if lic.startswith('공공누리 1유형') else 'AUTO_NOEDIT' if lic.startswith('공공누리 3유형') else ''
            if u in ver and x.get('usable'):
                x['rights'] = x.get('rights') or 'MANUAL_OK'
            keep.append(x)
        r['photos'] = keep
    return n


def slim(recs, cfg):
    """사진은 사용 가능한 것 먼저 최대 maxPhotos장만 남겨 피드 크기를 줄임"""
    n = cfg.get('maxPhotos', 3)
    for r in recs:
        ph = r.get('photos')
        if ph:
            ph.sort(key=lambda x: not x.get('usable'))
            r['photos'] = ph[:n]
    return recs


def collect(api, cfg, state, today, max_details, log):
    """목록 → 바뀐 항목만 상세 → 피드 레코드"""
    seen = state.setdefault('seen', {})
    buckets = []  # 권역 × 유형별 장소 후보 [(kind, contentId, contentTypeId, modifiedtime)]
    events = []
    okq = badq = 0
    # 1) 장소 목록 (수정일순, 권역 × 유형)
    for regn in cfg['regions']:
        for ct in cfg['placeContentTypes']:
            b = []; buckets.append(b)
            for page in range(1, cfg['listPagesPerQuery'] + 1):
                try:
                    r = api.area_based(ct, regn, page=page, rows=cfg['numOfRows'])
                    okq += 1
                except TourAPIError as e:  # 한 목록이 안 열려도 나머지는 계속(서버가 느릴 때)
                    log.append(f'목록 건너뜀(권역 {regn}·유형 {ct}): {e}'); badq += 1
                    if okq == 0 and badq >= 3: raise TourAPIError('목록 조회가 연속 실패했습니다(TourAPI 서버가 응답하지 않음). 잠시 뒤 다시 실행해 주세요')
                    break
                fresh = 0
                for it in r['items']:
                    cid, mt = str(it.get('contentid')), str(it.get('modifiedtime') or '')
                    if excluded(mapping.clean(it.get('title')), cfg) or is_excluded_id('PLACE', cid, cfg):
                        continue
                    if seen.get(cid) != mt:
                        b.append(('PLACE', cid, ct, mt)); fresh += 1
                if fresh == 0 or page * cfg['numOfRows'] >= r['total']:
                    break  # 수정일순이므로 새 것이 없으면 다음 페이지도 없음
    # 2) 행사 (오늘 이후 시작 또는 진행 중)
    start = (today - datetime.timedelta(days=30)).strftime('%Y%m%d')
    horizon = (today + datetime.timedelta(days=cfg['festivalDaysAhead'])).strftime('%Y%m%d')
    for page in range(1, cfg['listPagesPerQuery'] * 3 + 1):
        try:
            r = api.festivals(start, page=page, rows=cfg['numOfRows'])
            okq += 1
        except TourAPIError as e:
            log.append(f'행사 목록 건너뜀: {e}'); badq += 1; break
        for it in r['items']:
            cid, mt = str(it.get('contentid')), str(it.get('modifiedtime') or '')
            end = str(it.get('eventenddate') or '99999999'); st = str(it.get('eventstartdate') or '0')
            if end < today.strftime('%Y%m%d') or st > horizon or excluded(mapping.clean(it.get('title')), cfg) or is_excluded_id('EVENT', cid, cfg):
                continue
            lab = mapping.region_of(it)
            if lab and lab not in region_labels(cfg):
                continue  # 설정한 권역 밖 행사는 받지 않음
            if seen.get(cid) != mt:
                events.append(('EVENT', cid, '15', mt))
        if page * cfg['numOfRows'] >= r['total']:
            break
    # 순서: 행사 먼저(기간이 있어 늦으면 쓸모없음) → 장소는 권역·유형을 번갈아(한 권역만 몰리지 않게)
    if okq == 0 and badq:
        raise TourAPIError('목록 조회가 모두 실패했습니다(TourAPI 서버가 응답하지 않음). 잠시 뒤 다시 실행해 주세요')
    events.sort(key=lambda t: t[3], reverse=True)
    todo = list(events)
    for i in range(max((len(b) for b in buckets), default=0)):
        todo.extend(b[i] for b in buckets if i < len(b))
    log.append(f'목록 확인: 새로 받을 항목 {len(todo)}건(행사 {len(events)}) · 이번 실행 상한 {max_details}건')
    # 3) 상세 (common + intro + image = 3건/항목)
    out = {'PLACE': [], 'EVENT': []}
    done = 0
    t0 = time.time(); fails = 0
    for kind, cid, ct, mt in todo[:max_details]:
        if time.time() - t0 > cfg.get('maxSeconds', 1080):  # 워크플로 제한(30분) 전에 멈추고 지금까지 받은 것을 저장
            log.append('시간 한도 도달 — 남은 항목은 다음 실행에서 이어 받습니다'); break
        if fails >= 8:
            log.append('연속 실패 8회 — 서버가 불안정해 중단하고 지금까지 받은 것을 저장합니다'); break
        try:
            c = api.common(cid)
            if not c:
                continue
            c.setdefault('contentid', cid)
            i = api.intro(cid, ct)
            im = api.images(cid)
        except QuotaExceeded:
            log.append('호출 예산 도달 — 남은 항목은 다음 실행에서 이어 받습니다'); break
        except TourAPIError as e:
            log.append(f'{cid} 건너뜀: {e}'); fails += 1; continue
        fails = 0
        checked = today.isoformat()
        rec = mapping.event(c, i, im, checked, cfg['maxOverviewChars']) if kind == 'EVENT' else mapping.place(c, i, im, ct, checked, cfg['maxOverviewChars'])
        out[kind].append(rec)
        seen[cid] = mt
        done += 1
    log.append(f'상세 수집 {done}건 · API 호출 {api.calls}건')
    return out


def curation_tag(records, here=HERE):
    """큐레이션 목록(collector/curation/*.json)과 이름이 맞으면 표시(curation)를 붙임"""
    import glob, re
    norm = lambda s: re.sub(r'[\s·.,\-_\'"!<>「」]|\(.*?\)', '', str(s or '')).lower()
    lists = [load(f, {}) for f in sorted(glob.glob(os.path.join(here, 'curation', '*.json')))]
    n = 0
    for rec in records:
        t = norm(rec.get('n') or rec.get('name'))
        if len(t) < 3:
            continue
        for L in lists:
            for it in L.get('items', []):
                c = norm(it['name'])
                if len(c) >= 4 and (c == t or (len(t) >= 4 and (c in t or t in c))):
                    rec.setdefault('curation', [])
                    if L['name'] not in rec['curation']:
                        rec['curation'].append(L['name']); rec['curationId'] = it['id']; n += 1
    return n


def merge(feed, new, today):
    """이전 피드와 합치기: 같은 feedId는 새 값으로, 끝난 행사는 제외"""
    by = {x['feedId']: x for x in feed.get('places', [])}
    for x in new['PLACE']:
        by[x['feedId']] = x
    ev = {x['feedId']: x for x in feed.get('events', [])}
    for x in new['EVENT']:
        ev[x['feedId']] = x
    t = today.isoformat()
    events = [x for x in ev.values() if (x.get('end_date') or '9999') >= t]
    return sorted(by.values(), key=lambda x: x['feedId']), sorted(events, key=lambda x: x.get('start_date') or '')


def probe(api, today):
    """키가 되는지, 응답 항목 이름이 매핑과 맞는지 한 번에 확인"""
    try:
        lst = api.area_based('14', '11', rows=1)
        print('areaBasedList2 OK · 전체', lst['total'], '· 항목:', sorted(lst['items'][0].keys()) if lst['items'] else '-')
        cid = str(lst['items'][0]['contentid']) if lst['items'] else '126508'
        c = api.common(cid); print('detailCommon2 OK · 항목:', sorted(c.keys()))
        i = api.intro(cid, '14'); print('detailIntro2 OK · 항목:', sorted(i.keys()))
        im = api.images(cid); print('detailImage2 OK · 사진', len(im), '· 항목:', sorted(im[0].keys()) if im else '-')
        f = api.festivals(today.strftime('%Y%m%d'), rows=1); print('searchFestival2 OK · 전체', f['total'], '· 항목:', sorted(f['items'][0].keys()) if f['items'] else '-')
        print('호출', api.calls, '건 · 키 정상')
        return 0
    except TourAPIError as e:
        print('확인 실패:', e); return 2


def main(argv=None):
    ap = argparse.ArgumentParser(description='궁리 자동 수집기 (TourAPI → feed/gungri_feed.json)')
    ap.add_argument('--out', default=os.environ.get('GUNGRI_FEED_DIR', 'feed'))
    ap.add_argument('--mock', action='store_true', help='인증키 없이 예시 자료로 실행')
    ap.add_argument('--max-details', type=int, default=None)
    ap.add_argument('--today', default=None, help='YYYY-MM-DD (시험용)')
    ap.add_argument('--probe', action='store_true', help='인증키 확인: 각 기능을 1건씩 불러 응답 항목 이름을 보여 줌(호출 약 5건)')
    a = ap.parse_args(argv)
    cfg = load(os.path.join(HERE, 'config.json'), {})
    cfg['_exclude'] = exclude_ids()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.datetime.now(KST).date()
    feed_path, state_path = os.path.join(a.out, 'gungri_feed.json'), os.path.join(a.out, 'state.json')
    feed, state = load(feed_path, {}), load(state_path, {})
    log = []
    if a.mock:
        from .mock import MockOpener
        cfg['regions'] = ['11', '41', '43']  # 예시 자료가 있는 권역(설정과 무관하게 시험)
        api = TourAPI('MOCK-KEY', cfg.get('mobileApp', 'GUNGRI'), cfg['dailyCallBudget'], opener=MockOpener(), sleep=0)
    else:
        try:
            api = TourAPI(os.environ.get('TOURAPI_KEY', ''), cfg.get('mobileApp', 'GUNGRI'), cfg['dailyCallBudget'])
        except TourAPIError as e:
            print('수집 중단:', e, file=sys.stderr)
            return 2
    if a.probe:
        return probe(api, today)
    try:
        new = collect(api, cfg, state, today, a.max_details or cfg['maxDetailsPerRun'], log)
    except TourAPIError as e:
        print('수집 실패:', e, file=sys.stderr)
        return 2
    places, events = merge(feed, new, today)
    ex = cfg['_exclude']
    if ex:
        n0 = len(places) + len(events)
        places = [x for x in places if x['feedId'] not in ex]
        events = [x for x in events if x['feedId'] not in ex]
        if n0 != len(places) + len(events):
            log.append(f'폐기 목록(exclude.json)에 있는 항목 {n0 - len(places) - len(events)}건 피드에서 제거')
    keep = region_labels(cfg)
    before = (len(places), len(events))
    places = [x for x in places if not x.get('ar') or x['ar'] in keep]
    events = [x for x in events if not x.get('region') or x['region'] in keep]
    if before != (len(places), len(events)):
        log.append(f'설정 권역 밖 항목 정리: 장소 {before[0] - len(places)} · 행사 {before[1] - len(events)}건 제외')
    rej, ver = photo_rights()
    m = apply_photo_rights(places + events, rej, ver)
    if m:
        log.append(f'철회한 사진 {m}장 피드에서 제거(photo_rights.json)')
    slim(places + events, cfg)
    log.append(f'큐레이션 표시(로컬100 등) {curation_tag(places + events)}건')
    out = {
        'schema': 'GUNGRI_FEED_V1', 'generatedAt': datetime.datetime.now(KST).isoformat(timespec='seconds'),
        'source': {'name': '한국관광공사 TourAPI 4.0 (KorService2)', 'page': mapping.SOURCE_PAGE,
                   'notice': '사진은 공공누리 유형(Type1·Type3)이 표시된 것만 사용 가능으로 표시합니다. 공개는 궁리 스텝 검수·대표 승인 후에만 합니다.'},
        'stats': {'places': len(places), 'events': len(events), 'newPlaces': len(new['PLACE']), 'newEvents': len(new['EVENT']), 'apiCalls': api.calls, 'mock': a.mock},
        'options': {'showExamples': bool(cfg.get('showExamples', True))},
        'log': log, 'places': places, 'events': events,
    }
    save(feed_path, out)
    state['lastRun'] = out['generatedAt']
    save(state_path, state)
    print('\n'.join(log))
    print(f"피드 저장: {feed_path} · 장소 {len(places)} · 행사 {len(events)} · 새로 {len(new['PLACE'])}/{len(new['EVENT'])} · 호출 {api.calls}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
