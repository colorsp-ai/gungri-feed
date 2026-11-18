"""키 없이 시험하는 예시 응답(실제 형식을 추정한 것)."""
def mock_fetch(url, opener=None):
    it = lambda n, a, t: f'<item><insttNm>{n}</insttNm><addr>{a}</addr><telNo>{t}</telNo><insttTypeNm>시니어클럽</insttTypeNm></item>'
    return ('<response><header><resultCode>00</resultCode></header><body><items>'
            + it('예시 구리시니어클럽', '경기 구리시 예시로 1', '031-000-0000')
            + it('예시 남양주시니어클럽', '경기 남양주시 예시로 2', '031-111-1111')
            + it('예시 서울클럽', '서울 강남구', '02-000-0000') + '</items><totalCount>3</totalCount></body></response>')
