#!/usr/bin/env python3
"""Контроль локального комплекта PIR без записи в боевой опросник."""
import json, pathlib, re, subprocess, xml.etree.ElementTree as ET
from collections import Counter
ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/'pir-expo'
rows=json.loads((P/'exhibitors.json').read_text())
c=Counter(r['prio'] for r in rows)
assert (len(rows),c['A'],c['B'],c['C'])==(694,33,54,607),(len(rows),c)
assert sum(not r['stand'] for r in rows)==60
assert all(not any(k.startswith('_') for k in r) for r in rows)
assert not any('email' in r or 'phone' in r for r in rows)
assert {r['stand'] for r in rows if 'прямой заказ/бронь' in r['tags']}=={'3E60','3HC4','3HC8','4HC24'}
assert sum('брендформанс' in r['tags'] for r in rows)==29
assert sum('ссылка на МП — кто селлер?' in r['tags'] for r in rows)==3
plan=json.loads((P/'plan/plan.json').read_text())
assert set(plan)=={'13','14','15'}
assert sum(len(p['stands']) for p in plan.values())==612
for hall,p in plan.items():
    svg=P/'plan'/p['img']
    assert svg.is_file() and svg.stat().st_size>100_000
    ET.parse(svg)
    assert all(0<=x<=100 and 0<=y<=100 for x,y in p['stands'].values())
for r in rows:
    if r['prio'] in ('A','B'):
        key=r['stand'].split(',')[0].upper().translate(str.maketrans('АВСЕНКМОРТХ','ABCEHKMOPTX'))
        assert key in plan[r['hall']]['stands'],(r['name'],r['stand'])
for filename in ['events.html','pir-expo/presenter.html','pir-expo/index.html','pir-expo/presenter-full.html','pir-expo/exhibitors.html','pir-expo/map.html']:
    s=(ROOT/filename).read_text()
    assert '<!doctype html>' in s.lower(),filename
    assert 'ПИР Экспо' in s,filename
    for index,js in enumerate(re.findall(r'<script[^>]*>(.*?)</script>',s,re.S)):
        if not js.strip():continue
        r=subprocess.run(['node','--check'],input=js,text=True,capture_output=True)
        assert r.returncode==0,(filename,index,r.stderr[:400])
short=(P/'presenter.html').read_text()
assert 'ПИР Экспо · 26–29.10' in short
assert 'Кто заполняет' not in short
assert 'Маршрут и ссылки на планы организатора' in short
assert 'план зала организатор не публикует' not in short
assert 'рост узнаваемости марки' in short
assert 'партнёры продают на МП' in short
map_html=(P/'map.html').read_text()
assert 'Официальный план с метками Click Out' in map_html
assert 'plan/hall-' not in map_html  # путь к SVG задаётся данными плана, а не вымышленной картинкой
assert 'presenter.html?c=' in map_html
for filename in ['index.html','presenter-full.html']:
    s=(P/filename).read_text()
    assert len(re.findall(r'<section\b',s))==16,(filename,len(re.findall(r'<section\b',s)))
    for forbidden in ['кэшбек','сертифицированный партнёр','внешний трафик на карточки','Сопровождение: чем больше','Бьюти-бренд','Если вы агентство']:
        assert forbidden not in s,(filename,forbidden)
print('PIR: 694 = 33 A + 54 B + 607 C; 3 официальных SVG, 612 стендов, все 87 A/B на плане; JS — OK')
