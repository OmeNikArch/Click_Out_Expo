#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор презентаций Click Out под конкретные выставки.
Клон presenter.html (версия ведущего с суфлёром и формой-опросником) + элементы
предварительного аудита под нишу выставки (ниша в цифрах, сегменты по площадкам,
бенчмарки, чек-лист аудита, кейсы и смежные направления Церебро).

Данные событий — events/data.py. Запуск из корня репозитория:
    python3 events/build.py
На выходе для каждого события: <slug>/presenter.html (ведущему) и <slug>/index.html (клиенту),
плюс events.html — оглавление.
"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from data import EVENTS, COMMON  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent

WEBHOOK_URL = ("https://script.google.com/macros/s/AKfycbxk6iyhU5V-6hkcZbyMODE1YIqrjGNJxz6tjhiiXn7PuxB-W2iWnuBEkfz0kcIpAR3D/exec")

SOURCE_OPTIONS = [
    "ОТДЫХ Leisure · 02–04.09",
    "WorldFood · 15–18.09",
    "Дентал-Экспо · 21–24.09",
    "ПаркЗоо · 23–25.09",
    "BUYBRAND · 29.09–01.10",
    "InterCHARM · 14–17.10",
    "РАППА Осень · 21–22.10",
    "PIR Expo · 26–29.10",
]

