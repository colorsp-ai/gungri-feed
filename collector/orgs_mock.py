"""키 없이 시험하는 예시 응답(실제 형식을 추정한 것)."""
def mock_fetch(url, opener=None):
    it = lambda n, a, t: f'<item><orgName>{n}</orgName><orgAddr>{a}</orgAddr><orgTelNo>{t}</orgTelNo><projYear>2026</projYear></item>'
    if 'dstrCd2=4131000000' in url:
        body = it('예시 구리시니어클럽', '경기 구리시 예시로 1', '031-000-0000')
    elif 'dstrCd2=4136000000' in url:
        body = it('예시 남양주시니어클럽', '경기 남양주시 예시로 2', '031-111-1111')
    else:
        body = it('예시 서울클럽', '서울 강남구', '02-000-0000')
    return f'<response><header><resultCode>00</resultCode></header><body><items>{body}</items><totalCount>1</totalCount></body></response>'
