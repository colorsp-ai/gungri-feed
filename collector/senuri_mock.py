"""키 없이 시험하기 위한 예시 응답(실제 응답 형식을 추정해 만든 것입니다)."""
def _item(i, title, place, end, extra=''):
    return f'<item><jobId>J{i}</jobId><recrtTitle>{title}</recrtTitle><emplymShpNm>시간제</emplymShpNm><jobclsNm>청소·시설</jobclsNm><workPlaceNm>{place}</workPlaceNm><acptInstNm>예시기관{i}</acptInstNm><toAcptDd>{end}</toAcptDd>{extra}</item>'
LIST = ('<response><header><resultCode>00</resultCode><resultMsg>OK</resultMsg></header><body><items>'
  + _item(1, '구리시 아파트 경비원 모집', '경기 구리시 인창동', '20991231')
  + _item(2, '남양주 도서관 사서보조', '경기 남양주시 다산동', '20991231')
  + _item(3, '서울 강남 주차관리', '서울 강남구', '20991231')
  + _item(4, '구리 마감된 공고', '경기 구리시', '20200101')
  + _item(5, '남양주 가입비 선입금 필수 판매원', '경기 남양주시', '20991231')
  + _item(1, '중복 공고', '경기 구리시', '20991231')
  + '</items><totalCount>6</totalCount></body></response>')
DETAIL = '<response><header><resultCode>00</resultCode></header><body><items><item><jobId>J1</jobId><detailContent>&lt;p&gt;주 3일 근무, 만 60세 이상 우대&lt;/p&gt;</detailContent><age>60세 이상</age><clltPrnnum>2</clltPrnnum><homepage>https://example.org/j1</homepage></item></items></body></response>'
def mock_fetch(url, opener=None):
    if 'id=' in url:
        return DETAIL if 'id=J1' in url else '<response><header><resultCode>00</resultCode></header><body><items></items></body></response>'
    return LIST