CSS = r"""
  :root{
    --bg:#000; --card:#272727; --card2:#111;
    --txt:#E7E6E6; --mute:#A5A5A5; --yellow:#FDD101; --white:#fff;
    --head:'Unbounded', Arial, sans-serif; --body:Arial, Helvetica, sans-serif;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{background:var(--bg);color:var(--txt);font-family:var(--body)}
  section{min-height:100vh;padding:6vh 7vw;display:flex;flex-direction:column;justify-content:center;position:relative;border-bottom:1px solid #1a1a1a}
  .kicker{display:flex;align-items:center;gap:14px;margin-bottom:26px}
  .kicker .bar{width:44px;height:8px;background:var(--yellow);flex:none}
  .kicker span{font-family:var(--head);font-weight:700;font-size:13px;letter-spacing:.08em;color:var(--yellow);text-transform:uppercase}
  .num{position:absolute;top:5vh;right:7vw;color:var(--mute);font-size:14px}
  h1{font-family:var(--head);font-weight:700;color:var(--white);font-size:clamp(28px,4.6vw,58px);line-height:1.1;margin-bottom:24px}
  h2{font-family:var(--head);font-weight:700;color:var(--white);font-size:clamp(23px,3.2vw,42px);line-height:1.14;margin-bottom:26px}
  .sub{font-size:clamp(16px,1.6vw,22px);line-height:1.45;max-width:66ch}
  .sub b{color:var(--white)}
  .sub a{color:var(--yellow)}
  .yline{color:var(--yellow);font-family:var(--head);font-weight:700;font-size:clamp(16px,1.7vw,24px);margin-top:32px;line-height:1.3}
  .logo{display:flex;align-items:center;gap:16px;margin-bottom:44px}
  .logo .sign{width:56px;height:56px;background:var(--white);border:7px solid var(--yellow);display:flex;align-items:center;justify-content:center;font-family:var(--head);font-weight:700;color:#000;font-size:26px}
  .logo .nm{font-family:var(--head);font-weight:700;color:var(--white);font-size:18px;line-height:1.25}
  .mark{position:absolute;bottom:5vh;right:7vw;width:38px;height:38px;background:var(--white);border:5px solid var(--yellow);display:flex;align-items:center;justify-content:center;font-family:var(--head);font-weight:700;color:#000;font-size:17px;opacity:.9}
  .cards{display:grid;gap:20px;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));margin-top:10px}
  .card{background:var(--card);border-radius:18px;padding:26px 28px}
  .card h3{font-family:var(--head);font-weight:700;color:var(--white);font-size:clamp(15px,1.4vw,20px);margin-bottom:12px}
  .card p{font-size:clamp(13px,1.15vw,17px);line-height:1.5;color:var(--txt)}
  .card p+p{margin-top:8px}
  .card .big{font-family:var(--head);font-weight:700;color:var(--yellow);font-size:clamp(26px,3.2vw,44px);line-height:1;margin-bottom:10px}
  .card .cap{color:var(--mute);font-size:13px;margin-top:12px;line-height:1.4}
  .card.hl{border:1px solid var(--yellow)}
  .card .tag{display:inline-block;background:var(--yellow);color:#000;font-family:var(--head);font-weight:700;font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:5px 12px;border-radius:100px;margin-bottom:14px}
  .stats{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));margin-top:14px}
  .stat .n{font-family:var(--head);font-weight:700;color:var(--yellow);font-size:clamp(30px,4vw,56px);line-height:1}
  .stat .t{color:var(--txt);font-size:clamp(13px,1.15vw,17px);margin-top:10px;line-height:1.4}
  .stats.niche{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
  .stats.niche .n{font-size:clamp(22px,2.6vw,38px);white-space:nowrap}
  .rows{margin-top:12px;max-width:1150px}
  .row{display:grid;grid-template-columns:minmax(150px,240px) 1fr;gap:26px;padding:20px 0;border-top:1px solid #232323;align-items:start}
  .row .l{font-family:var(--head);font-weight:700;color:var(--yellow);font-size:clamp(14px,1.3vw,19px)}
  .row .r{font-size:clamp(14px,1.2vw,18px);line-height:1.5}
  .row .r b{color:var(--white)}
  .foot{margin-top:34px;color:var(--mute);font-size:clamp(12px,1vw,15px);line-height:1.5;max-width:80ch}
  .foot a{color:var(--yellow)}
  .price{display:grid;gap:20px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));margin-top:10px}
  .p{background:var(--card2);border:1px solid #262626;border-radius:18px;padding:26px 28px;position:relative}
  .p.best{border-color:var(--yellow)}
  .p .tag{position:absolute;top:-13px;left:26px;background:var(--yellow);color:#000;font-family:var(--head);font-weight:700;font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:5px 12px;border-radius:100px}
  .p h3{font-family:var(--head);font-weight:700;color:var(--white);font-size:clamp(15px,1.4vw,20px);margin-bottom:16px}
  .p .was{color:var(--mute);text-decoration:line-through;font-size:15px}
  .p .now{font-family:var(--head);font-weight:700;color:var(--yellow);font-size:clamp(24px,2.8vw,38px);line-height:1.1;margin:6px 0 4px}
  .p .per{color:var(--mute);font-size:13px}
  .p ul{list-style:none;margin-top:16px}
  .p li{font-size:clamp(13px,1.1vw,16px);line-height:1.5;padding-left:18px;position:relative;margin-bottom:8px}
  .p li:before{content:"";position:absolute;left:0;top:9px;width:7px;height:7px;background:var(--yellow)}
  ul.seg{list-style:none;margin-top:6px}
  ul.seg li{font-size:clamp(13px,1.15vw,17px);line-height:1.5;padding-left:20px;position:relative;margin-bottom:9px}
  ul.seg li:before{content:"";position:absolute;left:0;top:9px;width:7px;height:7px;background:var(--yellow)}
  ul.seg li b{color:var(--white)}
  .grid2{display:grid;gap:30px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));margin-top:10px}
  .grid3{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));margin-top:10px}
  .colh{font-family:var(--head);font-weight:700;color:var(--white);font-size:clamp(15px,1.5vw,21px);margin-bottom:14px}
  .colh small{display:block;color:var(--mute);font-family:var(--body);font-weight:400;font-size:13px;margin-top:6px;line-height:1.4}
  table.bench{border-collapse:collapse;margin-top:14px;width:100%;max-width:1150px}
  table.bench th{font-family:var(--head);font-weight:700;color:var(--yellow);font-size:clamp(11px,1vw,14px);text-align:left;padding:12px 14px;border-bottom:2px solid var(--yellow);text-transform:uppercase;letter-spacing:.05em}
  table.bench td{font-size:clamp(13px,1.1vw,16px);padding:12px 14px;border-bottom:1px solid #232323;line-height:1.45;vertical-align:top}
  table.bench td:first-child{font-family:var(--head);font-weight:700;color:var(--white)}
  table.bench .tbd{color:var(--mute)}
  .twrap{overflow-x:auto;max-width:100%}
  .note{display:inline-block;background:#0d0d0d;border-left:5px solid var(--yellow);border-radius:0 12px 12px 0;padding:16px 20px;margin-top:24px;font-size:clamp(13px,1.1vw,16px);line-height:1.55;color:#cfcfcf;max-width:80ch}
  .note b{color:var(--white)}
  .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
  .chip{border:1px solid #3a3a3a;border-radius:100px;color:var(--txt);font-size:clamp(12px,1vw,14px);padding:7px 14px;line-height:1.3}
  .chip.y{border-color:var(--yellow);color:var(--yellow)}
  .q{background:var(--card2);border:1px solid #262626;border-radius:18px;padding:24px 28px;margin-bottom:16px}
  .q .qn{font-family:var(--head);font-weight:700;color:var(--yellow);font-size:13px;letter-spacing:.06em;margin-bottom:10px}
  .q .qt{font-family:var(--head);font-weight:700;color:var(--white);font-size:clamp(16px,1.7vw,24px);line-height:1.25}
  .prompter{display:none;margin-top:26px;border-left:5px solid var(--yellow);background:#0d0d0d;padding:20px 24px;border-radius:0 14px 14px 0}
  body.souffleur .prompter{display:block}
  .prompter .lbl{font-family:var(--head);font-weight:700;color:var(--yellow);font-size:11px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px}
  .prompter p{font-size:15px;line-height:1.55;color:#cfcfcf;margin-bottom:9px}
  .prompter p b{color:var(--white)}
  .prompter a{color:var(--yellow)}
  .toggle{position:fixed;right:16px;bottom:16px;z-index:50;background:#151515;border:1px solid #333;color:var(--mute);font-family:var(--head);font-weight:700;font-size:11px;letter-spacing:.08em;text-transform:uppercase;padding:10px 16px;border-radius:100px;cursor:pointer}
  body.souffleur .toggle{background:var(--yellow);color:#000;border-color:var(--yellow)}
  .btn{display:inline-block;background:var(--yellow);color:#000;font-family:var(--head);font-weight:700;font-size:clamp(14px,1.3vw,18px);padding:18px 34px;border-radius:100px;text-decoration:none;margin-top:26px}
  .lead{font-family:var(--head);font-weight:500;color:var(--yellow);font-size:clamp(15px,1.5vw,21px);line-height:1.35;margin-bottom:20px}
  .form{margin-top:26px;max-width:1180px}
  .fgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin-bottom:26px}
  .fl{display:block;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--yellow);font-weight:700;margin-bottom:8px}
  .fi,.fs,.ft{width:100%;background:#0f0f0f;border:1px solid #2a2a2a;border-radius:12px;color:#fff;
    font-family:inherit;font-size:16px;line-height:1.5;padding:12px 14px;outline:none}
  .ft{min-height:84px;resize:vertical}
  .fi:focus,.fs:focus,.ft:focus{border-color:var(--yellow)}
  .fs{-webkit-appearance:none;appearance:none;background:#0f0f0f url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' fill='%23FDD101'><path d='M2 5l5 5 5-5z'/></svg>") no-repeat right 14px center;
    border:1px solid #2a2a2a;border-radius:12px;color:#fff;font-family:inherit;font-size:16px;padding:12px 38px 12px 14px;outline:none}
  .fq{margin-bottom:20px}
  .fq .qq{font-size:19px;font-weight:600;margin-bottom:8px}
  .fq .qq b{color:var(--yellow);font-family:var(--head);margin-right:10px}
  .fq .hint{color:var(--mute);font-size:14px;margin:-4px 0 10px;line-height:1.45}
  .xa{background:#0d0d0d;border:1px solid #262626;border-radius:16px;padding:20px 22px;margin-bottom:26px}
  .xa .xh{font-family:var(--head);font-weight:700;color:var(--white);font-size:15px;margin-bottom:6px}
  .xa .xs{color:var(--mute);font-size:13px;margin-bottom:14px;line-height:1.45}
  .xgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
  .send{background:var(--yellow);color:#000;border:0;border-radius:14px;font-family:var(--head);font-weight:700;
    font-size:18px;padding:16px 34px;cursor:pointer}
  .send:disabled{opacity:.5;cursor:default}
  .st{margin-top:14px;font-size:15px;color:var(--mute)}
  .st.ok{color:#7fe08a}.st.err{color:#ff8a8a}
  .evhead{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:22px}
  .evhead .chip{font-family:var(--head);font-weight:700;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
  @media screen and (max-width:1100px){
    .price{grid-template-columns:1fr}
    .cards{grid-template-columns:1fr}
    .grid2,.grid3{grid-template-columns:1fr}
    .row{grid-template-columns:1fr;gap:8px}
    section{padding:7vh 8vw}
  }
  @media print{
    @page{size:1600px 1500px;margin:0}
    *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
    html,body{background:#000}
    section{min-height:auto;height:auto;page-break-inside:avoid;page-break-after:always;padding:70px 90px;border-bottom:none;justify-content:flex-start}
    .num{top:60px;right:90px}
    .mark{bottom:60px;right:90px}
    .toggle{display:none!important}
    .prompter{display:block!important}
    table.bench td{padding:8px 12px;font-size:13px}
    table.bench th{padding:8px 12px;font-size:11px}
    .chips{margin-top:10px}
    section.long{page-break-inside:auto}
  }
"""


