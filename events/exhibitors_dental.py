#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Участники «Дентал-Экспо 2026» (Крокус, павильон 2, залы 5/7/8) с разметкой под Click Out.
Вход: events/raw_icatalog/dental_rows.json — результат events/dental_crawl.py + парсера
(каталог expo.dental-expo.com, платформа ЭКСПОДАТ: страна, стенд, описание, виды продукции, профиль, сайт, контакты).
Выход: dental-expo/exhibitors.json и dental-expo/exhibitors.html (без контактов — страница публичная);
--xlsx <путь> — Excel с листами A / B / C и контактами (в ИСХОДЯЩИЕ, не в репозиторий).
Запуск из корня: python3 events/exhibitors_dental.py [--xlsx /путь/файл.xlsx]
"""
import json, re, sys, pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).parent.parent
RAW = ROOT / "events" / "raw_icatalog" / "dental_rows.json"
OUT = ROOT / "dental-expo"

B2C = re.compile(r"зубн\w* паст|зубн\w* щ[её]тк|ирригатор|ополаскиват|уход\w* за зубами|отбелив\w* .*домаш|зубн\w* нит|ёршик|ершик|жеват|для детей|гигиен\w* полости", re.I)
CLINIC = re.compile(r"стоматологическ\w+ (клиник|центр)|сеть (клиник|стоматолог)|клиника|приём пациентов|лечение пациентов|имплантац\w+ под ключ", re.I)
LAB = re.compile(r"зуботехническ\w+ лаборатор|лаборатория", re.I)
SOFT = re.compile(r"программн|CRM|МИС|софт|IT-|цифров\w+ платформ|приложение", re.I)
EDU = re.compile(r"обучени|учебн\w+ центр|курс|семинар|академи|школа", re.I)
ECOM = re.compile(r"интернет-магазин|онлайн-магазин|розничн\w+ продаж|фирменн\w+ магазин", re.I)

CONSUMER = re.compile(r"маркетплейс|ozon|wildberries|озон|вайлдберриз|аптек|розниц|для потребител|потребительск|для дома|домашн\w+ (уход|использован)|бренд|торгов\w+ марк|собственн\w+ марк", re.I)
CLINIC_STRICT = re.compile(r"наш\w+ клиник|сеть клиник|сеть стоматологи|стоматологическ\w+ клиник\w* [«\"]|многопрофильн\w+ клиник", re.I)

def tags_of(r):
    prof = set(r["profile"])
    tags = []
    if r["country"] != "Россия":
        tags.append("иностр.")
    if "Пресса" in prof: tags.append("пресса")
    if "Общественная организация" in prof: tags.append("ассоциация")
    b2c_products = [p for p in r["products"] if B2C.search(p)]
    soft = bool(SOFT.search(r["descr"])) and not b2c_products
    maker = "Производитель" in prof
    dealer_like = "Дистрибьютор" in prof and len(r["products"]) >= 10
    consumer = bool(CONSUMER.search(r["descr"]))
    if soft: tags.append("софт для клиник")
    if CLINIC_STRICT.search(r["descr"]) and not maker and not dealer_like and not soft: tags.append("клиника / сеть")
    if b2c_products or B2C.search(r["descr"]):
        if (maker or consumer) and not dealer_like: tags.append("B2C: бренд для пациентов")
        else: tags.append("дилер с B2C-линейкой")
    if maker: tags.append("производитель")
    if "Дистрибьютор" in prof: tags.append("дистрибьютор / дилер")
    if dealer_like: tags.append("широкий каталог")
    if "Обучение" in prof or (EDU.search(r["descr"]) and not maker): tags.append("обучение врачей")
    if LAB.search(r["descr"]) or any("з/т лаб" in p for p in r["products"]): tags.append("лаборатория / CAD-CAM")
    if ECOM.search(r["descr"]): tags.append("свой интернет-магазин")
    return tags or ["прочее"], b2c_products

def priority(r, tags):
    if "иностр." in tags or "пресса" in tags or "ассоциация" in tags: return "C"
    if not r["site"]: return "C"
    if "B2C: бренд для пациентов" in tags or "клиника / сеть" in tags: return "A"
    return "B"

def star(r, tags, pr):
    b2c_n = len([p for p in r["products"] if B2C.search(p)])
    if pr == "A":
        return b2c_n >= 3 or "клиника / сеть" in tags or bool(re.search(r"маркетплейс|ozon|wildberries|озон|аптек", r["descr"], re.I))
    if pr == "B":
        return "дилер с B2C-линейкой" in tags and "свой интернет-магазин" in tags
    return False

def load():
    rows = json.load(open(RAW, encoding="utf-8"))
    out = []
    for r in rows:
        tags, b2c = tags_of(r)
        pr = priority(r, tags)
        out.append({"hall": r["hall"], "stand": r["stand"].replace("Зал ", "").replace(", ", " · "), "name": r["name"], "country": r["country"],
                    "city": r["city"], "site": r["site"], "profile": [p for p in r["profile"] if p in ("Производитель", "Дистрибьютор", "Обучение", "Пресса", "Общественная организация")],
                    "descr": r["descr"][:600], "products": r["products"], "b2c": b2c, "brands": r["brands"][:12], "tags": tags, "prio": pr,
                    "top": star(r, tags, pr), "_emails": r["_emails"], "_phones": r["_phones"]})
    order = {"A": 0, "B": 1, "C": 2}
    out.sort(key=lambda x: (order[x["prio"]], not x["top"], x["hall"], x["stand"]))
    return out

CSS = (ROOT / "events" / "exhibitors_build.py").read_text(encoding="utf-8").split('CSS = """')[1].split('"""')[0]

def page(rows):
    pub = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    c = Counter(r["prio"] for r in rows); nTop = sum(r["top"] for r in rows)
    ru = sum(1 for r in rows if r["country"] == "Россия")
    data = json.dumps(pub, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Дентал-Экспо 2026 · участники по эшелонам A/B/C для Click Out</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="kicker"><div class="bar"></div><span>Click Out · Дентал-Экспо · 21–24.09.2026 · Крокус Экспо, павильон 2, залы 5, 7, 8</span></div>
  <h1>{len(rows)} участников по эшелонам A, B, C</h1>
  <p class="sub">{ru} российских компаний, {len(rows) - ru} иностранных (75 из Китая, 12 из Кореи). Источник — онлайн-каталог выставки expo.dental-expo.com, снят 22.09.2026.
  Разметка по описаниям, видам продукции и профилю: <b>A — {c['A']}</b> (из них ★ {nTop}), <b>B — {c['B']}</b>, C — {c['C']}. Нажмите на описание, чтобы раскрыть виды продукции.
  Презентация: <a href="presenter.html">версия ведущего</a> · <a href="index.html">клиентская</a> · <a href="../events.html">все выставки</a>.</p>
  <div class="legend">
    <div class="lg"><b>A</b> — прямой формат Click Out: российский производитель или владелец бренда с сайтом и линейкой для пациентов (пасты, щётки, ирригаторы, уход) либо клиника / сеть клиник. Разговор про баннер на Ozon, WB и в Яндексе с переходом на сайт бренда или клиники.</div>
    <div class="lg"><b>B</b> — российские производители и дилеры оборудования и материалов, дилеры с B2C-линейкой в широком каталоге, софт для клиник, обучение врачей. Продают клиникам: разговор про B2B — сегмент «Клиент B2B» на Ozon, Директ, Авито, посадочная для дилерских заявок.</div>
    <div class="lg"><b>C</b> — иностранные фабрики без российского юрлица в каталоге, пресса, ассоциации, компании без сайта. К стендам не подходим.</div>
    <div class="lg"><b>★</b> — первыми: сильная B2C-линейка (3+ вида продукции для пациентов), сети клиник, производители со своим интернет-магазином.</div>
  </div>
  <div class="panel">
    <div class="row"><input class="q" id="q" placeholder="Поиск: компания, бренд, город, сайт, вид продукции"><span class="cnt" id="cnt"></span></div>
    <div class="row"><span class="lbl">Зал</span>
      <button class="chip on" data-f="expo" data-v="">все</button><button class="chip" data-f="expo" data-v="5">зал 5</button><button class="chip" data-f="expo" data-v="7">зал 7</button><button class="chip" data-f="expo" data-v="8">зал 8</button></div>
    <div class="row"><span class="lbl">Эшелон</span>
      <button class="chip" data-f="prio" data-v="top">★ первыми</button><button class="chip on" data-f="prio" data-v="A">A</button><button class="chip" data-f="prio" data-v="B">B</button><button class="chip" data-f="prio" data-v="C">C</button></div>
    <div class="row" id="tags"><span class="lbl">Сегмент</span></div>
  </div>
  <div class="list" id="list"></div>
</div>
<script>
const DATA={data};
const state={{expo:(new URLSearchParams(location.search).get("hall")||""),prio:new Set([(new URLSearchParams(location.search).get("prio")||"A")]),tags:new Set(),q:""}};
document.querySelectorAll('.chip[data-f="expo"]').forEach(x=>x.classList.toggle("on",x.dataset.v===state.expo));
document.querySelectorAll('.chip[data-f="prio"]').forEach(x=>x.classList.toggle("on",state.prio.has(x.dataset.v)));
const TAGS=[...new Set(DATA.flatMap(r=>r.tags))].filter(t=>t!=="иностр.").sort();
const tagsRow=document.getElementById("tags");
TAGS.forEach(t=>{{const b=document.createElement("button");b.className="chip";b.dataset.f="tag";b.dataset.v=t;b.textContent=t;tagsRow.appendChild(b);}});
function esc(s){{return (s||"").replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));}}
function host(u){{return u.replace(/^https?:[/][/]/,"").replace(/^www[.]/,"").replace(/[/].*$/,"")}}
function render(){{
  const q=state.q.trim().toLowerCase();
  const rows=DATA.filter(r=>{{
    if(state.expo&&r.hall!==state.expo)return false;
    if(state.prio.size){{let ok=false;state.prio.forEach(p=>{{if(p==="top"?r.top:r.prio===p)ok=true;}});if(!ok)return false;}}
    if(state.tags.size){{let ok=false;state.tags.forEach(t=>{{if(r.tags.includes(t))ok=true;}});if(!ok)return false;}}
    if(q){{const h=(r.name+" "+r.city+" "+r.site+" "+r.descr+" "+r.products.join(" ")+" "+r.brands.join(" ")+" "+r.stand).toLowerCase();if(!h.includes(q))return false;}}
    return true;}});
  document.getElementById("cnt").textContent=rows.length+" из "+DATA.length;
  const L=document.getElementById("list");
  if(!rows.length){{L.innerHTML='<div class="empty">Ничего не найдено — снимите фильтры.</div>';return;}}
  L.innerHTML=rows.map(r=>`<div class="it ${{r.prio}}">
    <div class="st">${{esc(r.stand)}}<small>зал ${{r.hall}}</small></div>
    <div><div class="nm"><span class="pr ${{r.prio}}">${{r.prio}}</span>${{r.top?'<span class="star">★</span>':''}}${{esc(r.name)}}</div>
      <div class="meta">${{esc([r.country!=="Россия"?r.country:"",r.city,r.profile.join(", ")].filter(Boolean).join(" · "))}}${{r.site?` · <a href="${{esc(r.site.startsWith("http")?r.site:"http://"+r.site)}}" target="_blank" rel="noopener">${{esc(host(r.site))}}</a>`:" · сайта нет"}}</div>
      <div class="tg">${{r.tags.map(t=>`<span>${{esc(t)}}</span>`).join("")}}${{r.b2c.length?`<span style="border-color:var(--y);color:var(--y)">B2C: ${{esc(r.b2c.slice(0,4).join(", "))}}</span>`:""}}</div>
      ${{r.descr?`<div class="ds">${{esc(r.descr)}}</div>`:""}}
      ${{r.products.length||r.brands.length?`<div class="rb">${{r.brands.length?"Бренды: "+esc(r.brands.join(", "))+". ":""}}${{r.products.length?"Виды продукции: "+esc(r.products.join(" · ")):""}}</div>`:""}}
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

def xlsx(rows, path):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook(); wb.remove(wb.active)
    cols = ["Эшелон", "★", "Зал", "Стенд", "Компания", "Страна", "Город", "Сайт", "Профиль", "Сегменты", "B2C-продукция", "Бренды", "Описание", "Телефоны", "E-mail"]
    def sheet(title, rs):
        ws = wb.create_sheet(title); ws.append(cols)
        for c in ws[1]: c.font = Font(bold=True, color="000000"); c.fill = PatternFill("solid", fgColor="FDD101")
        for r in rs:
            ws.append([r["prio"], "★" if r["top"] else "", r["hall"], r["stand"], r["name"], r["country"], r["city"], r["site"], ", ".join(r["profile"]),
                       ", ".join(r["tags"]), ", ".join(r["b2c"]), ", ".join(r["brands"]), r["descr"][:400], "; ".join(r["_phones"][:3]), "; ".join(r["_emails"][:3])])
        for col, w in zip("ABCDEFGHIJKLMNO", (7, 4, 5, 12, 34, 10, 14, 26, 18, 30, 30, 24, 60, 24, 28)): ws.column_dimensions[col].width = w
        for row in ws.iter_rows(min_row=2):
            for c in row: c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
    sheet("A — Click Out", [r for r in rows if r["prio"] == "A"])
    sheet("B — B2B", [r for r in rows if r["prio"] == "B"])
    sheet("C — не наши", [r for r in rows if r["prio"] == "C"])
    sheet("Все", rows)
    wb.save(path)

if __name__ == "__main__":
    rows = load()
    OUT.mkdir(exist_ok=True)
    pub = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    (OUT / "exhibitors.json").write_text(json.dumps(pub, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "exhibitors.html").write_text(page(rows), encoding="utf-8")
    if "--xlsx" in sys.argv:
        p = pathlib.Path(sys.argv[sys.argv.index("--xlsx") + 1]); p.parent.mkdir(parents=True, exist_ok=True); xlsx(rows, p); print("xlsx →", p)
    print("OK dental-expo/exhibitors.html:", len(rows), dict(Counter(r["prio"] for r in rows)), "top", sum(r["top"] for r in rows))
    print("tags:", Counter(t for r in rows for t in r["tags"]).most_common())
    for r in rows:
        if r["prio"] == "A":
            print(f'{"★" if r["top"] else " "} {r["stand"]:12} | {r["name"][:40]:40} | {r["city"][:14]:14} | {r["site"][:32]:32} | {", ".join(t for t in r["tags"] if t not in ("производитель","дистрибьютор / дилер"))} | {", ".join(r["b2c"][:3])}')
