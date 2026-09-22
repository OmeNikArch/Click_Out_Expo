#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Участники «ПаркЗоо 2026» (Крокус, залы 3–4) по эшелонам A/B/C под Click Out.
Вход: events/raw_icatalog/parkzoo_rows.json (каталог lk.parkzoo.ru, платформа ЭКСПОДАТ; краулер events/parkzoo_crawl.py + events/parkzoo_parse.py).
Запуск из корня: python3 events/exhibitors_parkzoo.py [--xlsx /путь.xlsx]"""
import json, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from exhibitors_page import emit, ROOT

RAW = ROOT / "events" / "raw_icatalog" / "parkzoo_rows.json"
RETAIL = re.compile(r"интернет-магазин|онлайн-магазин|маркетплейс|ozon|wildberries|озон|вайлдберриз|сеть (магазинов|зоомагазинов)|розничн\w+ (сеть|магазин|продаж)|фирменн\w+ магазин", re.I)
VET = re.compile(r"ветеринарн\w+ (клиник|центр|госпитал)|ветклиник", re.I)
NKO = re.compile(r"приют|благотворит|фонд помощи", re.I)
GROOM = re.compile(r"груминг|зоосалон", re.I)
BRAND = re.compile(r"собственн\w+ (бренд|торгов\w+ марк|марк)|под брендом|бренд\w* компании|наш бренд|торгов\w+ марк\w+ [«\"]|ТМ [«\"]", re.I)
CHINA_IMPORT = re.compile(r"импорт\w* (товар\w* )?из кита|китайск\w+ (фабрик|производит)|прямые поставки из кита", re.I)
FORCE_A, FORCE_B, FORCE_C = [], [], ["новинки", "эксподат", "зона новинок"]

def tag(r):
    prof = set(r["profile"]); d = r["descr"]; tags = []
    if r["country"] != "Россия": tags.append("иностр.")
    if prof & {"СМИ", "Выставка"} and not (prof & {"Производитель", "Оптовая торговля", "Дистрибьютор"}): tags.append("СМИ / выставка")
    maker = "Производитель" in prof
    trade_only = bool(prof & {"Оптовая торговля", "Дистрибьютор", "Импортер", "Импорт товаров из Китая"}) and not maker
    if maker: tags.append("производитель / бренд")
    if prof & {"Оптовая торговля", "Дистрибьютор"}: tags.append("опт / дистрибуция")
    if prof & {"Импортер", "Импорт товаров из Китая"} or CHINA_IMPORT.search(d): tags.append("импорт")
    if "Интернет-магазин" in prof or RETAIL.search(d): tags.append("своя розница / e-com")
    if "Зоомагазин" in prof: tags.append("зоомагазин")
    if "Ветеринарная клиника" in prof or "Дистанционные ветеринарные консультации" in prof or VET.search(d): tags.append("ветеринария")
    if "Зоосалон" in prof or GROOM.search(d): tags.append("груминг")
    if re.search(r"ассоциац|союз ", r["name"], re.I): tags.append("ассоциация")
    elif "НКО" in prof or NKO.search(d): tags.append("НКО / приют")
    if "Разработчик" in prof or "Логистические услуги и таможенное сопровождение" in prof: tags.append("сервис для бизнеса")
    ps = set(r["products"])
    if ps & {"Товары для кошек", "Товары для собак"}: tags.append("кошки и собаки")
    if ps & {"Товары для грызунов", "Товары для птиц", "Товары для мелких животных", "Аквариумистика", "Террариумистика", "Товары для экзотических животных"}: tags.append("мелкие, птицы, аквариум")
    if "Ветеринария" in ps: tags.append("ветпрепараты")
    if "Оборудование для производства кормов" in ps: tags.append("оборудование для производств")
    return tags or ["прочее"], maker, trade_only

def prio(r, tags, maker, trade_only):
    n = r["name"].lower()
    if any(k in n for k in FORCE_C) or "иностр." in tags or "СМИ / выставка" in tags or not r["site"]: return "C"
    if any(k in n for k in FORCE_A): return "A"
    if any(k in n for k in FORCE_B): return "B"
    if "ассоциация" in tags or "сервис для бизнеса" in tags and "своя розница / e-com" not in tags: return "B"
    if {"своя розница / e-com", "зоомагазин", "НКО / приют"} & set(tags): return "A"
    if "ветеринария" in tags and (set(r["profile"]) & {"Ветеринарная клиника", "Дистанционные ветеринарные консультации"} or VET.search(r["descr"])): return "A"
    if "груминг" in tags and "Зоосалон" in r["profile"]: return "A"
    if maker and "импорт" not in tags and BRAND.search(r["descr"]): return "A"
    return "B"

def load():
    out = []
    for r in json.load(open(RAW, encoding="utf-8")):
        tags, maker, trade_only = tag(r); p = prio(r, tags, maker, trade_only)
        d = r["descr"]
        top = p == "A" and ((bool(RETAIL.search(d)) or "Интернет-магазин" in r["profile"]) and maker or "ветеринария" in tags or "НКО / приют" in tags)
        hl = [t for t in ("своя розница / e-com", "ветеринария", "НКО / приют") if t in tags]
        out.append({"hall": r["hall"], "stand": r["stand"].replace(" / зал 3", "").replace(" / зал 4", ""), "name": r["name"], "country": r["country"], "city": r["city"],
                    "site": r["site"], "profile": [x for x in r["profile"] if x not in ("Сервис от партнеров (Эксподат)",)], "descr": d[:600],
                    "products": [x for x in r["products"] if not x.startswith(("Внимание", "У вас есть", "Сервис от", "Телеграм"))], "hl": hl, "brands": [],
                    "tags": [t for t in tags if t not in hl] + (["производитель без прямых продаж"] if p == "B" and maker and "импорт" not in tags else []), "prio": p, "top": top, "meta": "", "_phones": r["_phones"], "_emails": r["_emails"]})
    order = {"A": 0, "B": 1, "C": 2}
    out.sort(key=lambda x: (order[x["prio"]], not x["top"], x["hall"], x["stand"]))
    return out

CFG = {
    "title": "ПаркЗоо 2026 · участники по эшелонам A/B/C для Click Out",
    "kicker": "Click Out · ПаркЗоо · 23–25.09.2026 · Крокус Экспо, павильон 1, залы 3 и 4",
    "h1": "{n} участников по эшелонам A, B, C",
    "sub": "193 российских компании, 81 из Китая, ещё семь из Германии, Италии, Японии, Беларуси и Словении. Источник — электронный каталог выставки lk.parkzoo.ru, снят 22.09.2026. "
           "Разметка по виду деятельности, группам товаров и описаниям: <b>A — {a}</b> (из них ★ {top}), <b>B — {b}</b>, C — {c}. Нажмите на описание, чтобы раскрыть группы товаров.",
    "legend": [("A", "прямой формат Click Out: российский производитель со своим брендом и сайтом, розница и интернет-магазины, ветклиники, груминг, приюты и фонды (модель «Дай лапу»). Разговор про Click Out на сайт бренда и внешний трафик на карточки WB и Ozon."),
               ("B", "производители без прямых продаж (разговор про внешний трафик на карточки и B2B), оптовики, дистрибьюторы, импортёры, ассоциации, сервисы для зообизнеса. Разговор про B2B: сегмент «Клиент B2B», Директ, посадочная для дилерских заявок."),
               ("C", "китайские и другие иностранные фабрики, СМИ, зона новинок, компании без сайта. К стендам не подходим."),
               ("★", "первыми: бренды, которые уже продают напрямую (интернет-магазин, маркетплейсы, своя розница), ветклиники и фонды.")],
    "placeholder": "Поиск: компания, город, сайт, группа товаров, слово из описания", "filter1_label": "Зал", "filter1": [("3", "зал 3"), ("4", "зал 4")], "hall_label": "зал", "hl_label": "Сигналы",
}
if __name__ == "__main__":
    emit(CFG, load(), ROOT / "parkzoo", sys.argv)
    for r in load():
        if r["prio"] == "A": print(f'{"★" if r["top"] else " "} {r["hall"]}·{r["stand"]:14} | {r["name"][:38]:38} | {r["city"][:14]:14} | {r["site"][:30]:30} | {", ".join(r["hl"] + [t for t in r["tags"] if t not in ("кошки и собаки",)])}')