def seg(items):
    return '<ul class="seg">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def rows(pairs):
    return '<div class="rows">' + "".join(
        f'<div class="row"><div class="l">{l}</div><div class="r">{r}</div></div>' for l, r in pairs) + "</div>"


def prompter(label, paras):
    return (f'<div class="prompter"><div class="lbl">{label}</div>'
            + "".join(f"<p>{p}</p>" for p in paras) + "</div>")


def bench_table(ev):
    """Средние Click Out по трём источникам + строки под нишу («после аудита»)."""
    avg = COMMON["bench_avg"]
    head = ("<tr><th>Источник · сегмент</th><th>Охват</th><th>Показы</th><th>CPM</th>"
            "<th>CTR</th><th>CPC</th></tr>")
    body = ""
    for src_key, src_name in (("ozon", "Ozon Performance"), ("urban", "Яндекс Urban Ads"), ("wb", "WB Media")):
        a = avg[src_key]
        body += (f"<tr><td>{src_name} · средние клиентов СРК</td><td>—</td><td>—</td>"
                 f"<td>{a['cpm']}</td><td>{a['ctr']}</td><td>{a['cpc']}</td></tr>")
        for r in ev["bench_rows"][src_key]:
            body += (f'<tr><td>{src_name} · {r}</td>' + '<td class="tbd">после аудита</td>' * 5 + "</tr>")
    return f'<div class="twrap"><table class="bench">{head}{body}</table></div>'


