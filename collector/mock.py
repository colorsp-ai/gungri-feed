"""인증키 없이 수집기를 시험하는 가짜 TourAPI 응답(실제 응답 모양과 같게). 내용은 시험용 예시입니다."""
import datetime, json, urllib.parse

T = datetime.date.today()
D = lambda n: (T + datetime.timedelta(days=n)).strftime('%Y%m%d')
PLACES = {
    ('14', '43'): [{'contentid': '900001', 'title': '국립현대미술관 청주', 'addr1': '충청북도 청주시 청원구 상당로 314', 'lDongRegnCd': '43', 'modifiedtime': '20260920100000', 'contenttypeid': '14'}],
    ('12', '11'): [{'contentid': '900002', 'title': '서울숲', 'addr1': '서울특별시 성동구 뚝섬로 273', 'lDongRegnCd': '11', 'modifiedtime': '20260921090000', 'contenttypeid': '12'},
                   {'contentid': '900009', 'title': '○○ 키즈카페', 'addr1': '서울특별시 강남구', 'lDongRegnCd': '11', 'modifiedtime': '20260921090000', 'contenttypeid': '12'}],
    ('12', '41'): [{'contentid': '900003', 'title': '구리 동구릉', 'addr1': '경기도 구리시 동구릉로 197', 'lDongRegnCd': '41', 'modifiedtime': '20260922080000', 'contenttypeid': '12'},
                   {'contentid': '900005', 'title': '행주산성', 'addr1': '경기도 고양시 덕양구 행주로15번길 89', 'lDongRegnCd': '41', 'modifiedtime': '20260922070000', 'contenttypeid': '12'}],
    ('38', '41'): [{'contentid': '900004', 'title': '구리전통시장', 'addr1': '경기도 구리시 구리시장로 19', 'lDongRegnCd': '41', 'modifiedtime': '20260919080000', 'contenttypeid': '38'}],
}
COMMON = {
    '900001': {'overview': '담배공장을 고친 수장고형 미술관입니다. 소장품이 보관된 모습을 가까이서 볼 수 있습니다.', 'tel': '043-261-1400', 'homepage': '<a href="https://www.mmca.go.kr/" target="_blank">https://www.mmca.go.kr</a>', 'firstimage': 'http://tong.visitkorea.or.kr/cms/resource/01/900001_image2_1.jpg', 'cpyrhtDivCd': 'Type3', 'mapx': '127.4905', 'mapy': '36.6512'},
    '900002': {'overview': '뚝섬 일대의 대규모 도시 숲입니다.<br>평지 산책로가 넓어 천천히 걷기 좋습니다.', 'tel': '02-460-2905', 'homepage': '', 'firstimage': 'http://tong.visitkorea.or.kr/cms/resource/02/900002_image2_1.jpg', 'cpyrhtDivCd': 'Type1', 'mapx': '127.0374', 'mapy': '37.5444'},
    '900003': {'overview': '조선 왕릉 아홉 기가 모인 세계유산입니다. 숲길이 완만해 천천히 걷기 좋습니다.', 'tel': '031-563-2909', 'homepage': '', 'firstimage': 'http://tong.visitkorea.or.kr/cms/resource/03/900003_image2_1.jpg', 'cpyrhtDivCd': 'Type1', 'mapx': '127.1330', 'mapy': '37.6213'},
    '900005': {'overview': '한강을 내려다보는 산성 유적입니다. 성곽길 전망이 좋습니다.', 'tel': '031-8075-4642', 'homepage': '', 'firstimage': '', 'cpyrhtDivCd': '', 'mapx': '126.8119', 'mapy': '37.6005'},
    '900004': {'overview': '구리역 가까이의 전통시장입니다. 떡볶이와 전 골목이 유명합니다.', 'tel': '', 'homepage': '', 'firstimage': 'http://tong.visitkorea.or.kr/cms/resource/04/900004_image2_1.jpg', 'cpyrhtDivCd': '', 'mapx': '127.1393', 'mapy': '37.6027'},
    '900101': {'overview': '한강 둔치에 코스모스가 가득 피는 가을 축제입니다.', 'tel': '031-550-2065', 'homepage': '', 'firstimage': 'http://tong.visitkorea.or.kr/cms/resource/11/900101_image2_1.jpg', 'cpyrhtDivCd': 'Type1', 'mapx': '127.1402', 'mapy': '37.5836'},
}
INTRO = {
    '900001': {'usetimeculture': '10:00~18:00<br>(입장마감 17:00)', 'restdateculture': '매주 월요일, 1월 1일', 'usefee': '무료(일부 전시 유료)', 'parkingculture': '가능', 'infocenterculture': '043-261-1400', 'spendtime': '2시간'},
    '900002': {'usetime': '상시 개방', 'restdate': '연중무휴', 'parking': '유료 주차장', 'infocenter': '02-460-2905'},
    '900003': {'usetime': '09:00~18:00 (계절별 상이)', 'restdate': '매주 월요일', 'usefee': '어른 1,000원', 'parking': '가능', 'infocenter': '031-563-2909'},
    '900005': {'usetime': '09:00~18:00', 'restdate': '매주 월요일', 'parking': '가능(유료)', 'infocenter': '031-8075-4642'},
    '900004': {'opentime': '09:00~21:00', 'restdateshopping': '점포별 상이', 'parkingshopping': '공영주차장', 'infocentershopping': '031-000-0000', 'fairday': '없음(상설)'},
    '900101': {'eventstartdate': D(10), 'eventenddate': D(16), 'eventplace': '구리한강시민공원', 'playtime': '10:00~18:00', 'usetimefestival': '무료', 'sponsor1': '구리시', 'sponsor1tel': '031-550-2065', 'eventhomepage': '<a href="https://www.guri.go.kr/">구리시청</a>'},
}
IMAGES = {
    '900001': [{'originimgurl': 'http://tong.visitkorea.or.kr/cms/resource/01/900001_image2_2.jpg', 'smallimageurl': 'http://tong.visitkorea.or.kr/cms/resource/01/900001_image3_2.jpg', 'cpyrhtDivCd': 'Type3', 'imgname': '전시실'}],
    '900002': [{'originimgurl': 'http://tong.visitkorea.or.kr/cms/resource/02/900002_image2_2.jpg', 'smallimageurl': '', 'cpyrhtDivCd': 'Type1', 'imgname': '산책로'}],
}
FESTIVALS = [
    {'contentid': '900101', 'title': '구리 코스모스 축제', 'addr1': '경기도 구리시 토평동 1', 'lDongRegnCd': '41', 'eventstartdate': D(10), 'eventenddate': D(16), 'modifiedtime': '20260925090000'},
    {'contentid': '900102', 'title': '지난 축제(끝남)', 'addr1': '서울특별시 중구', 'lDongRegnCd': '11', 'eventstartdate': D(-20), 'eventenddate': D(-5), 'modifiedtime': '20260901090000'},
]


