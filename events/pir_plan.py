#!/usr/bin/env python3
"""Экспорт официальных SVG-планов PIR 2026 и координат стендов.

Источник: https://pirexpo.com/map/{13,14,15} — SSR содержит inline SVG,
элементы <text data-number-label="…" x="…" y="…">СТЕНД</text>.
Не придумываем геометрию: координаты маркировки берём непосредственно с плана.
Кэш оригиналов: cache/pir-expo/official_hall_*.svg (вне публичного репозитория).
"""
import html, json, pathlib, re, sys, urllib.request, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
CACHE=ROOT.parent/'Multi-Agent Orchestration Platform/cache/pir-expo'
OUT=ROOT/'pir-expo/plan'
HALLS=('13','14','15')
HOMO=str.maketrans('АВСЕНКМОРТХавсенкмортх','ABCEHKMOPTXabcehkmoptx')

def norm(s): return re.sub(r'[^A-Z0-9]','',html.unescape(str(s or '')).translate(HOMO).upper())
def extract(hall):
 cache=CACHE/f'official_hall_{hall}.svg'
 if cache.exists() and '--refresh' not in sys.argv:
  svg=cache.read_text(encoding='utf-8')
 else:
  req=urllib.request.Request(f'https://pirexpo.com/map/{hall}',headers={'User-Agent':'Mozilla/5.0'})
  page=urllib.request.urlopen(req,timeout=45).read().decode('utf-8')
  match=re.search(r'<svg\b[^>]*class="hall-plan"[^>]*>.*?</svg>',page,re.S)
  if not match: raise RuntimeError(f'Зал {hall}: официальный inline SVG не найден')
  svg=match.group(0)
  CACHE.mkdir(parents=True,exist_ok=True);cache.write_text(svg,encoding='utf-8')
 view=re.search(r'viewBox="([^"]+)"',svg)
 if not view: raise RuntimeError(f'Зал {hall}: нет viewBox')
 _,_,w,h=map(float,view.group(1).split())
 points={}
 for x,y,txt in re.findall(r'<text\b[^>]*data-number-label="[^"]+"[^>]*x="([\d.]+)"\s+y="([\d.]+)"[^>]*>(.*?)</text>',svg,re.S):
  key=norm(re.sub(r'<[^>]+>','',txt))
  if re.fullmatch(r'[1-4][A-Z]{1,2}\d{1,3}[A-Z]?',key):
   points.setdefault(key,[round(float(x)/w*100,3),round(float(y)/h*100,3)])
 # Удаляем Angular-директивы, обработчики и внешние зависимости; svg используется как <img>.
 clean=re.sub(r'\s+_ngcontent-[\w-]+="[^"]*"','',svg)
 clean=re.sub(r'\s+jsaction="[^"]*"','',clean)
 clean=re.sub(r'\s+on[a-zA-Z]+="[^"]*"','',clean)
 clean=re.sub(r'<!---->','',clean)
 clean=re.sub(r'<svg\b','<svg xmlns="http://www.w3.org/2000/svg"',clean,count=1)
 ET.fromstring(clean)
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/f'hall-{hall}.svg').write_text(clean,encoding='utf-8')
 return {'img':f'hall-{hall}.svg','w':w,'h':h,'stands':points}

if __name__=='__main__':
 plans={hall:extract(hall) for hall in HALLS}
 (OUT/'plan.json').write_text(json.dumps(plans,ensure_ascii=False,indent=1),encoding='utf-8')
 print('Официальные планы:',{hall:(len(x['stands']),round(x['w']),round(x['h'])) for hall,x in plans.items()})
 rows=json.loads((ROOT/'pir-expo/exhibitors.json').read_text())
 for hall in HALLS:
  target=[r for r in rows if r['hall']==hall and r['prio'] in ('A','B')]
  missing=[(r['name'],r['stand']) for r in target if norm(r['stand'].split(',')[0]) not in plans[hall]['stands']]
  if missing: raise RuntimeError(f'Приоритетные участники без метки в зале {hall}: {missing}')
 print('Все A/B стенды сопоставлены с официальной схемой')
