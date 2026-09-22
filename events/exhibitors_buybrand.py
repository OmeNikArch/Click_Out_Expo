#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Участники «BUYBRAND Expo 2026» (Тимирязев Центр) по эшелонам A/B/C под Click Out.
Вход: events/raw_icatalog/buybrand_rows.json (buybrandexpo.com/exhibitors — карточки: специализация, стенд, точки, инвестиции, сайт, описание;
сайт публикует только подтверждённых участников, пагинации нет — union по фильтрам FILTER_TYPE/FILTER_INVEST).
Запуск из корня: python3 events/exhibitors_buybrand.py [--xlsx /путь.xlsx]"""
import json, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from exhibitors_page import emit, ROOT

RAW = ROOT / "events" / "raw_icatalog" / "buybrand_rows.json"
NICHE = [("общепит / доставка", r"пицц|суши|кофе|кафе|ресторан|бургер|стритфуд|общепит|пекарн|шаурм|бар\b|фастфуд|еда|кухн"),
         ("медицина / стоматология", r"стоматолог|клиник|медицин|анализ|лаборатор|аптек"),
         ("красота / здоровье", r"салон|красот|барбершоп|маникюр|косметолог|массаж|spa|эпиляц"),
         ("дети / образование", r"детск|школ|курс|образован|детей|садик|сад\b|обучени|IT-школ"),
         ("авто", r"авто|шиномонтаж|мойк|сто\b|автосервис"),
         ("фитнес / досуг", r"фитнес|спорт|клуб|квест|игров|развлеч|студи"),
         ("ритейл", r"магазин|ритейл|розниц|сеть магазинов|дрогери|маркет"),
         ("финтех / IT", r"финанс|платеж|оплат|сервис|IT|цифров|платформ|приложени|маркетинг"),
         ("недвижимость / услуги", r"недвижим|агентств|клининг|уборк|прачечн|химчист|ремонт|логистик|доставк")]
CONSUMER_SPEC = {"Общественное питание", "Розничные сети", "Услуги", "Гостиничный сегмент"}
C_SPEC = {"СМИ", "Национальные франчайзинговые ассоциации", "Государственные организации"}
FORCE_C = ["businessmens", "franchising.ru", "topfranchise", "портал"]

def num(s):
    m = re.search(r"\d+", (s or "").replace(" ", "")); return int(m.group(0)) if m else 0

def invest_rank(s):
    return {"отсутствуют": 0, "1 млн – 7 млн": 1, "7 млн – 15 млн": 2, "15 млн – 40 млн": 3, "Свыше 40 млн": 4}.get(s, 0)

def load():
    out = []
    for r in json.load(open(RAW, encoding="utf-8")):
        d = r["descr"]; text = (r["name"] + " " + d).lower()
        tags = [r["spec"]] if r["spec"] else []
        for label, rx in NICHE:
            if re.search(rx, text, re.I): tags.append(label)
        pts = num(r["corp"]) + num(r["fr"]); ir = invest_rank(r["invest"])
        if pts >= 50: tags.append("федеральная сеть 50+ точек")
        elif pts >= 10: tags.append("сеть 10–49 точек")
        elif pts: tags.append("молодая сеть до 10 точек")
        n = r["name"].lower()
        if r["spec"] in C_SPEC or not r["site"] or any(k in n for k in FORCE_C): p = "C"
        elif r["spec"] in CONSUMER_SPEC and (pts >= 10 or ir >= 2): p = "A"
        else: p = "B"
        top = p == "A" and (pts >= 100 or ir >= 3 or any(t in tags for t in ("общепит / доставка", "медицина / стоматология", "красота / здоровье", "авто")) and pts >= 40)
        meta = " · ".join(x for x in [f"точек: {r['corp'] or '0'} свои / {r['fr'] or '0'} франчайзи" if pts else "", f"инвестиции {r['invest']}" if r["invest"] and r["invest"] != "отсутствуют" else ""] if x)
        out.append({"hall": r["spec"] or "Другое", "stand": r["stand"], "name": r["name"], "country": "Россия", "city": "", "site": r["site"], "profile": r["labels"],
                    "descr": d[:600], "products": [], "hl": [t for t in tags if t.startswith(("федеральная", "сеть 10"))], "brands": [],
                    "tags": [t for t in tags if not t.startswith(("федеральная", "сеть 10"))], "prio": p, "top": top, "meta": meta, "_phones": [], "_emails": []})
    order = {"A": 0, "B": 1, "C": 2}
    out.sort(key=lambda x: (order[x["prio"]], not x["top"], x["hall"], x["name"]))
    return out

CFG = {
    "title": "BUYBRAND Expo 2026 · участники по эшелонам A/B/C для Click Out",
    "kicker": "Click Out · BUYBRAND Expo · 29.09–01.10.2026 · Тимирязев Центр, Верхняя аллея 6с1",
    "h1": "{n} опубликованных участников по эшелонам A, B, C",
    "sub": "Организатор заявляет 164 участника, на сайте buybrandexpo.com опубликованы карточки {n} компаний (снято 22.09.2026): специализация, стенд, число точек, "
           "инвестиции, сайт. Разметка: <b>A — {a}</b> (из них ★ {top}), <b>B — {b}</b>, C — {c}. Список пополняется, перед выставкой снять ещё раз.",
    "legend": [("A", "франчайзеры в потребительских нишах (общепит, ритейл, услуги) с сайтом и сетью от 10 точек или инвестициями от 7 млн ₽: две задачи — заявки на франшизу (сегмент «Клиент B2B», Авито «Готовый бизнес») и клиенты в точки (Click Out с гео по городам сети)."),
               ("B", "молодые сети до 10 точек, поставщики B2B-услуг, производственный франчайзинг, инвестпроекты. Разговор про B2B-заявки: «Клиент B2B», Директ, VK."),
               ("C", "СМИ, порталы о франшизах, ассоциации, госорганизации, компании без сайта."),
               ("★", "первыми: сети от 100 точек, инвестиции от 15 млн ₽, а также общепит, медицина, красота и авто от 40 точек — ниши, где у Click Out есть кейсы.")],
    "placeholder": "Поиск: бренд, специализация, стенд, слово из описания", "filter1_label": "Специализация",
    "filter1": [("Общественное питание", "общепит"), ("Розничные сети", "ритейл"), ("Услуги", "услуги"), ("Поставщик B2B услуг", "B2B-услуги"), ("Производственный франчайзинг", "производство"), ("Другое", "другое")],
    "hall_label": "", "hl_label": "Масштаб сети",
}
if __name__ == "__main__":
    emit(CFG, load(), ROOT / "buybrand", sys.argv)
    for r in load():
        if r["prio"] in ("A", "B"): print(f'{r["prio"]}{"★" if r["top"] else " "} {r["stand"]:6} | {r["name"][:34]:34} | {r["hall"][:22]:22} | {r["meta"][:48]:48} | {", ".join(t for t in r["tags"] if t != r["hall"])}')