def wrap(items):
    return json.dumps({'response': {'header': {'resultCode': '0000', 'resultMsg': 'OK'}, 'body': {'items': {'item': items} if items else '', 'numOfRows': 100, 'pageNo': 1, 'totalCount': len(items)}}}, ensure_ascii=False)


class MockOpener:
    def __call__(self, url):
        p = urllib.parse.urlparse(url)
        op = p.path.rsplit('/', 1)[-1]
        q = {k: v[0] for k, v in urllib.parse.parse_qs(p.query).items()}
        if op == 'areaBasedList2':
            return wrap(PLACES.get((q.get('contentTypeId'), q.get('lDongRegnCd')), []) if q.get('pageNo', '1') == '1' else [])
        if op == 'searchFestival2':
            return wrap(FESTIVALS if q.get('pageNo', '1') == '1' else [])
        cid = q.get('contentId', '')
        if op == 'detailCommon2':
            base = next((x for v in PLACES.values() for x in v if x['contentid'] == cid), None) or next((x for x in FESTIVALS if x['contentid'] == cid), {})
            return wrap([dict(base, **COMMON.get(cid, {}))] if base else [])
        if op == 'detailIntro2':
            return wrap([INTRO.get(cid, {})])
        if op == 'detailImage2':
            return wrap(IMAGES.get(cid, []))
        return '<OpenAPI_ServiceResponse><cmmMsgHeader><returnAuthMsg>UNKNOWN_OPERATION</returnAuthMsg></cmmMsgHeader></OpenAPI_ServiceResponse>'
