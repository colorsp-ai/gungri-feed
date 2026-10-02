"""눈·입·손·머리·몸 세부 유형 분류 (앱과 같은 taxonomy.json 규칙). 앱의 r17_taxo.js 와 결과가 같아야 한다."""
import json, os, re

_P = os.path.join(os.path.dirname(__file__), 'taxonomy.json')
TAXO = json.load(open(_P, encoding='utf-8'))
_PR = [(r['sub'], r['axis'], re.compile(r['n']) if r.get('n') else None, re.compile(r['t']) if r.get('t') else None) for r in TAXO['placeRules']]
_ER = [(r['sub'], r['axis'], re.compile(r['re'])) for r in TAXO['eventRules']]


def sub_of_place(name, tags=None):
    """장소 이름·태그 → 세부 유형(없으면 '')."""
    name = str(name or ''); tags = [str(t) for t in (tags or [])]
    for sub, axis, n, t in _PR:
        if n and n.search(name):
            return sub
        if t and any(t.search(x) for x in tags):
            return sub
    return ''


def sub_of_event(name, theme=None):
    text = str(name or '') + ' ' + ' '.join(theme or [])
    for sub, axis, rx in _ER:
        if rx.search(text):
            return sub
    return TAXO['eventDefault']['sub']