def build(ev, presenter=True):
    n = [0]

    def num():
        n[0] += 1
        return f"{n[0]:02d}"

    P = (lambda label, paras: prompter(label, paras)) if presenter else (lambda *a, **k: "")
    s = []
    ev_chip = f'{ev["name"]} · {ev["dates"]} · {ev["venue"]}'

    # ---------- 01 Титул ----------
    num()
    s.append(f"""
<section>
  <div class="logo"><div class="sign">Ц</div><div class="nm">Церебро<br>Таргет</div></div>
  <div class="kicker"><div class="bar"></div><span>Направление Click Out · {ev['name']} · {ev['dates']}</span></div>
  <h1>{ev['title_h1']}</h1>
  <p class="sub">{ev['title_sub']}</p>
  <div class="yline">Ozon Performance · Яндекс Urban Ads · WB Media</div>
  {P("Что сказать · 30 секунд, потом молчим", ev['p_title'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 02 Кто мы ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Кто мы</span></div>
  <h2>Диджитал-агентство<br>«Церебро Диджитал»</h2>
  <div class="stats">
    <div class="stat"><div class="n">100+</div><div class="t">проектов Click Out в 29 нишах</div></div>
    <div class="stat"><div class="n">89 700+</div><div class="t">заявок клиентам направления за два года</div></div>
    <div class="stat"><div class="n">3 из 3</div><div class="t">сертифицированный партнёр Ozon Performance, Яндекс Urban Ads и WB Media</div></div>
    <div class="stat"><div class="n">10+ лет</div><div class="t">на российских рекламных площадках, 3000+ клиентов агентства</div></div>
  </div>
  <p class="sub" style="margin-top:34px">Шесть направлений под одной крышей: Click Out, ВК Реклама, Яндекс Директ, Авито,
  внешний трафик для селлеров и Яндекс ПромоСтраницы. За каждым клиентом закреплён специалист по источникам:
  он ведёт кампании, готовит отчётность и отвечает за стоимость заявки, объём и качество трафика.</p>
  {P("Что сказать", COMMON['p_who'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 03 Продукт ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Продукт</span></div>
  <h2>Click Out — это выход<br>с маркетплейса на ваш сайт</h2>
  <div class="cards">
    <div class="card"><h3>Что делает контекст</h3>
      <p>Собирает тех, кто уже сформулировал запрос и пошёл искать. Спрос конечный: когда он выбран,
      каждая следующая заявка дороже предыдущей.</p></div>
    <div class="card"><h3>Что делает Click In</h3>
      <p>Продвигает карточку товара внутри площадки. Работает для тех, кто на площадке торгует.
      Услугам этот формат недоступен.</p></div>
    <div class="card"><h3>Что делаем мы</h3>
      <p>Показываем вашу рекламу человеку, который пришёл на площадку за покупками, и приводим его
      на ваш сайт. Контекст работает с теми, кто вас уже ищет. Мы начинаем раньше — с человеком,
      который о вас ещё не думал.</p></div>
  </div>
  <div class="yline">{ev['product_yline']}</div>
  {P("Что сказать", ev['p_product'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 04 Три источника ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Где работает</span></div>
  <h2>Три источника — три разные аудитории</h2>
  <div class="cards">
    <div class="card"><div class="big">65 млн</div><h3>Ozon Performance</h3>
      <p>Активные покупатели за 2025 год, в среднем 38 заказов на человека, 83% — вне Москвы и Петербурга.
      Таргетинг по полу, возрасту, гео, сегментам «покупают / смотрят категорию», B2B, плюс загрузка вашей базы.</p>
      <p class="cap">Форматы: видеобаннер, баннер на главной и в поиске, размещение в карточке, экран «заказ выполнен»</p></div>
    <div class="card"><div class="big">до 94 млн</div><h3>Яндекс Urban Ads</h3>
      <p>Аудитория в месяц по сервисам Яндекса: Маркет, Еда, Лавка, Go, Деливери. Доход средний и выше,
      интересы, история покупок, подписка Плюс, тарифы такси. CPM от 50 ₽.</p>
      <p class="cap">Форматы: видеобаннер, горизонтальный баннер, растяжка, вертикальный баннер</p></div>
    <div class="card"><div class="big">79 млн</div><h3>WB Media</h3>
      <p>Посетителей, из них 49 млн покупателей. 78% — женщины 25–44. Поведенческие сегменты DMP
      на основе реальных покупок: поиск, корзина, покупка.</p>
      <p class="cap">Форматы: баннер на главной, видео 15 секунд, слайдер в личном кабинете, DMP-таргеты</p></div>
  </div>
  <div class="foot">{ev['sources_foot']}</div>
  {P("Что сказать", ev['p_sources'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 05 Ниша в цифрах ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Предварительный аудит · Ваша ниша в цифрах</span></div>
  <h2>{ev['niche_h2']}</h2>
  <div class="stats niche">{"".join(f'<div class="stat"><div class="n">{v}</div><div class="t">{t}</div></div>' for v, t in ev['niche_stats'])}
  </div>
  <p class="sub" style="margin-top:34px">{ev['niche_text']}</p>
  <div class="foot">{ev['niche_sources']}</div>
  {P("Что сказать", ev['p_niche'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 06 Два разговора на выставке ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>{ev['name']} · Кто перед нами</span></div>
  <h2>{ev['aud_h2']}</h2>
  <div class="cards">{"".join(f'<div class="card{" hl" if c.get("hl") else ""}">{"<div class=tag>" + c["tag"] + "</div>" if c.get("tag") else ""}<h3>{c["h"]}</h3>{"".join(f"<p>{p}</p>" for p in c["p"])}</div>' for c in ev['aud_cards'])}
  </div>
  <div class="foot">{ev['aud_foot']}</div>
  {P("Как вести", ev['p_aud'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 07 Сегменты под нишу ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Предварительный аудит · Сегменты на площадках</span></div>
  <h2>{ev['seg_h2']}</h2>
  <p class="sub">Сегменты собираются из категорий каталогов 1-го и 2-го уровня, поведения (смотрят, кладут в корзину,
  покупают) и вашей базы. Ниже — стартовая гипотеза для {ev['seg_for']}; размеры аудиторий снимем в кабинетах после согласования проекта площадками.</p>
  <div class="grid3">
    <div><div class="colh">Ozon Performance<small>сегменты «покупают / смотрят категорию», Premium, B2B, свой сегмент</small></div>{seg(ev['seg_ozon'])}</div>
    <div><div class="colh">Яндекс Urban Ads<small>интерес и покупки на Маркете, сервисы Еда · Лавка · Go, доход, тарифы</small></div>{seg(ev['seg_urban'])}</div>
    <div><div class="colh">WB Media<small>DMP-сегменты: поиск, корзина, покупка по каталогу WB</small></div>{seg(ev['seg_wb'])}</div>
  </div>
  <div class="note">{ev['seg_note']}</div>
  {P("Что сказать", ev['p_seg'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 08 Бенчмарки ----------
    s.append(f"""
<section class="long">
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Предварительный аудит · Бенчмарки</span></div>
  <h2>Бенчмарки для предварительного расчёта</h2>
  <p class="sub">Средние показатели клиентов на сопровождении в направлении Click Out — и строки под сегменты вашей ниши,
  которые заполняются в аудите из рекламных кабинетов площадок.</p>
  {bench_table(ev)}
  <div class="chips">{"".join(f'<div class="chip y">{c}</div>' for c in ev['bench_facts'])}</div>
  <div class="foot">Аудитории площадок не складываются: это три разные среды, и человек может быть сразу в нескольких.
  Три источника нужны ради частоты касаний и разных сценариев показа, а не ради суммы охвата. Показатели по вашей нише уточняются после сбора бенчмарков по выбранным сегментам.</div>
  {P("Что сказать", ev['p_bench'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 09 Четыре замера ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Чем отличаемся</span></div>
  <h2>Мы доказываем, что спрос<br>создала реклама</h2>
  <p class="sub">Обычный отчёт агентства показывает показы, клики и заявки по последнему клику.
  Он не отвечает на главный вопрос собственника: <b>сколько из этих обращений пришло бы и без рекламы.</b>
  Мы отвечаем — четырьмя замерами.</p>
  {rows(ev['lift_rows'])}
  <div class="foot">Часть замеров — наш собственный контур, он доступен на любом бюджете. Исследования площадок
  (Brand Lift Study, Sales Lift, post-view отчёт) подключаются от своих порогов и работают как подтверждение
  от третьей стороны, а не от подрядчика.</div>
  {P("Что сказать", ev['p_lift'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 10 Что проверим в аудите ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Предварительный аудит · Что вы получите за 3–5 дней</span></div>
  <h2>{ev['audit_h2']}</h2>
  {rows(ev['audit_rows'])}
  <div class="yline">Замер «до» снимаем в рамках бесплатного аудита — ещё до подписания договора</div>
  {P("Что сказать", ev['p_audit'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 11 Четыре шага ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Как начинаем</span></div>
  <h2>Четыре шага, из них первый —<br>бесплатный</h2>
  <div class="cards">
    <div class="card"><h3>1 · Аудит</h3>
      <p>Бесплатно, 3–5 дней. Смотрим вашу нишу на площадках, конкурентов, стоимость входа и снимаем замер «до»:
      сколько людей сейчас ищут вас по имени.</p></div>
    <div class="card"><h3>2 · Условия теста</h3>
      <p>До старта письменно фиксируем, какой результат означает «продолжаем», а какой — «останавливаемся».
      Критерии формулируете вы, мы вносим их в договор.</p></div>
    <div class="card"><h3>3 · Тест</h3>
      <p>Тестовый период 6–8 недель: на меньшем сроке результат ещё не читается. Смотрим цифры вместе
      на 2, 4 и 6–8 неделе и на каждой встрече решаем: идём дальше, что-то меняем — либо останавливаемся.</p></div>
    <div class="card"><h3>4 · Сопровождение</h3>
      <p>Недельная и месячная отчётность, а в конце цикла — не отчёт о показах, а документ с решением:
      что дала реклама, что делать дальше и на каких цифрах это основано.</p></div>
  </div>
  <div class="yline">Точка выхода известна до входа — поэтому вход безопасен</div>
  {P("Что сказать", COMMON['p_steps'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 12 Условия ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Условия работы</span></div>
  <h2>Сопровождение: чем больше<br>источников, тем ниже цена</h2>
  <div class="price">
    <div class="p"><h3>Один источник</h3><div class="now">50 000 ₽</div><div class="per">в месяц за сопровождение</div>
      <ul><li>Ozon, Urban Ads или WB на выбор</li><li>Полный аналитический контур</li><li>Недельная и месячная отчётность</li></ul></div>
    <div class="p"><h3>Два источника</h3><div class="was">100 000 ₽</div><div class="now">80 000 ₽</div><div class="per">в месяц · скидка 20% на тестовый период</div>
      <ul><li>Любые два из трёх</li><li>Сравнение источников на ваших данных</li><li>Перераспределение бюджета между ними</li></ul></div>
    <div class="p best"><div class="tag">Максимум охвата</div><h3>Три источника</h3><div class="was">150 000 ₽</div><div class="now">90 000 ₽</div><div class="per">в месяц · скидка 40% на тестовый период</div>
      <ul><li>Ozon + Urban Ads + WB</li><li>Разные среды и сценарии показа</li><li>Частота касаний, которую не даёт один канал</li></ul></div>
  </div>
  <div class="rows" style="margin-top:26px">
    <div class="row"><div class="l">Рекламный бюджет</div><div class="r">От 120 000 ₽ в месяц на каждый источник. Это порог, ниже которого площадка не набирает объём для выводов.</div></div>
    <div class="row"><div class="l">Срок контракта</div><div class="r">От шести месяцев. Медийный эффект читается на горизонте 6–8 недель, а решения по бюджету принимаются по кварталу.</div></div>
    <div class="row"><div class="l">Что входит</div><div class="r">Ведение кампаний, креативы, аналитический контур, замеры, отчётность и документ-решение в конце цикла.</div></div>
    <div class="row"><div class="l">Ведёте сами</div><div class="r">Кабинет в агентском аккаунте Церебро с менеджерским доступом и кэшбек от квартального расхода: Ozon до 18%, Urban Ads до 13%, WB до 16%. С сопровождением кэшбек не совмещается.</div></div>
  </div>
  {P("Что сказать", COMMON['p_price'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 13 Кейсы ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Как это выглядит на практике</span></div>
  <h2>{ev['cases_h2']}</h2>
  <div class="cards">{"".join(f'<div class="card"><div class="big">{c["big"]}</div><h3>{c["h"]}</h3><p>{c["p"]}</p>{"<p class=cap>" + c["cap"] + "</p>" if c.get("cap") else ""}</div>' for c in ev['cases'])}
  </div>
  <div class="foot">Показатели по нишам разные, и мы не переносим чужой результат на ваш бизнес.
  Что можно обещать до старта — честный замер «до» и понятные условия остановки.</div>
  {P("Что сказать", ev['p_cases'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 14 Другие направления под нишу ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Если задача шире Click Out</span></div>
  <h2>{ev['dir_h2']}</h2>
  <p class="sub">{ev['dir_sub']}</p>
  {rows(ev['dir_rows'])}
  <div class="foot">Единый порог по всем направлениям — рекламный бюджет от 100 000 ₽ в месяц (кроме самостоятельного запуска на Авито от 5 000 ₽).
  Клиент — ИП или юрлицо; кабинеты и креативы принадлежат клиенту, кабинеты открытые.</div>
  {P("Как вести", ev['p_dir'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 15 Опросник ----------
    if presenter:
        opts = "".join(
            f'<option{" selected" if o == ev["source"] else ""}>{o}</option>' for o in SOURCE_OPTIONS)
        qs = "".join(
            f'<div class="fq"><div class="qq"><b>{i+1:02d}</b>{q["q"]}</div>'
            + (f'<div class="hint">{q["hint"]}</div>' if q.get("hint") else "")
            + f'<textarea class="ft" id="a{i+1}" placeholder="ответ клиента"></textarea></div>'
            for i, q in enumerate(ev["questions"]))
        xa = "".join(
            f'<div><label class="fl" for="x_{k}">{lbl}</label><select class="fs" id="x_{k}"><option value="">—</option>'
            + "".join(f"<option>{o}</option>" for o in opts_) + "</select></div>"
            for k, lbl, opts_ in ev["express"])
        s.append(f"""
<section class="long">
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Снимаем ответы прямо здесь</span></div>
  <h2>Прежде чем что-то предлагать,<br>мы разбираемся</h2>
  <p class="sub">Пять вопросов из рабочего опросника под {ev['q_for']}. Записывайте ответы своими словами — строка уйдёт
  в общую таблицу, и на созвоне вы продолжите с того же места. Полный опросник из 15 вопросов —
  <a href="https://omenikarch.github.io/qnr-page/" target="_blank" rel="noopener">omenikarch.github.io/qnr-page</a>.</p>

  <div class="form">
    <div class="fgrid">
      <div style="grid-column:span 2"><label class="fl" for="source">Выставка *</label>
        <select class="fs" id="source"><option value="">— выберите —</option>{opts}<option value="__other__">Другое — вписать</option></select>
        <input class="fi" id="source_other" placeholder="название мероприятия" style="display:none;margin-top:10px"></div>
      <div><label class="fl" for="client">Клиент *</label><input class="fi" id="client" placeholder="Название компании"></div>
      <div><label class="fl" for="site">Сайт *</label><input class="fi" id="site" placeholder="адрес посадочной — или «нет сайта»"></div>
      <div><label class="fl" for="niche">Ниша *</label><input class="fi" id="niche" placeholder="{ev['niche_placeholder']}"></div>
      <div><label class="fl" for="contact">Контакт</label><input class="fi" id="contact" placeholder="имя, должность, телефон или мессенджер"></div>
    </div>

    <div class="xa">
      <div class="xh">Экспресс-квалификация у стенда</div>
      <div class="xs">Четыре переключателя вместо длинного разговора. Итог добавится к полю «Ниша» одной строкой — по нему руководитель сразу видит, наш ли это контакт.</div>
      <div class="xgrid">{xa}</div>
    </div>

    {qs}

    <div class="fq"><div class="qq"><b>{len(ev['questions'])+1:02d}</b>Договорились о встрече</div>
      <input class="fi" id="meeting" placeholder="когда клиенту удобно — дата, время, созвон или офис"></div>

    <div style="margin-top:26px">
      <button class="send" id="send">Отправить в таблицу</button>
      <div class="st" id="status"></div>
    </div>
  </div>
  {P("Как вести · правила у стенда", ev['p_form'])}
  <div class="mark">Ц</div>
</section>""")
    else:
        s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>С чего начинаем разговор</span></div>
  <h2>Прежде чем что-то предлагать,<br>мы разбираемся</h2>
  <p class="sub">Пять вопросов, с которых начинается любой наш проект под {ev['q_for']}. Ответы на них — основа предварительного аудита:
  без них мы не считаем медиаплан и не называем цифры.</p>
  <div style="margin-top:20px;max-width:1100px">{"".join(f'<div class="q"><div class="qn">ВОПРОС {i+1:02d}</div><div class="qt">{q["q"]}</div></div>' for i, q in enumerate(ev['questions']))}</div>
  <div class="mark">Ц</div>
</section>""")

    # ---------- 16 Агентствам ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Если вы агентство или частный специалист</span></div>
  <h2>Тринадцать рекламных кабинетов<br>в одном окне</h2>
  <p class="sub">Мы не только ведём рекламу сами. Через Церебро агентства и специалисты открывают
  кабинеты своим клиентам и <b>получают часть открученного бюджета обратно — до 18%</b>.</p>
  <div class="yline" style="margin-top:26px;font-size:clamp(14px,1.35vw,19px);line-height:1.6">
  VK Ads · VK AdBlogger · Telega.in · Яндекс Директ · Telegram Ads · Яндекс Бизнес · Авито Реклама ·
  Яндекс ПромоСтраницы · SberAds · Bidfox · Hybrid · Яндекс Навигатор · Ozon Performance</div>
  <div class="cards" style="margin-top:30px">
    <div class="card"><h3>Единое окно</h3><p>Софт, в котором кабинет создаётся, доступы выдаются, а деньги перекидываются между кабинетами
      в несколько кликов. Открытие бесплатное, комиссии за пополнение нет.</p></div>
    <div class="card"><h3>Документы без нервов</h3><p>Обмен через ЭДО, закрывающие в срок. Отдельно: 3% сбора нет.</p></div>
    <div class="card"><h3>Живая поддержка</h3><p>Отвечаем по рекламе, помогаем пройти модерацию, разбираем проблемы с документами и сбоями.
      При откруте от 1,5 млн — чат с персональным менеджером.</p></div>
    <div class="card"><h3>Аудит и обучение</h3><p>Разбор кампаний практикующими специалистами: точки роста, ошибки, что менять в стратегии.
      Плюс обучающие курсы для вашей команды.</p></div>
  </div>
  {P("Как вести · агентство вместо клиента", COMMON['p_agency'])}
  <div class="mark">Ц</div>
</section>""")

    # ---------- 17 Дальше ----------
    s.append(f"""
<section>
  <div class="num">{num()}</div>
  <div class="kicker"><div class="bar"></div><span>Следующий шаг</span></div>
  <h1>Начнём с бесплатного аудита</h1>
  <p class="sub">{ev['next_sub']}</p>
  <div class="yline">Церебро Таргет · направление Click Out<br>clickout.cerebrotarget.ru · t.me/cerebro_manager</div>
  {P("Что сделать до конца дня", ev['p_next'])}
  <div class="mark">Ц</div>
</section>""")

    body = "".join(s)
    title = (f"{ev['name']} · Click Out — версия ведущего (с суфлёром)" if presenter
             else f"Церебро Click Out · {ev['name']} — {ev['client_title']}")
    scripts = ""
    if presenter:
        amap = {f"a{i+1}": q["code"] for i, q in enumerate(ev["questions"])}
        xkeys = [k for k, _, _ in ev["express"]]
        scripts = f"""
<button class="toggle" id="toggle">Суфлёр</button>
<script>
  const t = document.getElementById('toggle');
  t.addEventListener('click', () => document.body.classList.toggle('souffleur'));
  document.addEventListener('keydown', e => {{
    if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
    if (e.key === 's' || e.key === 'ы') document.body.classList.toggle('souffleur');
  }});
</script>
<script>
const WEBHOOK_URL="{WEBHOOK_URL}";
const EVENT_SOURCE={ev['source']!r};
const DRAFT_KEY="expo_draft_{ev['slug']}";
const MAP={amap!r};
const XKEYS={xkeys!r};
const FIELDS=["source","source_other","client","site","niche","contact","meeting",...Object.keys(MAP),...XKEYS.map(k=>"x_"+k)];
const KEEP=["source","source_other"];
function draftSave(){{ try{{const d={{}};FIELDS.forEach(k=>{{const e=document.getElementById(k);if(e)d[k]=e.value}});
  localStorage.setItem(DRAFT_KEY,JSON.stringify(d));}}catch(e){{}} }}
function draftLoad(){{ try{{const d=JSON.parse(localStorage.getItem(DRAFT_KEY)||"{{}}");
  FIELDS.forEach(k=>{{const e=document.getElementById(k);if(e&&d[k])e.value=d[k]}});}}catch(e){{}} }}
const srcSel=document.getElementById("source"), srcOther=document.getElementById("source_other");
function srcToggle(){{ srcOther.style.display = srcSel.value==="__other__" ? "block" : "none"; }}
srcSel.addEventListener("change",()=>{{ srcToggle(); draftSave(); }});
draftLoad(); if(!srcSel.value) srcSel.value=EVENT_SOURCE; srcToggle();
document.addEventListener("input",draftSave);
document.addEventListener("change",draftSave);
function expressLine(){{
  const parts=[]; XKEYS.forEach(k=>{{const e=document.getElementById("x_"+k); if(e&&e.value) parts.push(e.value);}});
  return parts.join(", ");
}}
document.getElementById("send").addEventListener("click",async()=>{{
  const st=document.getElementById("status"), btn=document.getElementById("send");
  const val=id=>document.getElementById(id).value.trim();
  const client=val("client"), site=val("site"); let niche=val("niche");
  const source = srcSel.value==="__other__" ? val("source_other") : srcSel.value;
  if(!source){{ st.className="st err"; st.textContent="Выберите выставку — без неё строку не разложить по мероприятиям."; srcSel.focus(); return; }}
  if(!client||!site||!niche){{ st.className="st err";
    st.textContent="Заполните «Клиент», «Сайт» и «Ниша». Нет сайта — так и напишите, это тоже ответ.";
    document.getElementById(!client?"client":(!site?"site":"niche")).focus(); return; }}
  const answers={{}}; let filled=0;
  Object.keys(MAP).forEach(id=>{{ const v=val(id); if(v){{ answers[MAP[id]]=v; filled++; }} }});
  if(!filled){{ st.className="st err"; st.textContent="Запишите хотя бы один ответ клиента."; return; }}
  const xl=expressLine(); if(xl) niche = niche + " · экспресс: " + xl;
  btn.disabled=true; st.className="st"; st.textContent="Отправляю…";
  try{{
    await fetch(WEBHOOK_URL,{{method:"POST",mode:"no-cors",headers:{{"Content-Type":"text/plain;charset=utf-8"}},
      body:JSON.stringify({{client,niche,site,contact:val("contact"),meeting:val("meeting"),
        answers,source,sentAt:new Date().toISOString()}})}});
    st.className="st ok"; st.textContent="Готово: «"+client+"» ушёл в таблицу ("+filled+" из "+Object.keys(MAP).length+" ответов). Форма очищена, выставка сохранена — можно принимать следующего.";
    FIELDS.filter(k=>KEEP.indexOf(k)===-1).forEach(k=>{{const e=document.getElementById(k); if(e) e.value="";}});
    draftSave();
  }}catch(err){{
    st.className="st err"; st.textContent="Не ушло: "+err+". Ответы сохранены в черновике — повторите при связи.";
  }}
  btn.disabled=false;
}});
</script>"""

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
{body}
{scripts}
</body>
</html>
"""


def build_hub():
    cards = "".join(
        f'<div class="card"><div class="tag">{ev["dates"]}</div><h3>{ev["name"]}</h3>'
        f'<p>{ev["hub_line"]}</p>'
        f'<p style="margin-top:14px"><a href="{ev["slug"]}/presenter.html" style="color:var(--yellow)">Версия ведущего</a> · '
        f'<a href="{ev["slug"]}/index.html" style="color:var(--yellow)">Клиентская</a></p></div>'
        for ev in EVENTS)
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Click Out · выставки сентября — октября 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<section>
  <div class="logo"><div class="sign">Ц</div><div class="nm">Церебро<br>Таргет</div></div>
  <div class="kicker"><div class="bar"></div><span>Направление Click Out · презентации под выставки</span></div>
  <h1>Четыре выставки —<br>четыре презентации</h1>
  <p class="sub">Каждая — клон базовой презентации Click Out, адаптированный под нишу площадки: ниша в цифрах, сегменты
  по Ozon, Urban Ads и WB, бенчмарки, чек-лист аудита, кейсы и опросник, который отправляет строку в общую таблицу.
  «Версия ведущего» — с суфлёром (клавиша S) и формой; «Клиентская» — для отправки ссылкой.</p>
  <div class="cards" style="margin-top:30px">{cards}</div>
  <div class="foot">Базовая презентация: <a href="presenter.html">presenter.html</a> · скрипт работы на выставке: <a href="script.html">script.html</a> ·
  полный опросник: <a href="https://omenikarch.github.io/qnr-page/">qnr-page</a> · аудиты: <a href="https://omenikarch.github.io/Preliminary_audit/">Preliminary_audit</a></div>
  <div class="mark">Ц</div>
</section>
</body>
</html>
"""


if __name__ == "__main__":
    for ev in EVENTS:
        d = ROOT / ev["slug"]
        d.mkdir(exist_ok=True)
        for presenter, fname in ((True, "presenter.html"), (False, "index.html")):
            html = build(ev, presenter=presenter)
            (d / fname).write_text(html, encoding="utf-8")
            print(f"OK {ev['slug']}/{fname} ({len(html)} bytes)")
    (ROOT / "events.html").write_text(build_hub(), encoding="utf-8")
    print("OK events.html")
