#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Участники InterCHARM 2026 по эшелонам A/B/C под Click Out.

Источник: официальный API каталога expovr, событие 69d8e35163aa2ec91670244b.
Запуск из корня репозитория: python3 events/exhibitors_intercharm.py [--xlsx путь.xlsx]
"""
import json, pathlib, re, sys, unicodedata
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from exhibitors_page import emit, ROOT

RAW = ROOT / "events" / "raw_icatalog" / "intercharm_expovr_rows.json"

COUNTRIES = {
    "RUS": "Россия", "BLR": "Беларусь", "CHN": "Китай", "KOR": "Южная Корея",
    "TUR": "Турция", "ITA": "Италия", "FRA": "Франция", "GBR": "Великобритания",
    "USA": "США", "DEU": "Германия", "ESP": "Испания", "IND": "Индия", "JPN": "Япония",
    "KAZ": "Казахстан", "UZB": "Узбекистан", "ARE": "ОАЭ", "BGR": "Болгария",
    "BRA": "Бразилия", "HKG": "Гонконг", "IDN": "Индонезия", "IRN": "Иран",
    "JOR": "Иордания", "KWT": "Кувейт", "PRK": "КНДР", "QAT": "Катар", "ROU": "Румыния",
    "SAU": "Саудовская Аравия", "SRB": "Сербия", "SYR": "Сирия", "THA": "Таиланд",
    "TWN": "Тайвань",
}

# Назначение под Click Out:
# A — потребительские бренды/производители с сайтом и явной розницей / D2C;
# B — B2B-поставщики, контрактное производство, сырьё, оборудование, салоны/услуги;
# C — пресса, ассоциации, обучение, маркетинг, логистика, упаковка, компании без сайта.
A_CATEGORIES = {
    "Уход за кожей лица и тела",
    "Косметика anti-age",
    "Лечебная косметика и космецевтика",
    "Космецевтика",
    "Натуральная и органическая косметика",
    "Декоративная косметика и кисти",
    "Детская косметика",
    "Мужская косметика",
    "Солнцезащитная косметика; автозагар",
    "Экспресс-уход (маски; патчи)",
    "Домашний уход за волосами",
    "Парфюмерия женская",
    "Парфюмерия мужская",
    "Нишевая парфюмерия",
    "Парфюмерия для детей",
    "Ароматерапия (масла; аксессуары)",
    "Ароматы для помещений (свечи; диффузоры)",
    "БАДы и нутрициология",
    "Диетическое питание; суперфуды",
    "Бытовая химия и хозяйственные товары",
    "Стиральные порошки и гели",
    "Чистящие и моющие средства",
    "Авто-косметика",
    "Косметика для животных",
    "Средства личной гигиены и гигиена полости рта",
    "Бьюти-гаджеты для домашнего использования",
    "Фены; плойки и другая техника",
    "Фитнес-товары",
    "Продукция для массажа",
    "Одноразовая продукция (перчатки; пеленки; салфетки)",
    "Кейсы; сумки; косметички",
}

B_CATEGORIES = {
    "Аппаратная косметология",
    "Инъекционная косметология",
    "Лазерная косметология",
    "Пластическая хирургия",
    "Эстетическая стоматология",
    "Депиляция и эпиляция",
    "Наращивание ногтей",
    "Салонный уход за ногтями; руками; ступнями",
    "Наращивание ресниц и бровей",
    "Коррекция и окрашивание бровей",
    "Ламинирование ресниц и бровей",
    "Окрашивание волос",
    "Профессиональная косметика для волос и кожи головы",
    "Профессиональная косметика, межкурсовый уход",
    "Профессиональная декоративная косметика и грим",
    "Стайлинги (гели; лаки; пасты для укладки); долговременная укладка",
    "Волосы для наращивания",
    "Накладные ресницы",
    "Инструменты для ногтевого сервиса; заточка",
    "Инструменты для парикмахеров и барберов (ножницы; зажимы; расчески); заточка",
    "Косметологические инструменты",
    "Кисти; спонжи; пуховки",
    "Дизайн ногтей",
    "Грумминг",
    "Подология",
    "Трихология",
    "Пирсинг, перманентный макияж",
    "Анестетики",
    "Дезинфицирующие средства и оборудование",
    "Продукция для соляриев",
    "Акссесуары для спа; саун; соляриев",
    "Специализированная мебель",
    "Парикмахерское оборудование (сушки; мойки)",
    "Оборудование для маникюра и педикюра (аппараты; лампы)",
    "Производственное оборудование",
    "Контрактное производство",
    "Сырье и ингредиенты для производства",
    "Разработка рецептур",
    "Инновационные технологии (экзосомы, пептиды, биотех)",
    "Лабораторные услуги",
    "Производство упаковки",
    "Производство этикетки",
    "Профессиональная одежда",
    "Франчайзинг",
}

C_CATEGORIES = {
    "Отраслевые организации; пресса",
    "Учебные центры",
    "Маркетинг; реклама; дизайн",
    "Софт и технологии",
    "Цифровые решения (персонализация, AI-подбор)",
    "Транспорт; логистика",
    "Дизайн интерьера",
    "Акции и скидки на стенде",
}

# Ключевые слова, которые повышают приоритет потребительского бренда до A★,
# если в тексте есть признаки розницы, маркетплейсов или собственного магазина.
RETAIL_HINTS = re.compile(
    r"интернет[- ]магазин|официальный магазин|розничн|маркетплейс|ozon|wildberries|wb|яндекс маркет|"
    r"собственн.*магазин|доставк.*по россии|дистрибьютор|сеть магазинов|оптом и в розницу",
    re.I,
)
B2B_HINTS = re.compile(
    r"контрактн|сырь|ингредиент|оборудован|производств|упаковк|этикетк|салон|клиник|обучени|курс|"
    r"дистрибьютор.*профессиональн|для профессионалов|b2b|оптов",
    re.I,
)
SERVICE_HINTS = re.compile(
    r"салон|клиник|услуг|студи|барбершоп|маникюр|косметолог|массаж|эпиляц|лазер|инъекц|стоматолог|подолог|трихолог",
    re.I,
)
MEDIA_HINTS = re.compile(
    r"журнал|издан|ассоциац|союз|портал|сми|премия|оргкомитет|учебн|академ|школ.*професс|маркетинг.*агентств|реклам.*агентств",
    re.I,
)


def txt(d, key="ru"):
    if isinstance(d, dict):
        return (d.get(key) or d.get("en") or "").strip()
    return (d or "").strip()


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ё", "е")
    return re.sub(r"[^a-z0-9а-я]+", " ", s).strip()


def categories(row):
    out = []
    for c in row.get("categories") or []:
        name = txt(c.get("name"))
        typ = c.get("type")
        if name:
            out.append((name, typ))
    return out


def hall(row):
    # Административная категория «Зал NN — …»
    for name, typ in categories(row):
        if typ == "admin" and name.lower().startswith("зал"):
            return name
    stand = row.get("stand") or ""
    m = re.match(r"(\d+)", stand)
    if m:
        return f"Зал {m.group(1)}"
    return "Без зала"


def site(row):
    c = row.get("contacts") or {}
    www = (c.get("www") or c.get("site") or "").strip()
    if not www:
        return ""
    # Убираем markdown-ссылки вида [url](url)
    www = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", www)
    # Разделители: запятая, точка с запятой, вертикальная черта, слэш-пробел, два и более пробела, китайская запятая
    parts = [p.strip() for p in re.split(r"[;,|，]|\s*/\s*|\s{2,}", www) if p.strip()]
    # Дополнительно разрезаем одиночные пробелы между URL-подобными кусками
    parts2 = []
    for p in parts:
        chunks = p.split()
        if len(chunks) > 1 and all(re.match(r"^(https?://|www\.|[a-z0-9-]+\.[a-z]{2,})", c, re.I) for c in chunks):
            parts2.extend(chunks)
        else:
            parts2.append(p)
    urls = []
    for p in parts2:
        p = p.strip().rstrip('/').strip()
        # Нормализуем двойной протокол и пробел после протокола
        p = re.sub(r"^(https?://)\s*", r"\1", p, flags=re.I)
        p = re.sub(r"^(https?://)\s*https?://", r"\1", p, flags=re.I)
        # Принимаем только латинские домены (кириллические названия компаний — мусор)
        if re.match(r"^https?://[a-z0-9.-]+\.[a-z]{2,}", p, re.I) or re.match(r"^www\.[a-z0-9.-]+\.[a-z]{2,}", p, re.I) or re.match(r"^[a-z0-9-]+\.[a-z]{2,}", p, re.I):
            if not p.startswith(("http://", "https://")):
                p = "https://" + p
            urls.append(p)
    if urls:
        return urls[0]
    return ""


def phones(row):
    c = row.get("contacts") or {}
    vals = []
    for k in ("phone", "phones", "tel"):
        v = c.get(k)
        if isinstance(v, list):
            vals.extend(x for x in v if x)
        elif isinstance(v, str) and v:
            vals.extend(re.split(r"[;,]\s*", v))
    out = []
    for v in vals:
        v = v.strip()
        if v and v not in out:
            out.append(v)
    return out


def emails(row):
    c = row.get("contacts") or {}
    vals = []
    for k in ("email", "emails", "mail"):
        v = c.get(k)
        if isinstance(v, list):
            vals.extend(x for x in v if x)
        elif isinstance(v, str) and v:
            vals.extend(re.split(r"[;,]\s*", v))
    out = []
    for v in vals:
        v = v.strip()
        if v and v not in out:
            out.append(v)
    return out


def classify(row, country=""):
    """Возвращает (prio, top, tags, hl, hall)."""
    cats = [name for name, typ in categories(row) if typ == "main"]
    admin = [name for name, typ in categories(row) if typ == "admin"]
    text = " ".join([
        txt(row.get("name")),
        row.get("brand") or "",
        txt(row.get("brief")),
        txt(row.get("about")),
        txt(row.get("descr")),
        " ".join(cats),
    ])
    nt = norm(text)

    tags = []
    hl = []

    # Явные признаки
    has_a = any(c in A_CATEGORIES for c in cats)
    has_b = any(c in B_CATEGORIES for c in cats)
    has_c = any(c in C_CATEGORIES for c in cats)
    has_site = bool(site(row))
    retail = bool(RETAIL_HINTS.search(text)) or bool(RETAIL_HINTS.search(nt))
    b2b = bool(B2B_HINTS.search(text)) or bool(B2B_HINTS.search(nt))
    service = bool(SERVICE_HINTS.search(text))
    media = bool(MEDIA_HINTS.search(text))

    # Флаги выставки
    if any("впервые" in a.lower() for a in admin):
        tags.append("впервые на выставке")
    if any("эколог" in a.lower() for a in admin):
        tags.append("эко-партнёр")

    # Логика приоритета:
    # 1. Если есть потребительские категории и сайт — A, даже если в тексте встречаются
    #    слова «производство», «дистрибьютор», «салон» (бренды часто описывают и производство,
    #    и продажу через салоны).
    # 2. Если только B2B-категории и нет потребительских — B.
    # 3. Если только сервисные категории — B.
    # 4. Если C-категории, медиа или нет сайта — C.
    if has_c or media or not has_site:
        prio = "C"
    elif has_a:
        prio = "A"
        if retail:
            tags.append("розница / D2C")
        else:
            tags.append("потребительский бренд")
    elif has_b:
        prio = "B"
        tags.append("B2B / производство")
    elif service:
        prio = "B"
        tags.append("салоны и услуги")
    else:
        prio = "B"

    # Подсказки по категориям — добавляем, только если тег ещё не проставлен
    tagset = " ".join(tags).lower()
    for c in cats:
        if c in A_CATEGORIES and "потребительский" not in tagset and "розница" not in tagset:
            tags.append("потребительский бренд")
            tagset += " потребительский бренд"
        if c in B_CATEGORIES and "b2b" not in tagset and "производство" not in tagset:
            tags.append("B2B / производство")
            tagset += " b2b / производство"
        if c in C_CATEGORIES and "пресса" not in tagset:
            tags.append(c.lower())
            tagset += " " + c.lower()

    # Уникальные теги
    seen = set()
    tags2 = []
    for t in tags:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            tags2.append(t)
    tags = tags2

    # ★ — идти первыми: только российские потребительские бренды с сайтом,
    # у которых есть признаки розницы/маркетплейсов или масштаба.
    # Иностранные производители (Китай, Корея, Турция) — не приоритет для Click Out:
    # у них нет российского сайта и они не цель для медийки на российских площадках.
    top = False
    if prio == "A" and has_site and country == "Россия":
        if retail:
            top = True
        else:
            # Крупный бренд: ищем признаки масштаба
            scale = re.search(
                r"крупнейш|лидер|30\+|40\+|50\+|собственн.*производств|представлен.*в сет|золот.*яблок|летуаль|рив гош|магнит косметик|ozon|wildberries|яндекс маркет",
                text, re.I)
            if scale:
                top = True

    return prio, top, tags, [], hall(row)


def load():
    rows = json.load(open(RAW, encoding="utf-8"))
    out = []
    for r in rows:
        name = txt(r.get("name")) or txt(r.get("name"), "en")
        if not name:
            continue
        cats = [n for n, t in categories(r) if t == "main"]
        contacts = r.get("contacts") or {}
        country = COUNTRIES.get(contacts.get("country"), contacts.get("country") or "")
        prio, top, tags, hl, h = classify(r, country)
        about = txt(r.get("about")) or txt(r.get("brief"))
        descr = txt(r.get("descr"))
        full = " ".join(x for x in [about, descr] if x)
        city = txt(contacts.get("city"))
        out.append({
            "hall": h,
            "stand": r.get("stand") or "",
            "name": name,
            "country": country,
            "city": city,
            "site": site(r),
            "profile": cats[:3],
            "descr": full[:300],
            "products": [],
            "hl": hl,
            "brands": [b.strip() for b in re.split(r"[;,]", r.get("brand") or "") if b.strip()][:5],
            "tags": tags[:3],
            "prio": prio,
            "top": top,
            "meta": " · ".join(x for x in [country, city] if x),
            "_phones": phones(r),
            "_emails": emails(r),
        })
    order = {"A": 0, "B": 1, "C": 2}
    out.sort(key=lambda x: (order[x["prio"]], not x["top"], x["hall"], x["name"].lower()))
    return out


CFG = {
    "title": "InterCHARM 2026 · участники по эшелонам A/B/C для Click Out",
    "kicker": "Click Out · InterCHARM · 14–17.10.2026 · Крокус Экспо, павильон 3",
    "h1": "{n} участников каталога по эшелонам A, B, C",
    "sub": ("Каталог снят 12.10.2026 из официального API InterCHARM (catalog.expovr.ru): {n} компаний, "
            "стенды, категории, сайты, города. Разметка: <b>A — {a}</b> (из них ★ {top}), <b>B — {b}</b>, C — {c}. "
            "Список пополняется — перед выставкой снять ещё раз."),
    "legend": [
        ("A", "потребительские бьюти-бренды и производители с сайтом: косметика, парфюмерия, уход, гаджеты, бытовая химия. "
              "Click Out на интернет-магазин бренда; если продажи через карточки — внешний трафик на маркетплейсы."),
        ("B", "B2B: сырьё, контрактное производство, оборудование, профессиональная косметика, салоны и услуги, упаковка. "
              "Разговор про B2B-заявки, дистрибуцию и внешний трафик на карточки профессиональных линеек."),
        ("C", "пресса, ассоциации, обучение, маркетинг, логистика, компании без сайта — не наш профиль."),
        ("★", "первыми: потребительские бренды с признаками розницы, маркетплейсов или собственного интернет-магазина."),
    ],
    "placeholder": "Поиск: бренд, стенд, категория, город, слово из описания",
    "filter1_label": "Зал / направление",
    "filter1": [
        ("Зал 13", "зал 13"),
        ("Зал 14", "зал 14"),
        ("Зал 15", "зал 15"),
        ("Зал 16", "зал 16"),
        ("Зал 17", "зал 17"),
        ("Зал 18", "зал 18"),
        ("Уход и косметика", "уход"),
        ("Парфюмерия", "парфюмерия"),
        ("Волосы", "волосы"),
        ("Ногти", "ногти"),
        ("Оборудование и B2B", "оборудование"),
        ("Бытовая химия", "бытовая химия"),
        ("Другое", "другое"),
    ],
    "hall_label": "",
    "hl_label": "Отметки",
}


if __name__ == "__main__":
    emit(CFG, load(), ROOT / "intercharm", sys.argv)
    for r in load():
        if r["prio"] in ("A", "B"):
            star = "★" if r["top"] else " "
            print(f'{r["prio"]}{star} {r["stand"]:8} | {r["name"][:34]:34} | {r["hall"][:18]:18} | '
                  f'{r["site"][:28]:28} | {", ".join(r["tags"][:3])[:44]}')
