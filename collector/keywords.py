"""AI 키워드 붙이기 — 장소 소개 글을 읽고 '정해진 키워드 목록' 안에서만 골라 feed/gungri_keywords.json 을 만듭니다.
  ANTHROPIC_API_KEY=... python -m collector.keywords --out feed          (실제 호출)
  python -m collector.keywords --mock --out /tmp/kw                       (키 없이 시험)
원칙: 목록 밖 키워드는 버립니다 · 글에 없는 편의·안전 정보는 절대 붙이지 않습니다 · 글에 직접 없고 짐작으로 붙인 것은 est(추정) 표시 ·
      바뀐 장소만 다시 읽고, 하루 최대 장소 수(maxPerRun)를 넘기지 않습니다(비용 보호)."""
import argparse, datetime, hashlib, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9))
MODEL = 'claude-haiku-4-5-20251001'
URL = 'https://api.anthropic.com/v1/messages'
# 앱의 검색 키워드와 같은 이름을 써야 합니다.
VOCAB = {
 '계절·꽃': ['벚꽃', '철쭉·진달래', '유채꽃', '튤립', '장미', '수국', '연꽃', '해바라기', '코스모스', '단풍', '은행나무', '억새', '눈꽃', '물놀이'],
 '풍경': ['호수·강변', '바다·해변', '산·등산', '계곡·폭포', '숲·나무', '일출·일몰', '야경', '꽃구경', '공원', '정원'],
 '활동': ['산책', '둘레길·트레킹', '체험·공예', '농촌체험', '공연', '축제', '사진 찍기 좋아요'],
 '문화': ['박물관', '미술관·전시', '도서관·책', '역사·유적', '사찰·고택', '궁궐·성곽', '한옥·전통마을', '건축'],
 '먹거리': ['먹거리', '카페', '전통시장', '로컬푸드', '막걸리·전통주'],
 '분위기': ['힐링·휴식', '한적함', '아이와 함께', '여행 명소'],
 '편의(글에 직접 있을 때만)': ['주차 편함', '유모차·휠체어', '반려견 동반', '무료', '화장실·쉼터 많음', '실내', '평지 산책', '지하철 가까움'],
}
ALL = [k for v in VOCAB.values() for k in v]
FACT_ONLY = set(VOCAB['편의(글에 직접 있을 때만)'])


def cfg():
    try:
        c = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf-8')).get('keywords', {})
    except Exception:
        c = {}
    return {'model': MODEL, 'maxPerRun': 250, 'batch': 8, **c}


def text_of(p):
    parts = [('이름', p.get('n')), ('지역', ' '.join(filter(None, [p.get('ar'), p.get('r')]))), ('분류', ' '.join(p.get('k') or [])),
             ('한줄', p.get('why')), ('소개', p.get('summary') or p.get('overview')), ('볼거리', ' / '.join(p.get('highlights') or [])),
             ('체류', p.get('stay')), ('운영', p.get('hours')), ('요금', p.get('fee')), ('주차', p.get('parking')), ('설명', p.get('c')), ('상세', p.get('cl'))]
    return '\n'.join(f'{k}: {re.sub(r"\s+", " ", str(v)).strip()[:500]}' for k, v in parts if v and str(v).strip())


def has_text(p):
    return any(p.get(k) for k in ('why', 'summary', 'overview', 'highlights', 'c', 'cl'))


def digest(p):
    return hashlib.sha1(text_of(p).encode('utf-8')).hexdigest()[:12]


PROMPT = """당신은 한국 시니어 여행 앱의 장소 분류 담당입니다. 아래 장소마다 ‘키워드 목록’ 안에서만 골라 붙이세요.
규칙
1. 목록에 없는 단어는 절대 쓰지 않습니다.
2. 글에 직접 나온 것은 est=false, 글에는 없지만 장소의 성격상 거의 확실한 것(예: 은행나무길 → 은행나무·단풍)은 est=true 로 하고 많이 붙이지 마세요.
3. ‘편의(글에 직접 있을 때만)’ 그룹(주차 편함·유모차·휠체어·반려견 동반·무료·화장실·실내 등)은 글에 그 내용이 직접 있을 때만 붙이고 est 는 항상 false 입니다. 짐작 금지.
4. ev 에는 근거가 되는 글의 짧은 구절을 그대로 옮겨 적습니다(est=true 면 비워도 됩니다).
5. 장소당 최대 8개. 확신이 없으면 붙이지 마세요. 글이 거의 없으면 빈 목록.
6. 답은 JSON 배열만 출력합니다. 형식: [{"id":"…","kw":[{"k":"단풍","est":false,"ev":"가을 단풍이 아름다운"}]}]

키워드 목록
""" + '\n'.join(f'- {g}: ' + ', '.join(v) for g, v in VOCAB.items()) + "\n\n장소\n"


