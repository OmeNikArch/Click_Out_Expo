#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Список участников «Мир детства + CJF 2026» с разметкой под направления Церебро.
Вход: events/raw_icatalog/{md,cjf}_exhibitors.json — результат events/icatalog_crawl.py
(страницы онлайн-каталога Экспоцентра: стенд, страна, город, сайт, описание, рубрики, телефон, e-mail).
Выход: mirdetstva/exhibitors.json (без телефонов и почт — страница публичная) и mirdetstva/exhibitors.html.
Полная версия с контактами — аргументом --full <путь> (кладём в ИСХОДЯЩИЕ, в репозиторий не пушим).
Запуск из корня репозитория: python3 events/exhibitors_build.py [--full /путь/full.json]
"""
import json, re, sys, pathlib, html

ROOT = pathlib.Path(__file__).parent.parent
RAW = ROOT / "events" / "raw_icatalog"
OUT = ROOT / "mirdetstva"

EXPO = {"md": ("Мир детства", "залы 10–11"), "cjf": ("CJF Детская мода", "зал 9")}

# ручные поправки приоритета по стенду: упаковка, батарейки, сервисы, медиа, китайский сорсинг — не наша аудитория
OVERRIDE = {
    "10E050": "B", "11G130": "B", "11F006": "B", "9B018": "B", "11F150": "B", "11C070": "B", "11C105": "C",
    "10C007": "C", "10D028": "C", "11C155": "C", "11D001": "C",
}
# ★ первыми: сильные российские бренды с розницей / своим магазином (по описаниям каталога и сайтам); ключ — фрагмент названия
TOP = [
    # CJF
    "kapika", "наследникъ выжанова", "toucankids", "minidino", "келеш", "piccino bellino", "парижская коммуна", "юки-кидс",
    "гудвин", "яхонт", "brinco", "gulsara", "славянка", "nikastyle", "malini", "дести", "ballover", "elicrown", "bokka",
    "маринатекс", "асселина", "флёр", "формула формы",
    # Мир детства
    "симбат", "степ пазл", "смолтойс", "zhorya", "игротрейд", "brick labs", "томь-сервис", "дельта, ооо", "бумбарам",
    "veselo games", "todi&co", "оптипром", "аркаданн", "балу, ооо", "конаково", "7-я, ооо", "mazari", "свежий ветер",
    "mta tm", "урал тойз", "оранж", "хохломская роспись", "нобикум", "plast team", "parklon", "madebybear", "берканамама",
    "данковская", "магия хобби", "астком", "i love to play", "азбукварик", "ридер, ооо",
]

def is_top(name):
    n = name.lower()
    return any(k in n for k in TOP)

def low(r):
    return ((r.get("Описание", "") or "") + " " + " ".join(r.get("Рубрики", []) or []) + " " + r.get("name", "")).lower()

def classify(r):
    t = low(r)
    if r.get("Страна", "") != "Россия":
        return ["иностр."]
    tags = []
    if re.search(r"дистриб|оптов|опт\b|поставщик|импорт|торгов(ая|ый) (дом|компан)|представитель|представляет бренд|эксклюзивн", t): tags.append("дистрибьютор/опт")
    if re.search(r"производ|фабрик|швейн|изготавлива|выпуска|собственн(ое|ого) производств|шьём|шьем|мануфактур", t): tags.append("производитель")
    if re.search(r"интернет-магазин|собственн\w* сайт|розничн\w* сет|сеть магазинов|фирменн\w* магазин|ритейл|розниц", t): tags.append("своя розница/e-com")
    if re.search(r"wildberries|ozon|озон|вайлдберриз|маркетплейс|яндекс маркет", t): tags.append("маркетплейсы")
    if re.search(r"издательств|книг|журнал", t): tags.append("издательство/медиа")
    if re.search(r"банк|финанс|шеринг|логистик|сертифика|услуг|сервис|платформ|обучени|франшиз", t) and "производ" not in t: tags.append("сервис/услуги")
    if re.search(r"школьн\w* форм|школьн", t): tags.append("школьная форма")
    if re.search(r"новорожд|0\+|для малышей|коляск|автокресл|подгузник", t): tags.append("0–3 / новорождённые")
    if re.search(r"игруш|конструктор|пазл|настольн", t): tags.append("игрушки")
    if re.search(r"канцеляр|творчеств|наборы для", t): tags.append("канцелярия/творчество")
    if re.search(r"мебел|текстил|постельн", t): tags.append("мебель/текстиль")
    if re.search(r"обув", t): tags.append("обувь")
    return tags or ["прочее"]

def priority(r, tags):
    st = (r.get("Стенд", "") or "").split(",")[0].strip()
    if st in OVERRIDE: return OVERRIDE[st]
    if "иностр." in tags: return "C"
    site = bool(r.get("Сайт"))
    if site and ({"производитель", "своя розница/e-com", "маркетплейсы"} & set(tags)): return "A"
    return "B"

def load():
    rows = []
    for key in ("md", "cjf"):
        for r in json.load(open(RAW / f"{key}_exhibitors.json", encoding="utf-8")):
            tags = classify(r); pr = priority(r, tags)
            st = (r.get("Стенд", "") or "").replace(" ", "")
            first = st.split(",")[0]
            hall = re.match(r"(\d+)", first).group(1) if re.match(r"(\d+)", first) else ""
            rows.append({
                "expo": key, "hall": hall, "stand": st, "name": r.get("name", ""), "city": r.get("Город", ""),
                "country": r.get("Страна", ""), "site": r.get("Сайт", ""), "descr": r.get("Описание", ""),
                "rubrics": r.get("Рубрики", []) or [], "tags": tags, "prio": pr, "top": is_top(r.get("name", "")),
                "_phone": r.get("Телефон", ""), "_email": r.get("E-mail", ""), "_addr": r.get("Адрес", ""), "_id": r.get("id", ""),
            })
    def key(x):
        m = re.match(r"(\d+)([A-Z])(\d+)", x["stand"]); return (int(m.group(1)), m.group(2), int(m.group(3))) if m else (99, "Z", 0)
    rows.sort(key=key)
    return rows

CSS = """
:root{--bg:#000;--card:#161618;--card2:#111;--txt:#E7E6E6;--mute:#A5A5A5;--y:#FDD101;--w:#fff;--head:'Unbounded',Arial,sans-serif;--body:Arial,Helvetica,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--txt);font-family:var(--body);padding:0 0 60px}
.wrap{max-width:1280px;margin:0 auto;padding:28px 20px}
.kicker{display:flex;align-items:center;gap:12px;margin-bottom:14px}.kicker .bar{width:36px;height:7px;background:var(--y)}
.kicker span{font-family:var(--head);font-weight:700;font-size:12px;letter-spacing:.08em;color:var(--y);text-transform:uppercase}
h1{font-family:var(--head);font-weight:700;color:var(--w);font-size:clamp(22px,3.4vw,38px);line-height:1.12;margin-bottom:12px}
.sub{font-size:15px;line-height:1.5;color:var(--txt);max-width:90ch}.sub b{color:var(--w)}.sub a{color:var(--y)}
.legend{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));margin:18px 0 6px}
.lg{background:var(--card);border-radius:12px;padding:12px 14px;font-size:13px;line-height:1.45}.lg b{font-family:var(--head);color:var(--y);font-size:13px}
.panel{position:sticky;top:0;z-index:5;background:rgba(0,0,0,.94);backdrop-filter:blur(6px);padding:12px 0;border-bottom:1px solid #222;margin-top:14px}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px}
.row .lbl{font-family:var(--head);font-weight:700;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);min-width:74px}
.chip{border:1px solid #3a3a3a;border-radius:100px;color:var(--txt);font-size:13px;padding:6px 12px;cursor:pointer;user-select:none;background:none;font-family:inherit}
.chip.on{border-color:var(--y);color:#000;background:var(--y);font-weight:700}
.q{flex:1;min-width:200px;background:#0f0f0f;border:1px solid #2a2a2a;border-radius:12px;color:#fff;font-family:inherit;font-size:15px;padding:9px 12px;outline:none}
.q:focus{border-color:var(--y)}
.cnt{font-family:var(--head);font-weight:700;color:var(--y);font-size:13px;margin-left:auto}
.list{margin-top:14px}
.it{display:grid;grid-template-columns:96px 1fr;gap:14px;padding:14px 0;border-top:1px solid #1e1e1e;align-items:start}
.it .st{font-family:'JetBrains Mono',ui-monospace,monospace;color:var(--y);font-size:15px;line-height:1.3}
.it .st small{display:block;color:var(--mute);font-size:11px;margin-top:4px;font-family:var(--body)}
.it .nm{font-family:var(--head);font-weight:700;color:var(--w);font-size:15px;line-height:1.3}
.it .nm .pr{display:inline-block;font-size:10px;letter-spacing:.08em;padding:3px 8px;border-radius:100px;margin-right:8px;vertical-align:middle;background:#2a2a2a;color:var(--mute)}
.it .nm .pr.A{background:var(--y);color:#000}.it .nm .pr.B{background:#3a3a3a;color:#fff}
.it .nm .star{color:var(--y);margin-right:6px}
.it .meta{color:var(--mute);font-size:13px;margin-top:4px;line-height:1.45}.it .meta a{color:var(--y);text-decoration:none}
.it .tg{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.it .tg span{border:1px solid #333;border-radius:100px;font-size:11px;padding:3px 9px;color:var(--txt)}
.it .ds{font-size:13.5px;line-height:1.5;margin-top:8px;color:#cfcfcf;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;cursor:pointer}
.it.open .ds{display:block}.it .rb{display:none;color:var(--mute);font-size:12px;margin-top:6px;line-height:1.45}.it.open .rb{display:block}
.it.C{opacity:.55}
.empty{padding:40px 0;color:var(--mute)}
@media (max-width:640px){.it{grid-template-columns:1fr;gap:6px}.wrap{padding:18px 14px}}
@media print{body{background:#fff;color:#000}.panel{display:none}.it{border-color:#ccc;page-break-inside:avoid}.it .nm,.it .st{color:#000}.it .nm .pr.A{background:#000;color:#fff}.it .ds{display:block;color:#222}.it .rb{display:block;color:#555}.it .meta a{color:#000}.it.C{display:none}.lg{background:#f2f2f2}h1{color:#000}}
"""

def page(rows):
    pub = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    n_md = sum(1 for r in rows if r["expo"] == "md"); n_cjf = len(rows) - n_md
    nA = sum(1 for r in rows if r["prio"] == "A"); nTop = sum(1 for r in rows if r["top"])
    ru_md = sum(1 for r in rows if r["expo"] == "md" and r["country"] == "Россия")
    ru_cjf = sum(1 for r in rows if r["expo"] == "cjf" and r["country"] == "Россия")
    data = json.dumps(pub, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Мир детства + CJF 2026 · участники с разметкой Click Out</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="kicker"><div class="bar"></div><span>Click Out · Мир детства + CJF · 16–18.09.2026 · Крокус Экспо, павильон 2</span></div>
  <h1>{len(rows)} участников: кого искать в залах 9, 10 и 11</h1>
  <p class="sub">«Мир детства» — {n_md} стендов в залах 10–11 ({ru_md} российских, остальное — китайские и индийские фабрики), «CJF Детская мода» — {n_cjf} стендов в зале 9
  ({ru_cjf} российских). Источник — онлайн-каталог Экспоцентра, снят 17.09.2026; разметка по описаниям и сайтам — <b>{nA} компаний приоритета A</b>, из них <b>{nTop} ★ первыми</b>.
  Нажмите на описание, чтобы раскрыть рубрики. Презентация: <a href="presenter.html">версия ведущего</a> · <a href="index.html">клиентская</a> · <a href="../events.html">все выставки</a>.</p>
  <div class="legend">
    <div class="lg"><b>A</b> — российский бренд с сайтом: производитель, своя розница или маркетплейсы. Разговор про Click Out на сайт и внешний трафик на карточки.</div>
    <div class="lg"><b>B</b> — российские дистрибьюторы, оптовики, сервисы, компании без сайта. Разговор про B2B-сегмент и Директ, механику не разворачиваем.</div>
    <div class="lg"><b>C</b> — иностранные фабрики (контрактное производство) и не по профилю. К стендам не подходим.</div>
    <div class="lg"><b>★</b> — сильные бренды с розницей или своим магазином: к ним идём первыми, пока есть силы и время.</div>
  </div>
  <div class="panel">
    <div class="row"><input class="q" id="q" placeholder="Поиск: название, город, сайт, рубрика, слово из описания"><span class="cnt" id="cnt"></span></div>
    <div class="row"><span class="lbl">Выставка</span>
      <button class="chip on" data-f="expo" data-v="">все</button><button class="chip" data-f="expo" data-v="md">Мир детства · залы 10–11</button><button class="chip" data-f="expo" data-v="cjf">CJF · зал 9</button></div>
    <div class="row"><span class="lbl">Приоритет</span>
      <button class="chip" data-f="prio" data-v="top">★ первыми</button><button class="chip on" data-f="prio" data-v="A">A</button><button class="chip" data-f="prio" data-v="B">B</button><button class="chip" data-f="prio" data-v="C">C</button></div>
    <div class="row" id="tags"><span class="lbl">Сегмент</span></div>
  </div>
  <div class="list" id="list"></div>
</div>
<script>
const DATA={data};
const state={{expo:"",prio:new Set(["A"]),tags:new Set(),q:""}};
const TAGS=[...new Set(DATA.flatMap(r=>r.tags))].filter(t=>t!=="иностр.").sort();
const tagsRow=document.getElementById("tags");
TAGS.forEach(t=>{{const b=document.createElement("button");b.className="chip";b.dataset.f="tag";b.dataset.v=t;b.textContent=t;tagsRow.appendChild(b);}});
function esc(s){{return (s||"").replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));}}
function host(u){{return u.replace(/^https?:[/][/]/,"").replace(/^www[.]/,"").replace(/[/].*$/,"")}}
function render(){{
  const q=state.q.trim().toLowerCase();
  const rows=DATA.filter(r=>{{
    if(state.expo&&r.expo!==state.expo)return false;
    if(state.prio.size){{let ok=false;state.prio.forEach(p=>{{if(p==="top"?r.top:r.prio===p)ok=true;}});if(!ok)return false;}}
    if(state.tags.size){{let ok=false;state.tags.forEach(t=>{{if(r.tags.includes(t))ok=true;}});if(!ok)return false;}}
    if(q){{const h=(r.name+" "+r.city+" "+r.site+" "+r.descr+" "+r.rubrics.join(" ")+" "+r.stand).toLowerCase();if(!h.includes(q))return false;}}
    return true;}});
  document.getElementById("cnt").textContent=rows.length+" из "+DATA.length;
  const L=document.getElementById("list");
  if(!rows.length){{L.innerHTML='<div class="empty">Ничего не найдено — снимите фильтры.</div>';return;}}
  L.innerHTML=rows.map(r=>`<div class="it ${{r.prio}}">
    <div class="st">${{esc(r.stand)}}<small>${{r.expo==="md"?"Мир детства":"CJF"}} · зал ${{r.hall}}</small></div>
    <div><div class="nm"><span class="pr ${{r.prio}}">${{r.prio}}</span>${{r.top?'<span class="star">★</span>':''}}${{esc(r.name)}}</div>
      <div class="meta">${{esc([r.country!=="Россия"?r.country:"",r.city].filter(Boolean).join(", "))}}${{r.site?` · <a href="${{esc(r.site.startsWith("http")?r.site:"http://"+r.site)}}" target="_blank" rel="noopener">${{esc(host(r.site))}}</a>`:" · сайта нет"}}</div>
      <div class="tg">${{r.tags.map(t=>`<span>${{esc(t)}}</span>`).join("")}}</div>
      ${{r.descr?`<div class="ds">${{esc(r.descr)}}</div>`:""}}
      ${{r.rubrics.length?`<div class="rb">Рубрики: ${{esc(r.rubrics.join(" · "))}}</div>`:""}}
    </div></div>`).join("");
}}
document.addEventListener("click",e=>{{
  const b=e.target.closest(".chip");
  if(b){{const f=b.dataset.f,v=b.dataset.v;
    if(f==="expo"){{state.expo=v;document.querySelectorAll('.chip[data-f="expo"]').forEach(x=>x.classList.toggle("on",x.dataset.v===v));}}
    else{{const set=f==="prio"?state.prio:state.tags; set.has(v)?set.delete(v):set.add(v); b.classList.toggle("on");}}
    render();return;}}
  const it=e.target.closest(".it"); if(it&&e.target.closest(".ds,.rb")) it.classList.toggle("open");
}});
document.getElementById("q").addEventListener("input",e=>{{state.q=e.target.value;render();}});
render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    rows = load()
    OUT.mkdir(exist_ok=True)
    pub = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    (OUT / "exhibitors.json").write_text(json.dumps(pub, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "exhibitors.html").write_text(page(rows), encoding="utf-8")
    if "--full" in sys.argv:
        p = pathlib.Path(sys.argv[sys.argv.index("--full") + 1])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print("full →", p)
    from collections import Counter
    print("OK mirdetstva/exhibitors.html:", len(rows), "rows; prio", dict(Counter(r["prio"] for r in rows)), "; top", sum(r["top"] for r in rows))
