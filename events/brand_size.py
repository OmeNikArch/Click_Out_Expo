# -*- coding: utf-8 -*-
"""Крупность бренда для сегмента «Оба» InterCHARM (Никита, 14.10.2026): кто тратит на маркетинг и потянет Click Out.

Без выручки (Rusprofile на сервере нет) — по признакам бюджета на сайте и в каталоге:
коллтрекинг и рекламные пиксели = платный трафик; федеральные сети = оборот; свой магазин/приложение = D2C;
B2B-производство, «впервые на выставке», иностранец без русского сайта — минус.
"""
import re

CALLTRACK = re.compile(r"calltouch|comagic|uiscom|roistat|callibri|mango-office|mango office|alloka|ringostat", re.I)
PIXELS = {
    "VK/MyTarget": r"vk\.com/rtrg|top-fwz1\.mail\.ru|vk-pixel|vkpixel|vk\.ru/rtrg|mytarget",
    "Top.Mail.ru": r"top\.mail\.ru",
    "Google Ads": r"googleadservices|gtag\(['\"]config['\"],\s*['\"]AW-|google_conversion",
    "Facebook": r"connect\.facebook\.net|fbq\(",
    "TikTok": r"analytics\.tiktok\.com",
}
METRIKA = re.compile(r"mc\.yandex\.(ru|com)|metrika", re.I)
GTM = re.compile(r"googletagmanager", re.I)
RETAIL = {
    "Золотое Яблоко": r"золото[ее] яблок|goldapple|gold apple",
    "Летуаль": r"л[’']?этуал|letu\.ru|l[’']?etoile",
    "Рив Гош": r"рив гош|rivegauche",
    "Магнит Косметик": r"магнит косметик|magnit.?cosmetic",
    "Подружка": r"\bподружк",
    "Улыбка радуги": r"улыбка радуги|r-ulybka",
    "Иль де Ботэ": r"иль де бот|iledebeaute",
    "Ашан": r"\bашан\b|auchan\.ru",
    "Лента": r"гипермаркет\w* «?лента|сет[ьи] «?лента|lenta\.com",
    "Перекрёсток/Пятёрочка": r"перекр[её]ст|пят[её]рочк",
    "Магнит": r"сет[ьи] «?магнит|«магнит»|magnit\.ru",
    "Fix Price": r"fix ?price|фикс прайс",
    "Аптеки": r"аптек[аи] 36,6|ригла|горздрав|аптеки «?апрель|eapteka|аптека\.ру|apteka\.ru",
    "Детский мир": r"детский мир|detmir",
}
SOCIAL = re.compile(r"vk\.com/(?!rtrg|share|widget|js)[\w.]+|t\.me/[\w]+|youtube\.com/|rutube\.ru/|dzen\.ru/|instagram\.com/", re.I)


def site_signals(text):
    t = text or ""
    return {
        "calltrack": bool(CALLTRACK.search(t)),
        "pixels": [k for k, p in PIXELS.items() if re.search(p, t, re.I)],
        "metrika": bool(METRIKA.search(t)),
        "gtm": bool(GTM.search(t)),
        "retail": [k for k, p in RETAIL.items() if re.search(p, t, re.I)],
        "social": len(set(m.lower() for m in SOCIAL.findall(t))),
        "ru": len(re.findall(r"[а-яё]", t, re.I)) > 400,
        "size": len(t),
    }


def brand_size(row, sig, opened):
    """→ (балл, [причины]). row — запись участника (tags, country, brands, own_shop, app, mp)."""
    s, why = 0, []
    tags = row.get("tags") or []
    if sig.get("calltrack"):
        s += 3; why.append("коллтрекинг")
    if sig.get("pixels"):
        s += 2 + (len(sig["pixels"]) > 1); why.append("пиксели " + ", ".join(sig["pixels"]))
    if sig.get("metrika") or sig.get("gtm"):
        s += 1; why.append("Метрика/GTM")
    if sig.get("retail"):
        s += min(4, 2 * len(sig["retail"])); why.append("в сетях: " + ", ".join(sig["retail"][:4]))
    if row.get("own_shop"):
        s += 2; why.append("свой магазин")
    if row.get("app"):
        s += 1; why.append("приложение")
    if row.get("mp"):
        s += 1; why.append("продаёт на МП")
    if sig.get("social", 0) >= 2:
        s += 1; why.append("соцсети")
    if len(row.get("brands") or []) >= 2:
        s += 1; why.append(f"брендов {len(row['brands'])}")
    if "B2B / производство" in tags and "потребительский бренд" not in tags and "розница / D2C" not in tags:
        s -= 3; why.append("B2B/производство")
    if "впервые на выставке" in tags:
        s -= 1; why.append("впервые на выставке")
    if "салоны и услуги" in tags:
        s -= 1; why.append("салон/услуги")
    if not opened:
        why.append("сайт не открылся — крупность не проверена")
    elif not sig.get("ru"):
        s -= 2; why.append("сайт не на русском")
    if row.get("country") and row["country"] != "Россия":
        s -= 1; why.append(row["country"])
    return s, why


def tier(score, row=None, opened=True):
    """A — крупный, подходить; B — средний (и непроверенные российские бренды); C — мелкий, пропустить."""
    if not opened and row is not None and row.get("country") in ("Россия", "") and \
            set(row.get("tags") or []) & {"потребительский бренд", "розница / D2C"}:
        return "B"          # сайт не открылся — не выкидываем, уточнить у стенда
    return "A" if score >= 6 else "B" if score >= 3 else "C"