def call_api(prompt, key, model, fetch=None):
    body = json.dumps({'model': model, 'max_tokens': 3000, 'messages': [{'role': 'user', 'content': prompt}]}).encode('utf-8')
    last = None
    for n in range(4):
        try:
            if fetch:
                return fetch(prompt)
            req = urllib.request.Request(URL, data=body, headers={'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode('utf-8'))
            return ''.join(b.get('text', '') for b in d.get('content', []) if b.get('type') == 'text')
        except Exception as e:
            last = e; time.sleep(4 * (n + 1))
    raise last


def parse(txt):
    m = re.search(r'\[.*\]', txt, re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except Exception:
        return []


def clean(entry, src_text):
    """목록 밖 키워드 제거 · 편의 그룹은 근거 구절이 글에 있어야 인정 · 근거가 글에 없으면 추정으로 낮춘다."""
    out, seen = [], set()
    for it in (entry.get('kw') or [])[:12]:
        k = str((it or {}).get('k', '')).strip()
        if k not in ALL or k in seen:
            continue
        ev = re.sub(r'\s+', ' ', str(it.get('ev', ''))).strip()[:80]
        est = bool(it.get('est'))
        grounded = bool(ev) and re.sub(r'\s+', '', ev) in re.sub(r'\s+', '', src_text)
        if k in FACT_ONLY and not grounded:
            continue
        if not est and not grounded:
            est = True
        seen.add(k)
        out.append({'k': k, 'est': est, 'ev': ev if grounded else ''})
        if len(out) >= 8:
            break
    return out


def load(path, default):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return default


def collect_places(feed_dir):
    base = load(os.path.join(HERE, 'places_base.json'), {}).get('places', [])
    feed = load(os.path.join(feed_dir, 'gungri_feed.json'), {})
    ps = [{**p, 'id': str(p['id'])} for p in base if p.get('id')]
    for p in feed.get('places', []):
        if p.get('feedId'):
            ps.append({**p, 'id': str(p['feedId'])})
    return ps


def run(places, state, out_items, key, c, fetch=None):
    todo = [p for p in places if state.get(p['id']) != digest(p) and has_text(p)]
    todo = todo[:int(c['maxPerRun'])]
    done = 0
    for i in range(0, len(todo), int(c['batch'])):
        chunk = todo[i:i + int(c['batch'])]
        prompt = PROMPT + '\n\n'.join(f'[id={p["id"]}]\n{text_of(p)}' for p in chunk)
        try:
            got = {str(e.get('id')): e for e in parse(call_api(prompt, key, c['model'], fetch)) if isinstance(e, dict)}
        except Exception as e:
            print('  AI 호출 실패:', e, file=sys.stderr); break
        for p in chunk:
            e = got.get(p['id'])
            if e is None:
                continue
            out_items[p['id']] = clean(e, text_of(p))
            state[p['id']] = digest(p); done += 1
    return done, len(todo)


def main(argv=None, fetch=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='feed'); ap.add_argument('--mock', action='store_true'); ap.add_argument('--max', type=int, default=None)
    a = ap.parse_args(argv)
    c = cfg()
    if a.max:
        c['maxPerRun'] = a.max
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    if a.mock:
        from .keywords_mock import mock_fetch
        fetch, key = mock_fetch, 'MOCK'
    if not key:
        print('ANTHROPIC_API_KEY 가 없습니다.', file=sys.stderr); return 2
    os.makedirs(a.out, exist_ok=True)
    sp, op = os.path.join(a.out, 'kw_state.json'), os.path.join(a.out, 'gungri_keywords.json')
    state = load(sp, {})
    items = load(op, {}).get('items', {})
    places = collect_places(a.out)
    live = {p['id'] for p in places}
    items = {k: v for k, v in items.items() if k in live}          # 사라진 장소는 지운다
    state = {k: v for k, v in state.items() if k in live}
    done, todo = run(places, state, items, key, c, fetch)
    feed = {'schema': 'GUNGRI_KW_V1', 'generatedAt': datetime.datetime.now(KST).isoformat(timespec='seconds'), 'model': c['model'],
            'note': 'AI가 장소 소개 글을 읽고 정해진 키워드 목록에서 고른 결과입니다. est=true 는 글에 직접 없는 추정입니다.', 'items': items}
    json.dump(feed, open(op, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(state, open(sp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    tagged = sum(1 for v in items.values() if v)
    print(f'이번에 {done}곳 처리(대기 {todo}곳) · 전체 {len(items)}곳 중 키워드가 붙은 곳 {tagged}곳')
    return 0


if __name__ == '__main__':
    sys.exit(main())
