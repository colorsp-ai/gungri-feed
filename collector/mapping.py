"""TourAPI 응답 → 궁리 피드(GUNGRI_FEED_V1) 변환. 값이 없으면 넣지 않습니다(앱에서 '확인 중')."""
import html, re

REGION = {  # 법정동 시도 코드 → 궁리 권역
    '11': '서울', '41': '경기', '28': '인천', '51': '강원', '42': '강원',
    '43': '충청', '44': '충청', '30': '충청', '36': '충청',
    '52': '호남', '45': '호남', '46': '호남', '29': '호남',
    '47': '경북', '27': '경북', '48': '경남', '26': '경남', '31': '경남', '50': '제주',
}
ADDR_REGION = [('서울', '서울'), ('경기', '경기'), ('인천', '인천'), ('강원', '강원'), ('충청', '충청'), ('충북', '충청'), ('충남', '충청'),
               ('대전', '충청'), ('세종', '충청'), ('전라', '호남'), ('전북', '호남'), ('전남', '호남'), ('광주', '호남'),
               ('경상북', '경북'), ('경북', '경북'), ('대구', '경북'), ('경상남', '경남'), ('경남', '경남'), ('부산', '경남'), ('울산', '경남'), ('제주', '제주')]
TYPE_LABEL = {'12': '관광지', '14': '문화시설', '15': '행사', '28': '레포츠', '38': '시장·쇼핑'}
KEYWORDS = ['박물관', '미술관', '전시', '과학관', '기념관', '문학관', '도서관', '공원', '수목원', '정원', '숲', '둘레길', '산책', '호수', '해변', '해수욕장',
            '시장', '전통시장', '오일장', '사찰', '궁', '유적', '서원', '향교', '성곽', '마을', '체험', '공예', '전망대', '케이블카', '온천', '자연휴양림', '계곡', '폭포', '섬']
# 소개에 따라 붙이는 이름 · 코드
LICENSE = {'Type1': '공공누리 1유형(출처표시)', 'Type3': '공공누리 3유형(출처표시·변경금지)'}
# 유형별 소개(detailIntro2) 필드
INTRO = {
    '12': {'hours': ['usetime'], 'closed': ['restdate'], 'fee': ['usefee'], 'parking': ['parking'], 'phone': ['infocenter'], 'stay': []},
    '14': {'hours': ['usetimeculture'], 'closed': ['restdateculture'], 'fee': ['usefee'], 'parking': ['parkingculture'], 'phone': ['infocenterculture'], 'stay': ['spendtime']},
    '28': {'hours': ['usetimeleports'], 'closed': ['restdateleports'], 'fee': ['usefeeleports'], 'parking': ['parkingleports'], 'phone': ['infocenterleports'], 'stay': []},
    '38': {'hours': ['opentime'], 'closed': ['restdateshopping'], 'fee': [], 'parking': ['parkingshopping'], 'phone': ['infocentershopping'], 'stay': [], 'fair': ['fairday']},
    '15': {'hours': ['playtime'], 'closed': [], 'fee': ['usetimefestival'], 'parking': [], 'phone': ['sponsor1tel'], 'stay': ['spendtimefestival']},
}
SOURCE_LABEL = '한국관광공사 TourAPI'
SOURCE_PAGE = 'https://www.data.go.kr/data/15101578/openapi.do'


def clean(v):
    if v is None:
        return ''
    s = str(v)
    s = re.sub(r'<\s*br\s*/?\s*>', ' / ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\r', ' ').replace('\n', ' ')
    s = re.sub(r'\s{2,}', ' ', s).strip(' /').strip()
    return s


def href(v):
    m = re.search(r'href\s*=\s*["\']?(https?://[^"\'\s>]+)', str(v or ''), re.I)
    if m:
        return m.group(1)
    s = clean(v)
    m = re.search(r'https?://\S+', s)
    return m.group(0).rstrip('.,)') if m else ''


def pick(d, keys):
    for k in keys:
        s = clean(d.get(k))
        if s:
            return s
    return ''


def region_of(item):
    code = str(item.get('lDongRegnCd') or '').strip()
    if code in REGION:
        return REGION[code]
    a = clean(item.get('addr1'))
    for k, v in ADDR_REGION:
        if a.startswith(k):
            return v
    return ''


def city_of(addr):
    t = clean(addr).split()
    return t[1] if len(t) > 1 and re.match(r'^[가-힣]{1,6}(시|군|구)$', t[1]) else ''


def tags(title, ctype, overview=''):
    out = [TYPE_LABEL.get(str(ctype), '')]
    text = title + ' ' + overview[:120]
    for k in KEYWORDS:
        if k in text and k not in out:
            out.append(k)
    return [x for x in out if x][:5]


def first_sentence(s, n=90):
    s = clean(s)
    m = re.match(r'(.{12,}?[.!?])(\s|$)', s)
    x = m.group(1) if m else s
    return x if len(x) <= n else x[:n - 1] + '…'


