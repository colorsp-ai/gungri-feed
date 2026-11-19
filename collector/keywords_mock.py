"""키 없이 시험하는 가짜 AI 응답: 글에 단어가 있으면 붙이고, 목록 밖 단어·근거 없는 편의 정보를 일부러 섞어 걸러지는지 본다."""
import json, re
def mock_fetch(prompt):
    out = []
    for m in re.finditer(r'\[id=([^\]]+)\]\n(.*?)(?=\n\n\[id=|\Z)', prompt.split('장소\n', 1)[1], re.S):
        pid, body = m.group(1), m.group(2)
        kw = []
        if '단풍' in body:
            kw.append({'k': '단풍', 'est': False, 'ev': '단풍'})
        if '은행나무' in body:
            kw.append({'k': '은행나무', 'est': False, 'ev': '은행나무'})
        if '야경' in body:
            kw.append({'k': '야경', 'est': False, 'ev': '야경'})
        kw.append({'k': '없는키워드', 'est': False, 'ev': ''})                   # 목록 밖 → 버려져야 함
        kw.append({'k': '반려견 동반', 'est': False, 'ev': '강아지와 함께'})        # 글에 없는 근거 → 버려져야 함
        if '주차' in body:
            kw.append({'k': '주차 편함', 'est': False, 'ev': '주차'})
        out.append({'id': pid, 'kw': kw})
    return json.dumps(out, ensure_ascii=False)
