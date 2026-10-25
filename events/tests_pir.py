#!/usr/bin/env python3
"""Контроль локального комплекта PIR без записи в боевой опросник."""
import json, pathlib, re, subprocess
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
for filename in ['index.html','presenter-full.html']:
    s=(P/filename).read_text()
    assert len(re.findall(r'<section\b',s))==16,(filename,len(re.findall(r'<section\b',s)))
    for forbidden in ['кэшбек','сертифицированный партнёр','внешний трафик на карточки','Сопровождение: чем больше','Бьюти-бренд','Если вы агентство']:
        assert forbidden not in s,(filename,forbidden)
print('PIR: 694 = 33 A (4 сети + 29 брендов) + 54 B + 607 C; 60 без стенда; JS и брендформанс — OK')