def ymd(s):
    s = re.sub(r'\D', '', str(s or ''))
    return f'{s[:4]}-{s[4:6]}-{s[6:8]}' if len(s) >= 8 else ''


def photos(images, common, max_n=6):
    out, seen = [], set()
    cands = list(images or [])
    if common.get('firstimage'):
        cands.insert(0, {'originimgurl': common.get('firstimage'), 'smallimageurl': common.get('firstimage2'), 'cpyrhtDivCd': common.get('cpyrhtDivCd'), 'imgname': '대표'})
    for im in cands:
        u = str(im.get('originimgurl') or '').replace('http://', 'https://')
        code = str(im.get('cpyrhtDivCd') or '').strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append({'url': u, 'thumb': str(im.get('smallimageurl') or '').replace('http://', 'https://') or u,
                    'licenseCode': code or None, 'license': LICENSE.get(code, ''), 'source': '한국관광공사',
                    'usable': code in LICENSE,
                    # 자동 확인 규칙: 1유형은 출처표시만, 3유형은 원본 그대로(변경 금지). 2·4유형은 usable=False라 받지 않음
                    'rights': {'Type1': 'AUTO', 'Type3': 'AUTO_NOEDIT'}.get(code, '')})
        if len(out) >= max_n:
            break
    return out


def place(common, intro, images, ctype, checked, max_over=400):
    cid = str(common.get('contentid') or '')
    title = clean(common.get('title'))
    over = clean(common.get('overview'))
    f = INTRO.get(str(ctype), INTRO['12'])
    hours = pick(intro, f['hours'])
    fair = pick(intro, f.get('fair', []))
    if fair:
        hours = (hours + ' · ' if hours else '') + '장날 ' + fair
    addr = ' '.join(x for x in [clean(common.get('addr1')), clean(common.get('addr2'))] if x)
    rec = {
        'feedId': 'TA-' + cid, 'contentId': cid, 'contentTypeId': str(ctype), 'modifiedtime': str(common.get('modifiedtime') or ''),
        'n': title, 'a': addr, 'ar': region_of(common), 'r': city_of(addr), 'k': tags(title, ctype, over),
        'why': first_sentence(over), 'summary': over[:max_over] + ('…' if len(over) > max_over else ''),
        'hours': hours, 'closed': pick(intro, f['closed']), 'fee': pick(intro, f['fee']), 'parking': pick(intro, f['parking']),
        'phone': clean(common.get('tel')) or pick(intro, f['phone']), 'stay': pick(intro, f['stay']),
        'homepage': href(common.get('homepage')),
        'lat': _num(common.get('mapy')), 'lng': _num(common.get('mapx')), 'coordState': 'SOURCE_PROVIDED',
        'sourceUrl': href(common.get('homepage')) or SOURCE_PAGE, 'sourceLabel': SOURCE_LABEL + (' · 공식 홈페이지' if href(common.get('homepage')) else f' (contentId {cid})'),
        'checkedAt': checked, 'photos': photos(images, common),
    }
    return {k: v for k, v in rec.items() if v not in ('', None, [])}


def event(common, intro, images, checked, max_over=400):
    cid = str(common.get('contentid') or '')
    over = clean(common.get('overview'))
    addr = ' '.join(x for x in [clean(common.get('addr1')), clean(common.get('addr2'))] if x)
    home = href(intro.get('eventhomepage')) or href(common.get('homepage'))
    rec = {
        'feedId': 'TA-E-' + cid, 'contentId': cid, 'contentTypeId': '15', 'modifiedtime': str(common.get('modifiedtime') or ''),
        'name': clean(common.get('title')), 'start_date': ymd(intro.get('eventstartdate') or common.get('eventstartdate')),
        'end_date': ymd(intro.get('eventenddate') or common.get('eventenddate')),
        'place_name': clean(intro.get('eventplace')), 'address': addr, 'region': region_of(common), 'city': city_of(addr),
        'hours': clean(intro.get('playtime')), 'fee': clean(intro.get('usetimefestival')), 'organizer': clean(intro.get('sponsor1')),
        'phone': clean(intro.get('sponsor1tel')) or clean(common.get('tel')), 'why': first_sentence(over),
        'summary': over[:max_over] + ('…' if len(over) > max_over else ''), 'theme': tags(clean(common.get('title')), '15', over)[1:],
        'source_url': home or SOURCE_PAGE, 'source_label': SOURCE_LABEL + (' · 행사 홈페이지' if home else f' (contentId {cid})'),
        'lat': _num(common.get('mapy')), 'lng': _num(common.get('mapx')), 'checkedAt': checked, 'photos': photos(images, common),
    }
    return {k: v for k, v in rec.items() if v not in ('', None, [])}


def _num(v):
    try:
        f = float(v)
        return f if f else None
    except (TypeError, ValueError):
        return None
