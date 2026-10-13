#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Участники InterCHARM 2026 по эшелонам A/B/C под Click Out.

Источник: официальный API каталога expovr, событие 69d8e35163aa2ec91670244b.
Запуск из корня репозитория: python3 events/exhibitors_intercharm.py [--xlsx путь.xlsx]
"""
import concurrent.futures, hashlib, html, json, pathlib, re, socket, sys, time, unicodedata
from collections import Counter
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from exhibitors_page import emit, ROOT

RAW = ROOT / "events" / "raw_icatalog" / "intercharm_expovr_rows.json"
CACHE = pathlib.Path("/home/omenik/Programs/Multi-Agent Orchestration Platform/cache/intercharm-sites")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141 Safari/537.36"
FETCH_TIMEOUT = 12
FETCH_WORKERS = 16

MP_DOMAINS = {
    "ozon": ("ozon.ru", "ozon.com"),
    "wb": ("wildberries.ru", "wb.ru"),
    "ym": ("market.yandex.ru", "market.yandex.com", "pokupki.market.yandex.ru"),
    "megamarket": ("megamarket.ru", "sbermegamarket.ru"),
    "lamoda": ("lamoda.ru",),
    "goldapple": ("goldapple.ru",),
}
APP_DOMAINS = ("apps.apple.com", "play.google.com", "rustore.ru", "appgallery.huawei.com")
SHOP_WORDS = re.compile(
    r"в корзин|добавить в корзин|оформить заказ|перейти к оформлению|мой заказ|"
    r"shopping-cart|add[-_ ]?to[-_ ]?cart|data-cart|/cart\b|/basket\b|/checkout\b|"
    r"купить онлайн|интернет[- ]магазин|оплатить заказ|записаться онлайн|онлайн[- ]запись",
    re.I,
)
PRICE_WORDS = re.compile(r"\b\d[\d\s]{2,}\s?(?:₽|руб\.?|р\.)", re.I)
WHERE_WORDS = re.compile(r"где купить|купить на|маркетплейс|wildberries|ozon|яндекс маркет|мегамаркет|lamoda|золотое яблоко|goldapple|интернет[- ]магазин", re.I)
NONE_HINTS = re.compile(
    r"контрактн|сырь|ингредиент|оборудован|упаковк|этикетк|логистик|маркетинг|реклам|пресса|журнал|ассоциац|союз|"
    r"учебн|академ|школ|дистрибьютор|оптов|b2b|oem|odm",
    re.I,
)

# Итоговые правила сегментации (Никита, 13.10.2026):
#   mp       — Андрей: присутствие на маркетплейсах ПОДТВЕРЖДЕНО (сайт ссылается на ozon/wb/ym/
#              megamarket/lamoda/goldapple, кнопки «купить на …», описание каталога о продажах на МП).
#              Свой магазин при этом тоже может быть — всё равно Андрей, без пометки «Никите тоже».
#   clickout — Никита: на МП их НЕТ ЯВНО (услуги: салоны, клиники косметологии, SPA, студии с
#              онлайн-записью; или сайт/описание прямо говорят о продаже только через свой магазин или сеть)
#              И есть свой канал: сайт с заказом или записью, интернет-магазин или приложение.
#   both     — «Оба, уточнить у стенда»: непонятно, есть ли на МП. Потребительские бренды и розница
#              без подтверждённых ссылок на МП, сайты, которые не открылись (если профиль не B2B),
#              иностранные потребительские бренды без признаков продаж в РФ.
#   none     — никому, ТОЛЬКО по профилю: B2B, сырьё, упаковка, оборудование, контрактное
#              производство / OEM / ODM, B2B-дистрибьюторы, пресса, школы и учебные центры.
#              Не по стране: ЕАЭС (Беларусь, Казахстан, Армения, Киргизия) — как Россия;
#              иностранец-потребительский бренд — both, а не none.
#   unknown не используется: всё неясное → both (кроме явного B2B → none).
# Маркетплейсы (WB/Ozon/ЯМ) не проверяем: с сервера и через VPN отдают «Подозрительную активность».
# Источники — только каталог expovr и кэш сайтов cache/intercharm-sites/.

# Явный B2B-профиль по рубрикам каталога — сегмент none.
NONE_CATEGORIES = {
    "Контрактное производство",
    "Сырье и ингредиенты для производства",
    "Разработка рецептур",
    "Лабораторные услуги",
    "Производство упаковки",
    "Производство этикетки",
    "Производственное оборудование",
    "Парикмахерское оборудование (сушки; мойки)",
    "Оборудование для маникюра и педикюра (аппараты; лампы)",
    "Специализированная мебель",
    "Отраслевые организации; пресса",
    "Учебные центры",
    "Маркетинг; реклама; дизайн",
    "Софт и технологии",
    "Цифровые решения (персонализация, AI-подбор)",
    "Транспорт; логистика",
    "Дизайн интерьера",
}

# B2B-товар: магазин на сайте у таких компаний продаёт сырьё, упаковку, оборудование — это не
# потребительский канал, поэтому корзина на сайте не выводит их из none.
B2B_GOODS = {
    "Сырье и ингредиенты для производства",
    "Разработка рецептур",
    "Лабораторные услуги",
    "Производство упаковки",
    "Производство этикетки",
    "Производственное оборудование",
    "Парикмахерское оборудование (сушки; мойки)",
    "Оборудование для маникюра и педикюра (аппараты; лампы)",
    "Специализированная мебель",
}

# Подтверждённые WB/Ozon из таблицы Андрея (проверка 09.10.2026): все — сегмент mp.
ANDREY_MP = {r["id"]: r for r in json.load(open(pathlib.Path(__file__).parent / "intercharm_andrey_mp.json", encoding="utf-8"))["rows"]}

# Явный B2B-профиль по тексту каталога — узкие формулировки, чтобы не задеть потребительские бренды
# («натуральные ингредиенты», «экологичная упаковка», «современное оборудование в салоне» — не B2B).
B2B_TEXT = re.compile(
    r"контрактн\w*(?:ое|ой|ых)?\s+\w*\s*(?:производств|изготовлен|выпуск)|"
    r"\boem\b|\bodm\b|"
    r"сырь\w*\s+(?:и\s+ингредиент|для\s+производств|и\s+комплектующ)|ингредиент\w*\s+(?:и\s+сырь|для\s+производств)|"
    r"производств\w*\s+(?:упаковк|этикеток|тары)|(?:упаковк|этикетк)\w*\s+и\s+(?:упаковк|этикетк|полиграф)|"
    r"поставк\w*\s+(?:оборудован|сырь|ингредиент)|производств\w*\s+и\s+поставк\w*\s+оборудован|"
    r"оптов\w*\s*(?:поставк|продаж|торговл|компани|баз|склад)|(?:только|работаем)\s+оптом|"
    r"журнал|издательств|оргкомитет|\bпортал\b|ассоциац\w+\s+(?:компани|производител|предприятий|парфюмер)|союз\s+(?:предприятий|производител|компани)|"
    r"учебн\w+\s+(?:центр|заведен)|школ\w+\s+(?:визаж|косметолог|мастер|маникюр|парикмах|красот|обучен|бизнес)|академ\w+\s+(?:красот|стиля|визаж)|"
    r"обучени\w+\s+(?:мастеров|специалистов|косметологов|персонала|врачей)|курсы\s+(?:косметолог|визажист|мастеров)|повышени\w+\s+квалификац|"
    r"логистическ\w+\s+(?:компани|услуг|оператор)|фулфилмент|складск\w+\s+(?:услуг|логистик|комплектац)|"
    r"маркетингов\w+\s+агентств|рекламн\w+\s+агентств|digital[\s-]?агентств|smm[\s-]?агентств|\bb2b\b|"
    r"оборудован\w*\s+(?:для\s+(?:салонов|клиник|процедур|маникюр|педикюр|парикмах|косметолог|массаж|реабилитаци|эпиляц|лазерн|производств|медицинск)|и\s+инструмент|высокоинтенсивн|премиум)|"
    r"реабилитационн\w+\s+оборудован|производств\w*\s+(?:аппарат|оборудован|медтехник)|"
    r"аппарат\w*\s+(?:ударно|микроволнов|для\s+(?:салонов|клиник|процедур|маникюр|лазерн))|"
    r"поставк\w*[^.\n]{0,30}оборудован|косметологическ\w+\s+(?:оборудован|аппарат)|препарат\w*\s+(?:для\s+(?:косметолог|клиник|инъекц|эстетическ))|"
    r"одежд\w+\s+(?:для\s+(?:работник|медик|врач|персонал|салонов|индустрии))|медицинск\w+\s+одежд|\bуниформ|"
    r"школ\w+\s+(?:косметолог|визаж|мастер|маникюр|парикмах|красот|карбокситерапи|профессора|перманентн|бровист|массажа|обучен|нейл|титан)|"
    r"академ\w+\s+(?:косметолог|красот|стиля|визаж)|учебно[\s-]методическ",
    re.I,
)

# Упоминания дистрибьютора, где дистрибьютор — ТРЕТЬЕ лицо (у бренда есть дистрибьютор в РФ —
# это признак продаж в России, а не B2B-профиль участника). Вырезаются до поиска B2B_TEXT.
DIST_3P = re.compile(
    r"наш\w*\s+(?:эксклюзивн\w+\s+|официальн\w+\s+)?дистрибьютор\w*|"
    r"представлен\w*\s+(?:в\s+(?:России|РФ)\s+)?(?:эксклюзивн\w+\s+|официальн\w+\s+)?дистрибьютор\w*|"
    r"(?:стать|найти|ищ\w+|приглашаем\w*|станьте)\s+(?:его\s+|нашим\s+|их\s+|вашим\s+)?(?:эксклюзивн\w+\s+|официальн\w+\s+)?дистрибьютор\w*|"
    r"дистрибьютор\w*\s+(?:в|на)\s+(?:РФ|России|странах[^.,;—]{0,20}|Беларуси|Казахстане|своем регионе|ЕАЭС)[^.—]{0,40}(?:—|-{1,2})\s*[^.,;]{0,40}|"
    r"дистрибьюторск\w+\s+сет\w+|сеть\s+дистрибьютор\w*",
    re.I,
)

# Признак собственного производства/бренда: гасит «дистрибьюторский» none для производителей
# со своими торговыми марками (они часто дистрибутируют и чужое).
OWN_BRAND = re.compile(r"производ\w+\s+собственн\w+\s+(?:бренд|торгов|продукц)|собственн\w+\s+(?:бренд|торгов\w+\s+марк)|собственн\w+\s+производств", re.I)

DIST_SELF = re.compile(
    r"\bдистрибьютор\b|\bимпорт[её]р\b|дистрибьюторск\w+\s+(?:компани|бизнес)|"
    r"(?:явля\w+|выступа\w+|позициониру\w+)\s+(?:[^.;]{0,80}?)?(?:дистрибьютор|импорт[её]р)\w*|"
    r"(?:эксклюзивн\w+|официальн\w+)\s+представител\w+\s+(?:корпорац|производител|крупнейш|завод)|"
    r"представля\w+\s+и\s+распространя|распространя\w+\s+(?:продукци|на рынках|товар)|весь спектр продукции|"
    r"производств\w+,?\s+дистрибуци|дистрибуци\w+\s+и\s+импорт|импорт\w+\s+и\s+дистрибуци|"
    r"обслужива\w+\s+[^.;]{0,40}?(?:медицинск\w+\s+учрежден|клиник\w*\s+и\s+дистрибьютор|дистрибьютор\w+)",
    re.I,
)

# Профиль «B2B-дистрибьютор / импортёр / представитель корпорации» — сегмент none.

# Компания САМА является салоном/клиникой/студией (узко, для решения о сегменте clickout).
# Широкий SERVICE_HINTS («салонные протоколы», «для салонов») даёт ложные срабатывания на брендах.
# Рубрики каталога для этого НЕ используем: «Окрашивание волос», «Депиляция» и т.п. — чаще товары.
SERVICE_NAME = re.compile(
    r"\b(?:клиник\w*|салон(?:а|у|е|ы|ов|ом|ами|ах)?|барбершоп\w*|студи\w+|медцентр|косметологическ\w+\s+центр|"
    r"спа[\s-]+салон|спа[\s-]+центр|spa[\s-]+(?:салон|клиник\w*|центр))\b",
    re.I,
)
SERVICE_TEXT = re.compile(
    r"сет[ьиью]\s+(?:салонов|клиник|студий)|"
    r"наш\w*\s+(?:салон|клиник\w+|студи\w+|барбершоп\w*|медцентр|спа)|"
    r"наши\s+(?:салоны|клиники|студии|процедурн\w+|кабинет\w+|врач\w*|мастер\w*)|"
    r"(?:салон|клиника|студия|барбершоп|центр\s+красоты)\s+(?:красоты\s+)?(?:в|на)\s+(?:москв|санкт|петербург|город|улиц|район)|"
    r"мы\s*—?\s*(?:салон|клиника|студия|барбершоп|сеть)|"
    r"запис(?:аться|ь)\s+(?:на|к|онлайн)|запись\s+(?:на|к)\s+(?:процедур|при[её]м|консультаци)|"
    r"онлайн[\s-]+запись|предварительн\w+\s+запись|"
    r"процедур\w+\s+в\s+(?:нашем|салоне|клинике|студии|кабинете)|"
    r"при[её]м\s+(?:ведут|врач|косметолог|пациент)",
    re.I,
)

# Строгие признаки «компания сама оказывает услуги» для текста САЙТА (HTML шумнее каталога):
# запись на процедуру/приём, «наши салоны/клиники», «сеть салонов», «салон красоты в Москве».
SITE_SERVICE = re.compile(
    r"запис(?:аться|ь|ываетесь|ись|и)\s+(?:на|к)\s+(?:процедур|при[её]м|врач|косметолог|массаж|эпиляц)|"
    r"онлайн[\s-]+запис|запись\s+на\s+(?:процедур|при[её]м|консультаци)|"
    r"наши\s+(?:салоны|клиники|студии|центры|филиал)|сет[ьиью]\s+(?:салонов|клиник|студий|центров)|"
    r"(?:салон|клиник\w+|студи\w+|барбершоп)\s+(?:красоты\s+)?(?:в|на)\s+(?:москв|санкт|петербург|город\w*|улиц)|"
    r"мы\s*—?\s*(?:салон|клиника|студия|барбершоп)",
    re.I,
)

# Сайт/описание ПРЯМО говорят о продаже только через свой магазин или сеть.
ONLY_OWN = re.compile(
    r"(?:продаж\w+|реализаци\w+|торговл\w+)\s+(?:ид[её]т|осуществля\w+|вед[её]тся|только)\s+(?:только|исключительно)\s+(?:в|на|через)|"
    r"только\s+(?:в|на)\s+(?:наш|нашем|фирменн\w+|собственн\w+|официальн\w+)|"
    r"исключительно\s+(?:в|на|через)\s+(?:наш|нашем|фирменн\w+|собственн\w+|официальн\w+)|"
    r"не\s+(?:прода[её]тся|представлен\w*|торгу\w+)\s+на\s+маркетплейс|"
    r"не\s+работаем\s+с\s+маркетплейс|"
    r"единственный\s+официальный\s+(?:интернет[-\s]?)?магазин|"
    r"официальный\s+магазин\s+бренда\s+—\s+единственный",
    re.I,
)


def b2b_reason(row, text, name=""):
    """Явный B2B-профиль: только по рубрикам каталога, названию-школе или узким формулировкам текста.
    Возвращает причину или ''. Упоминания чужого дистрибьютора («дистрибьютор в РФ — X») не считаются."""
    cats = [n for n, t in categories(row) if t == "main"]
    hit = [c for c in cats if c in NONE_CATEGORIES]
    if hit:
        return "рубрика каталога: " + ", ".join(hit[:2])
    nm = name or ""
    if re.search(r"(?:^|/)\s*(?:школ\w+|академ\w+|учебн\w+\s+центр|институт)\b|\bшкол\w+\s*$", nm, re.I):
        return "название: школа/академия — учебный центр"
    if re.search(r"\b(?:equipment|machinery|packaging)\b", nm, re.I):
        return "название: equipment/machinery/packaging — оборудование или упаковка"
    clean_text = DIST_3P.sub(" ", text)
    m = DIST_SELF.search(clean_text)
    if m and not OWN_BRAND.search(text):
        return "B2B-дистрибьютор/импортёр: «" + clean_text[max(0, m.start()-30):m.end()+30].strip()[:70] + "»"
    m = B2B_TEXT.search(clean_text)
    if m:
        return "описание: «" + m.group(0).strip()[:60] + "»"
    return ""

COUNTRIES = {
    "RUS": "Россия", "BLR": "Беларусь", "CHN": "Китай", "KOR": "Южная Корея",
    "TUR": "Турция", "ITA": "Италия", "FRA": "Франция", "GBR": "Великобритания",
    "USA": "США", "DEU": "Германия", "ESP": "Испания", "IND": "Индия", "JPN": "Япония",
    "KAZ": "Казахстан", "UZB": "Узбекистан", "ARE": "ОАЭ", "BGR": "Болгария",
    "BRA": "Бразилия", "HKG": "Гонконг", "IDN": "Индонезия", "IRN": "Иран",
    "JOR": "Иордания", "KWT": "Кувейт", "PRK": "КНДР", "QAT": "Катар", "ROU": "Румыния",
    "SAU": "Саудовская Аравия", "SRB": "Сербия", "SYR": "Сирия", "THA": "Таиланд",
    "TWN": "Тайвань",
    "ARM": "Армения", "KGZ": "Киргизия",
}

# ЕАЭС считаем как Россию: Беларусь, Казахстан, Армения, Киргизия — российские клиенты,
# продажи в РФ и на российских маркетплейсах для них обычная практика (решение Никиты 13.10.2026).
EAEU = {"Россия", "Беларусь", "Казахстан", "Армения", "Киргизия"}

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


def cache_key(url):
    return hashlib.sha256(url.encode("utf-8", "ignore")).hexdigest()[:24]


def fetch_url(url):
    """Кэшированный GET: повторный запуск читает JSON из cache/intercharm-sites."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{cache_key(url)}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    rec = {"url": url, "ok": False, "status": None, "final_url": url, "text": "", "error": ""}
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "ru,en;q=0.8"})
        with urlopen(req, timeout=FETCH_TIMEOUT) as r:
            raw = r.read(600_000)
            enc = r.headers.get_content_charset() or "utf-8"
            rec.update({
                "ok": 200 <= getattr(r, "status", 200) < 400,
                "status": getattr(r, "status", 200),
                "final_url": r.geturl(),
                "text": raw.decode(enc, "replace"),
            })
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
    rec["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    p.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return rec


def candidate_pages(base_url, home_html):
    base = base_url if base_url.endswith("/") else base_url + "/"
    out = []
    for path in ("shop", "catalog", "products", "where-to-buy", "gde-kupit", "stores", "basket", "cart"):
        out.append(urljoin(base, path))
    for m in re.finditer(r"href=[\"']([^\"'#]+)[\"']", home_html or "", re.I):
        href = html.unescape(m.group(1)).strip()
        low = href.lower()
        text_window = (home_html[max(0, m.start()-120):m.end()+120] or "").lower()
        if any(w in low or w in text_window for w in ("shop", "catalog", "product", "cart", "basket", "store", "where", "gde", "куп", "магаз", "каталог", "корзин")):
            u = urljoin(base_url, href)
            if urlparse(u).netloc == urlparse(base_url).netloc:
                out.append(u)
    seen, clean = set(), []
    for u in out:
        u = u.split("#", 1)[0]
        if u not in seen and len(clean) < 3:
            seen.add(u); clean.append(u)
    return clean


def mp_from_text(text):
    found = []
    low = (text or "").lower()
    for code, domains in MP_DOMAINS.items():
        if any(d in low for d in domains):
            found.append(code)
    return found


def app_from_text(text):
    low = (text or "").lower()
    return any(d in low for d in APP_DOMAINS)


def own_from_text(text, url=""):
    low = (text or "").lower()
    if SHOP_WORDS.search(low):
        return True
    if PRICE_WORDS.search(low) and re.search(r"купить|заказать|наличи|доставк", low, re.I):
        return True
    # Сам путь /catalog или /shop не считаем продажей: у B2B-сайтов это часто просто витрина.
    # Засчитываем только корзину/оформление в URL.
    if re.search(r"/(cart|basket|checkout)\b", urlparse(url).path, re.I):
        return True
    return False


def site_features(url):
    if not url:
        return {"opened": False, "pages": 0, "mp": [], "own_shop": False, "app": False, "only_own": False, "service": False, "evidence": "сайта нет в каталоге"}
    pages = []
    home = fetch_url(url)
    pages.append(home)
    if home.get("ok"):
        for u in candidate_pages(home.get("final_url") or url, home.get("text") or ""):
            if u != url:
                pages.append(fetch_url(u))
    ok_pages = [p for p in pages if p.get("ok")]
    text = "\n".join((p.get("final_url") or "") + "\n" + (p.get("text") or "") for p in ok_pages)
    mp = sorted(set(mp_from_text(text)), key=["ozon", "wb", "ym", "megamarket", "lamoda", "goldapple"].index)
    own = own_from_text(text, url) or any(own_from_text(p.get("text") or "", p.get("final_url") or "") for p in ok_pages)
    app = app_from_text(text)
    only_own = bool(ONLY_OWN.search(text))
    service = bool(SITE_SERVICE.search(text))
    if ok_pages:
        ev = []
        if own: ev.append("на сайте есть признаки заказа/корзины")
        if mp: ev.append("сайт ссылается на " + ", ".join(mp))
        if app: ev.append("есть ссылка на приложение")
        if only_own: ev.append("заявлена продажа только через свой магазин/сеть")
        if service: ev.append("на сайте — услуги/запись на процедуры (салон/клиника/студия)")
        if not ev: ev.append("сайт открылся, продажа не найдена")
        ev.append("проверено: " + ", ".join((p.get("final_url") or p.get("url") or "") for p in ok_pages[:3]))
        return {"opened": True, "pages": len(ok_pages), "mp": mp, "own_shop": own, "app": app, "only_own": only_own, "service": service, "evidence": "; ".join(ev)}
    err = home.get("error") or str(home.get("status") or "не открылся")
    return {"opened": False, "pages": 0, "mp": [], "own_shop": False, "app": False, "only_own": False, "service": False, "evidence": "сайт не открылся: " + err[:120]}


def catalog_features(row):
    text = " ".join([
        txt(row.get("name")), row.get("brand") or "", txt(row.get("brief")), txt(row.get("about")), txt(row.get("descr")),
        " ".join(n for n, t in categories(row) if t == "main")
    ])
    mp = sorted(set(mp_from_text(text)), key=["ozon", "wb", "ym", "megamarket", "lamoda", "goldapple"].index)
    own = bool(re.search(r"интернет[- ]магазин|собственн.*магазин|сайт.*заказ|заказ.*сайт|онлайн[- ]магазин|розничн", text, re.I))
    app = app_from_text(text)
    only_own = bool(ONLY_OWN.search(text))
    return {"mp": mp, "own_shop": own, "app": app, "only_own": only_own, "evidence": "описание/рубрики каталога"}


def segment_for(row, country, prio, site_info):
    """Сегмент по итоговым правилам Никиты (13.10.2026): mp / clickout / both / none, без unknown.

    mp       — Андрей: присутствие на МП ПОДТВЕРЖДЕНО (сайт/описание). Свой магазин тоже может быть — всё равно Андрей.
    clickout — Никита: на МП их НЕТ ЯВНО (услуги с онлайн-записью или «продажа только через свой магазин/сеть») + свой канал.
    both     — «Оба, уточнить у стенда»: непонятно, есть ли на МП (бренды/розница без подтверждённых ссылок,
               сайт не открылся, иностранец-потребитель без признаков продаж в РФ).
    none     — никому, ТОЛЬКО по профилю: B2B, сырьё, упаковка, оборудование, OEM/ODM, B2B-дистрибьюторы, пресса, школы.
    ЕАЭС (Беларусь, Казахстан, Армения, Киргизия) — как Россия. Маркетплейсы не проверяем (блокируют).
    """
    cat = catalog_features(row)
    mp = sorted(set(site_info.get("mp", []) + cat["mp"]), key=["ozon", "wb", "ym", "megamarket", "lamoda", "goldapple"].index)
    own = bool(site_info.get("own_shop") or cat["own_shop"])
    app = bool(site_info.get("app") or cat["app"])
    only_own = bool(site_info.get("only_own") or cat.get("only_own"))
    text = " ".join([txt(row.get("brief")), txt(row.get("about")), txt(row.get("descr")), " ".join(n for n, t in categories(row) if t == "main")])
    opened = site_info.get("opened")
    s_url = site(row)
    b2b = b2b_reason(row, text, txt(row.get("name")))
    name = txt(row.get("name"))
    cats = [n for n, t in categories(row) if t == "main"]
    # Сигнал «услуги» из текста САЙТА шумный: бренды ставят виджеты «запись на мастер-класс/экскурсию»
    # и карты партнёрских салонов. Он засчитывается, только если профиль каталога НЕ потребительский товар.
    has_a_cat = any(c in A_CATEGORIES for c in cats)
    service = bool(SERVICE_TEXT.search(text)) or bool(SERVICE_NAME.search(name)) or (bool(site_info.get("service")) and not has_a_cat)
    foreign = bool(country) and country not in EAEU
    # Свой потребительский бренд + свой канал (магазин, заказ, приложение) — не none, даже если компания
    # ещё и контрактный производитель или оптовик (Никита, 13.10.2026: пример — Dance Legend).
    goods_b2b = any(c in B2B_GOODS for c in cats)
    consumer_channel = has_a_cat and (own or app) and not goods_b2b
    andrey = ANDREY_MP.get(row.get("_id"))
    if andrey:
        mp = sorted(set(mp) | {{"WB": "wb", "Ozon": "ozon"}[m.strip()] for m in (andrey["mp"] or "").split("/") if m.strip() in ("WB", "Ozon")},
                    key=["ozon", "wb", "ym", "megamarket", "lamoda", "goldapple"].index)

    if andrey:
        seg = "mp"
        reason = "Андрей проверил 09.10: есть на " + (andrey["mp"] or "WB/Ozon") + (" (" + andrey["source"] + ")" if andrey["source"] else "")
        if own: reason += "; свой магазин тоже есть — всё равно Андрей"
    elif mp:
        seg = "mp"
        src = []
        if site_info.get("mp"): src.append("сайт ссылается на " + ", ".join(site_info["mp"]))
        if cat["mp"]: src.append("в описании каталога упомянуты " + ", ".join(cat["mp"]))
        reason = "присутствие на МП подтверждено: " + "; ".join(src)
        if own: reason += "; свой магазин тоже есть — всё равно Андрей"
    elif b2b and consumer_channel and not re.search(r"\boem\b|\bodm\b|оборудован|аппарат", b2b, re.I):
        seg = "both"
        reason = ("свой потребительский бренд и свой канал продаж (" + ("магазин/заказ" if own else "приложение") +
                  "), хотя в профиле есть B2B (" + b2b + "); ссылок на МП не найдено — уточнить у стенда")
    elif b2b:
        seg = "none"
        reason = "B2B-профиль (" + b2b + ") — ни Никите, ни Андрею"
    elif service and (own or app):
        seg = "clickout"
        reason = "услуги (салон/клиника/студия) — на МП не продаются; есть " + ("онлайн-запись/заказ" if own else "приложение")
    elif only_own:
        seg = "clickout"
        reason = "сайт/описание прямо говорят: продажа только через свой магазин или сеть"
    elif service:
        seg = "both"
        reason = "услуги — на МП не продаются, но онлайн-записи/заказа на сайте не найдено; уточнить у стенда"
    elif own or app:
        seg = "both"
        reason = "свой магазин" + ("/приложение" if app else "") + " есть, ссылок на МП не найдено — непонятно, есть ли на маркетплейсах; уточнить у стенда"
    elif s_url and not opened:
        seg = "both"
        reason = "сайт не открылся — непонятно, есть ли на МП и свой заказ; уточнить у стенда"
    elif not s_url:
        seg = "both"
        reason = "сайта нет в каталоге — непонятно, есть ли на МП; уточнить у стенда"
    else:
        seg = "both"
        reason = "сайт открылся, ни своего заказа, ни ссылок на МП не найдено — непонятно; уточнить у стенда"
    if foreign and seg != "none":
        reason += "; " + country + " — не ЕАЭС, уточнить продажи в РФ"
    ev = reason
    site_ev = site_info.get("evidence") or ""
    if site_ev and "сайта нет" not in site_ev:
        ev += "; " + site_ev
    if cat["mp"] or cat["own_shop"] or cat["app"]:
        ev += "; каталог: " + ", ".join(x for x in [cat["evidence"], ("МП " + ", ".join(cat["mp"]) if cat["mp"] else ""), ("свой магазин" if cat["own_shop"] else ""), ("приложение" if cat["app"] else "")] if x)
    return seg, ev[:500], mp, own, app


def site_features_map(raw_rows):
    urls = sorted({site(r) for r in raw_rows if site(r)})
    if not urls:
        return {}
    socket.setdefaulttimeout(FETCH_TIMEOUT)
    print(f"site cache: {CACHE} · {len(urls)} сайтов", file=sys.stderr)
    out = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
        futs = {ex.submit(site_features, u): u for u in urls}
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            u = futs[fut]
            try:
                out[u] = fut.result()
            except Exception as e:
                out[u] = {"opened": False, "pages": 0, "mp": [], "own_shop": False, "app": False, "evidence": f"ошибка проверки сайта: {type(e).__name__}: {e}"}
            if i % 100 == 0:
                print(f"  checked {i}/{len(urls)}", file=sys.stderr)
    return out


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
    features = site_features_map(rows)
    out = []
    for r in rows:
        name = txt(r.get("name")) or txt(r.get("name"), "en")
        if not name:
            continue
        cats = [n for n, t in categories(r) if t == "main"]
        contacts = r.get("contacts") or {}
        country = COUNTRIES.get(contacts.get("country"), contacts.get("country") or "")
        prio, top, tags, hl, h = classify(r, country)
        s = site(r)
        seg, seg_evidence, mp, own_shop, app = segment_for(r, country, prio, features.get(s, {"opened": False, "evidence": "сайт не проверен"}))
        if seg == "none":
            prio, top = "C", False
        about = txt(r.get("about")) or txt(r.get("brief"))
        descr = txt(r.get("descr"))
        full = " ".join(x for x in [about, descr] if x)
        city = txt(contacts.get("city"))
        out.append({
            "id": r.get("_id") or "",
            "hall": h,
            "stand": r.get("stand") or "",
            "name": name,
            "country": country,
            "city": city,
            "site": s,
            "profile": cats[:3],
            "descr": full[:300],
            "products": [],
            "hl": hl,
            "brands": [b.strip() for b in re.split(r"[;,]", r.get("brand") or "") if b.strip()][:5],
            "tags": tags[:3],
            "prio": prio,
            "top": top,
            "seg": seg,
            "seg_evidence": seg_evidence,
            "mp": mp,
            "own_shop": own_shop,
            "app": app,
            "meta": " · ".join(x for x in [country, city] if x),
            "_phones": phones(r),
            "_emails": emails(r),
        })
    seg_order = {"clickout": 0, "mp": 1, "both": 2, "none": 3}
    order = {"A": 0, "B": 1, "C": 2}
    out.sort(key=lambda x: (seg_order.get(x.get("seg"), 9), order[x["prio"]], not x["top"], x["hall"], x["name"].lower()))
    return out


CFG = {
    "title": "InterCHARM 2026 · участники по сегментам Никита / Андрей",
    "kicker": "Click Out · InterCHARM · 14–17.10.2026 · Крокус Экспо, павильон 3",
    "h1": "{n} участников каталога: кому идти Никите, кому Андрею",
    "sub": ("Каталог снят 12.10.2026 из официального API InterCHARM (catalog.expovr.ru): {n} компаний, "
            "стенды, категории, сайты, города. Разметка: сегмент владельца + эшелон внутри сегмента: <b>A — {a}</b> (из них ★ {top}), <b>B — {b}</b>, C — {c}. "
            "Список пополняется — перед выставкой снять ещё раз."),
    "legend": [
        ("Никита", "Click Out: на маркетплейсах их нет ЯВНО — услуги (салоны, клиники косметологии, SPA, студии с онлайн-записью) или продажа только через свой магазин/сеть, — и есть свой канал: сайт с заказом или записью, интернет-магазин, приложение."),
        ("Андрей", "Внешний трафик на маркетплейсы: присутствие на Ozon / WB / Яндекс Маркете / Мегамаркете / Lamoda / Золотом Яблоке ПОДТВЕРЖДЕНО сайтом или описанием. Свой магазин при этом тоже может быть — всё равно Андрей."),
        ("Оба — уточнить", "Непонятно, есть ли на маркетплейсах: потребительские бренды и розница без подтверждённых ссылок на МП, сайты, которые не открылись, иностранные бренды без признаков продаж в РФ. У стенда: «Вы есть на маркетплейсах?» Да — Андрей; нет и есть свой сайт/магазин — Никита."),
        ("Никому", "Только по профилю: B2B, сырьё, упаковка, оборудование, контрактное производство / OEM / ODM, B2B-дистрибьюторы, пресса, школы и учебные центры. ЕАЭС (Беларусь, Казахстан, Армения, Киргизия) — как Россия."),
        ("A/B/C", "эшелон внутри сегмента: A — целевой для своего руководителя, B — с оговорками, C — нецелевой; none → C."),
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
    loaded = load()
    emit(CFG, loaded, ROOT / "intercharm", sys.argv)
    for r in loaded:
        if r["prio"] in ("A", "B"):
            star = "★" if r["top"] else " "
            print(f'{r.get("seg", ""):8} {r["prio"]}{star} {r["stand"]:8} | {r["name"][:34]:34} | {r["hall"][:18]:18} | '
                  f'{r["site"][:28]:28} | {", ".join(r.get("mp", []))[:12]:12} | {", ".join(r["tags"][:3])[:36]}')
