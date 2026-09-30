"""한국관광공사 TourAPI 4.0 (KorService2) 클라이언트 — 표준 라이브러리만 사용.
- 하루 호출 한도(개발계정 1,000건)를 넘지 않도록 호출 수를 셉니다.
- 서비스키는 공공데이터포털의 '일반 인증키(Decoding)'를 권장합니다. Encoding 키(%가 들어간 키)도 그대로 받습니다.
- 오류 응답이 JSON이 아닌 XML로 오는 경우(키 미등록 등)를 구분해 알려 줍니다."""
import json, time, urllib.parse, urllib.request, urllib.error, http.client, os, re

BASE = os.environ.get('TOURAPI_BASE', 'https://apis.data.go.kr/B551011/KorService2')


class QuotaExceeded(Exception):
    pass


class TourAPIError(Exception):
    pass


class TourAPI:
    def __init__(self, service_key, mobile_app='GUNGRI', budget=900, opener=None, sleep=0.15):
        if not service_key:
            raise TourAPIError('TOURAPI_KEY(서비스키)가 없습니다. 공공데이터포털에서 받은 키를 환경변수 TOURAPI_KEY로 넣어 주세요.')
        self.key = service_key.strip()
        self.app = mobile_app
        self.budget = budget
        self.calls = 0
        self.opener = opener or self._http
        self.sleep = sleep
        self.log = []

    # ---------------------------------------------------------------- transport
    def _http(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': 'GUNGRI-collector/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode('utf-8', 'replace')

    def _url(self, op, params):
        q = {'MobileOS': 'ETC', 'MobileApp': self.app, '_type': 'json'}
        q.update({k: v for k, v in params.items() if v not in (None, '')})
        qs = urllib.parse.urlencode(q)
        key = self.key if '%' in self.key else urllib.parse.quote(self.key, safe='')
        return f'{BASE}/{op}?serviceKey={key}&{qs}'

    def call(self, op, **params):
        if self.calls >= self.budget:
            raise QuotaExceeded(f'오늘 호출 예산 {self.budget}건을 다 썼습니다')
        url = self._url(op, params)
        last = None
        for attempt in range(3):
            try:
                self.calls += 1
                txt = self.opener(url)
                break
            except urllib.error.HTTPError as e:
                last = f'HTTP {e.code}'
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(2 * (attempt + 1)); continue
                raise TourAPIError(f'{op}: {last}')
            except urllib.error.URLError as e:
                last = str(e.reason); time.sleep(2 * (attempt + 1))
            except (TimeoutError, OSError, http.client.HTTPException) as e:  # 읽기 시간 초과·연결 끊김: 잠시 뒤 다시 시도
                last = f'{type(e).__name__}: {e}'; time.sleep(3 * (attempt + 1))
        else:
            raise TourAPIError(f'{op}: 연결 실패 ({last})')
        if self.sleep:
            time.sleep(self.sleep)
        return self._parse(op, txt)

    @staticmethod
    def _parse(op, txt):
        t = txt.strip()
        if not t.startswith('{'):
            m = re.search(r'<returnAuthMsg>([^<]+)</returnAuthMsg>', t) or re.search(r'<resultMsg>([^<]+)</resultMsg>', t)
            raise TourAPIError(f'{op}: JSON이 아닌 응답 — {m.group(1) if m else t[:120]}')
        d = json.loads(t)
        resp = d.get('response') or {}
        head = resp.get('header') or {}
        code = str(head.get('resultCode', '0000'))
        if code not in ('0000', '00'):
            raise TourAPIError(f"{op}: {code} {head.get('resultMsg', '')}")
        body = resp.get('body') or {}
        items = body.get('items')
        if not items:  # 결과 없음이면 items가 "" 로 옴
            lst = []
        else:
            it = items.get('item') if isinstance(items, dict) else items
            lst = it if isinstance(it, list) else ([it] if it else [])
        return {'items': lst, 'total': int(body.get('totalCount') or 0), 'page': int(body.get('pageNo') or 1)}

    # ---------------------------------------------------------------- operations
    def area_based(self, content_type, ldong_regn, page=1, rows=100, arrange='C'):
        """수정일순(C) 목록 — 새로 바뀐 것부터"""
        return self.call('areaBasedList2', contentTypeId=content_type, lDongRegnCd=ldong_regn, arrange=arrange, numOfRows=rows, pageNo=page)

    def festivals(self, start_yyyymmdd, page=1, rows=100, ldong_regn=None):
        return self.call('searchFestival2', eventStartDate=start_yyyymmdd, lDongRegnCd=ldong_regn, arrange='C', numOfRows=rows, pageNo=page)

    def common(self, content_id):
        r = self.call('detailCommon2', contentId=content_id)
        return r['items'][0] if r['items'] else {}

    def intro(self, content_id, content_type):
        r = self.call('detailIntro2', contentId=content_id, contentTypeId=content_type)
        return r['items'][0] if r['items'] else {}

    def images(self, content_id):
        return self.call('detailImage2', contentId=content_id, imageYN='Y', numOfRows=10, pageNo=1)['items']
