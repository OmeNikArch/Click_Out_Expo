#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Короткая версия ведущего для работы у стенда с телефона: три вкладки.
  Питч  — открытие на 30 секунд, три тезиса, цифры «если спросят», возражения, цель контакта.
  Опрос — поиск клиента по каталогу участников выбранной выставки (есть / нет в списке, данные
          подтягиваются сами), отметка «уже подходили», 4 вопроса с быстрыми ответами, отправка в таблицу.
  Карта — схема стендов по номерам: зелёный A, голубой B, оранжевый C, фиолетовый — уже были.

«Уже были» собирается из двух мест: локальный журнал отправок этого устройства (сразу после «Отправить»)
и лист «Ответы» общей таблицы (строки с этой выставкой — видно и чужие подходы, с любого устройства).
Payload формы тот же, что у полной версии (client, niche, site, contact, meeting, answers по кодам, source,
sentAt): Apps Script закрыт, новых ключей не добавляем — стенд и эшелон уходят в поле niche.

Вызывается из build.py для событий с ключом "short"; полная дека пишется рядом в presenter-full.html.
"""

import html
import json
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
SHEET_ID = "1BPelyLKYCGHItz3HPlcjZG_9Qur1SiKT9ee7SnwMPUs"

CSS = r"""
:root{--bg:#000;--card:#161616;--card2:#0d0d0d;--line:#2a2a2a;--txt:#E7E6E6;--mute:#9a9a9a;--y:#FDD101;--w:#fff;
  --A:#2fbf5b;--B:#38b6f5;--C:#f28c28;--V:#a259ff;--err:#ff8a8a;--ok:#7fe08a;
  --head:'Unbounded',Arial,sans-serif;--body:'Manrope',Arial,Helvetica,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--txt);font-family:var(--body);font-size:16px;line-height:1.45;padding-bottom:40px}
a{color:var(--y)}
b{color:var(--w)}
.top{position:sticky;top:0;z-index:30;background:rgba(0,0,0,.94);backdrop-filter:blur(6px);border-bottom:1px solid #1d1d1d}
.top .in{max-width:820px;margin:0 auto;padding:10px 16px 0}
.brand{display:flex;align-items:center;gap:10px;white-space:nowrap;font-family:var(--head);font-weight:700;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--y)}
.brand .sg{width:24px;height:24px;background:#fff;border:4px solid var(--y);color:#000;display:flex;align-items:center;justify-content:center;font-size:11px;flex:none}
.brand .ev{color:var(--mute);font-weight:500;letter-spacing:.03em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tabs{display:flex;gap:6px;margin-top:10px}
.tab{flex:1;background:none;border:0;border-bottom:3px solid transparent;color:var(--mute);font-family:var(--head);font-weight:700;font-size:13px;letter-spacing:.05em;text-transform:uppercase;padding:10px 4px 11px;cursor:pointer}
.tab.on{color:var(--w);border-bottom-color:var(--y)}
.tab .bd[hidden]{display:none}
.tab .bd{display:inline-block;min-width:18px;padding:1px 6px;margin-left:6px;border-radius:100px;background:var(--V);color:#fff;font-size:10px;vertical-align:2px}
main{max-width:820px;margin:0 auto;padding:18px 16px}
.pane{display:none}.pane.on{display:block}
h2{font-family:var(--head);font-weight:700;color:var(--w);font-size:20px;line-height:1.2;margin:4px 0 12px}
.lbl{font-family:var(--head);font-weight:700;color:var(--y);font-size:11px;letter-spacing:.1em;text-transform:uppercase;margin:22px 0 10px}
.say{background:var(--card2);border-left:5px solid var(--y);border-radius:0 14px 14px 0;padding:14px 16px;font-size:17px;line-height:1.5;color:#f1f1f1}
.hook{margin-top:10px;color:var(--y);font-weight:700}
ul.dots{list-style:none}
ul.dots li{position:relative;padding-left:18px;margin-bottom:9px}
ul.dots li:before{content:"";position:absolute;left:0;top:9px;width:7px;height:7px;background:var(--y)}
ol.goal{list-style:none;counter-reset:g}
ol.goal li{counter-increment:g;position:relative;padding:10px 12px 10px 44px;background:var(--card);border-radius:12px;margin-bottom:8px}
ol.goal li:before{content:counter(g);position:absolute;left:12px;top:9px;width:22px;height:22px;border-radius:50%;background:var(--y);color:#000;font-family:var(--head);font-weight:700;font-size:12px;display:flex;align-items:center;justify-content:center}
details.ob{background:var(--card);border-radius:12px;margin-bottom:8px}
details.ob summary{cursor:pointer;padding:12px 14px;font-weight:700;color:var(--w);list-style:none}
details.ob summary::-webkit-details-marker{display:none}
details.ob summary:after{content:"+";float:right;color:var(--y);font-family:var(--head)}
details.ob[open] summary:after{content:"–"}
details.ob p{padding:0 14px 14px;color:#d6d6d6}
.more{margin-top:24px;color:var(--mute);font-size:14px}
/* форма */
.fl{display:block;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--y);font-weight:800;margin:0 0 7px}
.fi,.fs,.ft{width:100%;background:#0f0f0f;border:1px solid var(--line);border-radius:12px;color:#fff;font-family:inherit;font-size:16px;line-height:1.45;padding:12px 14px;outline:none}
.fi:focus,.fs:focus,.ft:focus{border-color:var(--y)}
.ft{min-height:64px;resize:vertical}
.fs{-webkit-appearance:none;appearance:none;background:#0f0f0f url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' fill='%23FDD101'><path d='M2 5l5 5 5-5z'/></svg>") no-repeat right 14px center;padding-right:38px}
.fld{margin-bottom:16px}
.srch{position:relative}
.sug{position:absolute;left:0;right:0;top:100%;margin-top:4px;background:#111;border:1px solid #333;border-radius:12px;z-index:20;overflow:hidden;display:none;max-height:340px;overflow-y:auto}
.sug.on{display:block}
.sg-it{display:flex;align-items:center;gap:10px;padding:11px 12px;border-bottom:1px solid #1f1f1f;cursor:pointer}
.sg-it:last-child{border-bottom:0}
.sg-it:hover,.sg-it.act{background:#1b1b1b}
.sg-it .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#fff}
.sg-it .sd{color:var(--mute);font-size:13px;white-space:nowrap}
.pr{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;border-radius:6px;font-family:var(--head);font-weight:700;font-size:11px;color:#000;padding:0 5px;flex:none}
.pr.A{background:var(--A)}.pr.B{background:var(--B)}.pr.C{background:var(--C)}.pr.V{background:var(--V);color:#fff}
.stt{margin-top:8px;font-size:14px;line-height:1.4;min-height:20px}
.stt.ok{color:var(--ok)}.stt.no{color:var(--C)}.stt.mute{color:var(--mute)}
.stt .fix{color:var(--y);text-decoration:underline;cursor:pointer}
.cl{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:12px 0 18px;display:none}
.cl.on{display:block}
.cl .h{display:flex;gap:10px;align-items:center;font-weight:800;color:#fff;font-size:17px}
.cl .m{color:var(--mute);font-size:14px;margin-top:6px}
.cl .d{color:#cfcfcf;font-size:14px;margin-top:8px;max-height:4.3em;overflow:hidden}
.cl .d.open{max-height:none}
.cl .edit{margin-top:12px;display:none}
.cl .edit.on{display:grid;gap:10px}
.cl .lnk{margin-top:10px;font-size:13px;color:var(--mute)}
.cl .lnk span{color:var(--y);cursor:pointer;text-decoration:underline;margin-right:14px}
.seen{display:none;margin:0 0 18px;border:1px solid var(--V);background:rgba(162,89,255,.12);border-radius:14px;padding:12px 14px;font-size:14px;line-height:1.45}
.seen.on{display:block}
.seen .t{font-family:var(--head);font-weight:700;color:#d8c2ff;font-size:12px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:6px}
.seen .r+.r{margin-top:8px;padding-top:8px;border-top:1px solid rgba(162,89,255,.35)}
.newf{display:none;gap:12px;margin:0 0 18px}
.newf.on{display:grid}
.q{background:var(--card2);border:1px solid #222;border-radius:14px;padding:14px;margin-bottom:12px}
.q .qq{font-weight:800;color:#fff;font-size:16px;line-height:1.35;margin-bottom:10px}
.q .qq b{color:var(--y);font-family:var(--head);font-size:12px;margin-right:8px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.chip{background:none;border:1px solid #3a3a3a;border-radius:100px;color:var(--txt);font-family:inherit;font-size:14px;padding:7px 12px;cursor:pointer;line-height:1.2}
.chip.on{border-color:var(--y);color:#000;background:var(--y)}
.xa{display:grid;gap:14px;grid-template-columns:1fr;margin:6px 0 16px}
.send{width:100%;background:var(--y);color:#000;border:0;border-radius:14px;font-family:var(--head);font-weight:700;font-size:17px;padding:17px 20px;cursor:pointer;margin-top:6px}
.send:disabled{opacity:.5}
.st{margin-top:12px;font-size:15px;color:var(--mute);line-height:1.45}
.st.ok{color:var(--ok)}.st.err{color:var(--err)}
.queue{margin-top:8px;font-size:13px;color:var(--C)}
/* карта */
.legend{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:13px;color:var(--txt);margin-bottom:10px}
.legend i{display:inline-block;width:14px;height:14px;border-radius:4px;vertical-align:-2px;margin-right:6px}
.mapnote{color:var(--mute);font-size:13px;line-height:1.45;margin-bottom:14px}
.fbar{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.mrow{display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-top:1px solid #1a1a1a}
.mrow .rl{width:52px;flex:none;font-family:var(--head);font-weight:700;color:var(--mute);font-size:12px;padding-top:12px}
.mrow .cells{display:flex;flex-wrap:wrap;gap:6px;flex:1}
.cell{position:relative;min-width:54px;height:44px;padding:0 6px;border-radius:9px;border:0;color:#000;font-family:var(--head);font-weight:700;font-size:12px;cursor:pointer;display:flex;align-items:center;justify-content:center}
.cell.A{background:var(--A)}.cell.B{background:var(--B)}.cell.C{background:var(--C)}
.cell.V{background:var(--V);color:#fff}
.cell.dim{opacity:.22}
.cell.top:after{content:"★";position:absolute;top:1px;right:4px;font-size:9px}
.cell .n{position:absolute;bottom:1px;right:4px;font-size:9px}
.pop{position:fixed;left:0;right:0;bottom:0;z-index:40;background:#121212;border-top:2px solid var(--y);border-radius:18px 18px 0 0;padding:16px 16px 22px;max-height:70vh;overflow-y:auto;transform:translateY(105%);transition:transform .18s}
.pop.on{transform:none}
.pop .x{float:right;background:none;border:0;color:var(--mute);font-size:26px;line-height:1;cursor:pointer}
.pop .it{padding:10px 0;border-top:1px solid #222}
.pop .it:first-of-type{border-top:0}
.pop .ttl{display:flex;gap:8px;align-items:center;font-weight:800;color:#fff}
.pop .m{color:var(--mute);font-size:13px;margin-top:4px}
.pop .v{color:#d8c2ff;font-size:13px;margin-top:6px}
.pop .go{margin-top:10px;background:var(--y);color:#000;border:0;border-radius:10px;font-family:var(--head);font-weight:700;font-size:13px;padding:10px 14px;cursor:pointer}
.route{margin-top:20px}
.route .it{display:flex;gap:10px;align-items:center;padding:9px 0;border-top:1px solid #1a1a1a;cursor:pointer}
.route .it .s{font-family:var(--head);font-weight:700;font-size:12px;color:var(--mute);width:52px;flex:none}
.route .it .nm{flex:1;color:#fff}
.sync{font-size:12px;color:var(--mute);margin-top:6px}
@media (min-width:640px){.xa{grid-template-columns:1fr 1fr}.newf.on{grid-template-columns:1fr 1fr}h2{font-size:24px}}
"""

PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#000000">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&family=Manrope:wght@400;600;800&display=swap" rel="stylesheet">
<style>__CSS__</style>
</head>
<body>
<header class="top"><div class="in">
  <div class="brand"><div class="sg">Ц</div><span>Click Out</span><span class="ev">__EVCHIP__</span></div>
  <nav class="tabs">
    <button class="tab" data-t="pitch">Питч</button>
    <button class="tab" data-t="form">Опрос</button>
    <button class="tab" data-t="map">Карта<span class="bd" id="bdV" hidden>0</span></button>
  </nav>
</div></header>
<main>

<section class="pane" id="p-pitch">
  <h2>Питч за минуту</h2>
  <div class="lbl">Открытие · 30 секунд</div>
  <div class="say">__OPENER__<div class="hook">__HOOK__</div></div>
  <div class="lbl">Три тезиса</div>
  <ul class="dots">__VALUE__</ul>
  <div class="lbl">Цель контакта — договориться</div>
  <ol class="goal">__GOAL__</ol>
  <div class="lbl">Возражения</div>
  __OBJ__
  <div class="lbl">Если спросят</div>
  <ul class="dots">__FACTS__</ul>
  <p class="more">Полная дека с суфлёром: <a href="presenter-full.html">presenter-full.html</a> · клиенту ссылкой: <a href="index.html">index.html</a> ·
  участники списком: <a href="exhibitors.html">exhibitors.html</a></p>
__PITCHALT__
</section>

<section class="pane" id="p-form">
  <h2>Опрос у стенда</h2>
__MGRHTML__
  <div class="fld"><label class="fl" for="source">Выставка</label>
    <select class="fs" id="source">__SRC_OPTS__<option value="__other__">Другое — вписать</option></select>
    <input class="fi" id="source_other" placeholder="название мероприятия" style="display:none;margin-top:8px"></div>

  <div class="fld srch"><label class="fl" for="client">Клиент *</label>
    <input class="fi" id="client" placeholder="начните писать название" autocomplete="off" autocapitalize="off" spellcheck="false">
    <div class="sug" id="sug"></div>
    <div class="stt mute" id="cstat"></div>
  </div>

  <div class="seen" id="seen"></div>

  <div class="cl" id="card">
    <div class="h" id="cardH"></div>
    <div class="m" id="cardM"></div>
    <div class="d" id="cardD"></div>
    <div class="lnk"><span id="cardMore">описание целиком</span><span id="cardEdit">поправить сайт / нишу</span><span id="cardClear">другой клиент</span></div>
    <div class="edit" id="cardEditBox">
      <div><label class="fl" for="site">Сайт</label><input class="fi" id="site"></div>
      <div><label class="fl" for="niche">Ниша</label><input class="fi" id="niche"></div>
    </div>
  </div>

  <div class="newf" id="newf">
    <div><label class="fl" for="site_new">Сайт</label><input class="fi" id="site_new" placeholder="адрес или «нет сайта»" autocapitalize="off"></div>
    <div><label class="fl" for="niche_new">Ниша</label><input class="fi" id="niche_new" placeholder="__NICHE_PH__"></div>
  </div>

  __QS__

  <div class="xa">__XA__</div>

  <div class="fld"><label class="fl" for="contact">Контакт</label>
    <input class="fi" id="contact" placeholder="имя, должность, телефон или Telegram"></div>
  <div class="fld"><label class="fl" for="meeting">Договорились</label>
    <div class="chips" data-for="meeting">__MCHIPS__</div>
    <input class="fi" id="meeting" placeholder="что и когда — дата созвона или встречи"></div>
  <div class="fld"><label class="fl" for="comment">Комментарий (необязательно)</label>
    <textarea class="ft" id="comment" placeholder="например: передать Никите, клиент не на маркетплейсах"></textarea></div>

  <button class="send" id="send">Отправить в таблицу</button>
  <div class="st" id="status"></div>
  <div class="queue" id="queue" hidden></div>
</section>

<section class="pane" id="p-map">
  <h2>Карта стендов</h2>
__MAPLINK__
  <div class="legend"><span><i style="background:var(--A)"></i>Эшелон A</span><span><i style="background:var(--B)"></i>Эшелон B</span>
    <span><i style="background:var(--C)"></i>Эшелон C</span><span><i style="background:var(--V)"></i>Уже были</span><span>★ — идти первыми</span></div>
  <div class="mapnote" id="mapnote"></div>
  <div class="fbar" id="fbar">
    <button class="chip on" data-m="all">все</button><button class="chip" data-m="A">A</button><button class="chip" data-m="B">B</button>
    <button class="chip" data-m="C">C</button>__SEGCHIPS__<button class="chip" data-m="left">ещё не были</button><button class="chip" data-m="V">уже были</button></div>
  <div id="map"></div>
  <div class="route"><div class="lbl">Маршрут: A и ★, где ещё не были</div><div id="route"></div></div>
  <div class="sync" id="sync"></div>
</section>
</main>

<div class="pop" id="pop"></div>

<script>
const WEBHOOK_URL=__WEBHOOK__;
const SHEET_CSV="https://docs.google.com/spreadsheets/d/__SHEET__/gviz/tq?tqx=out:csv&sheet="+encodeURIComponent("Ответы")+"&tq="+encodeURIComponent("select A,B,C,D,T,U,V");
const EVENT_SOURCE=__EVENT_SOURCE__;
const LISTS=__LISTS__;
const EMBED={source:__EVENT_SOURCE__,rows:__EMBED__};
__SEGDICTS__
const QCODES=__QCODES__;
const XKEYS=__XKEYS__;
const DRAFT_KEY="expo_short_draft___SLUG__", VISIT_KEY="expo_visits", OUTBOX_KEY="expo_outbox";

/* ---------- утилиты ---------- */
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const LS={get(k,d){try{const v=localStorage.getItem(k);return v?JSON.parse(v):d}catch(e){return d}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
const TR={"а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z","и":"i","й":"i","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"c","ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya"};
const STOP=/\\b(ооо|оао|зао|пао|ао|ип|гк|group|llc|ltd|сеть|компания|франшиза|franchise)\\b/g;
function norm(s){return String(s||"").toLowerCase().replace(/ё/g,"е").replace(/[«»"'`’“”]/g," ").replace(STOP," ").replace(/[^a-zа-я0-9]+/g," ").trim();}
function tr(s){return s.replace(/[а-я]/g,c=>TR[c]||c).replace(/kh/g,"h").replace(/[wv]/g,"v").replace(/ph/g,"f").replace(/x/g,"ks").replace(/ck/g,"k").replace(/q/g,"k").replace(/y/g,"i").replace(/j/g,"i");}
function key(s){return tr(norm(s)).replace(/ /g,"");}
function host(u){return String(u||"").toLowerCase().replace(/^\\s*https?:\\/\\//,"").replace(/^www\\./,"").replace(/[\\/?#].*$/,"").trim();}
function cleanSite(u){u=String(u||"").trim();return u.replace(/[?#].*$/,"").replace(/\\/$/,"");}
function grams(s){const g=new Set();s=" "+s+" ";for(let i=0;i<s.length-1;i++)g.add(s.slice(i,i+2));return g;}
function dice(a,b){if(!a||!b)return 0;const A=grams(a),B=grams(b);let n=0;A.forEach(x=>{if(B.has(x))n++});return 2*n/(A.size+B.size);}
const srcKey=s=>String(s||"").split(/[·+]/)[0].trim().toLowerCase();

/* ---------- стенды ---------- */
const HOMO={"А":"A","В":"B","С":"C","Е":"E","Н":"H","К":"K","М":"M","О":"O","Р":"P","Т":"T","Х":"X"};
function parseStand(s){
  let first=String(s||"").split(/[,;]/)[0];
  if(first.indexOf("·")>=0){const p=first.split("·");first=p[0].trim()+p[p.length-1].trim();}
  const code=first.toUpperCase().replace(/[АВСЕНКМОРТХ]/g,c=>HOMO[c]).replace(/\\s+/g,"");
  const m=code.match(/^(\\d*)([A-Z]+)-?(\\d+)/);
  if(!m) return {code:code||"—",row:"—",n:9999};
  const n=parseInt(m[3],10);
  const row=m[1]+m[2]+(n>=100?"·"+Math.floor(n/100):"");
  return {code,row,n};
}

/* ---------- каталог выбранной выставки ---------- */
let ROWS=[], CUR_SRC="";
function prep(rows){return rows.map((r,i)=>{const st=parseStand(r.stand);return {i,name:r.name,stand:r.stand||"",code:st.code,row:st.row,n:st.n,
  site:r.site||"",prio:r.prio||"C",top:!!r.top,hall:r.hall||"",meta:r.meta||"",tags:r.tags||[],descr:r.descr||"",
__PREPSEG__
  k:key(r.name),nw:norm(r.name),tw:tr(norm(r.name)),h:host(r.site)}});}
async function loadList(src){
  CUR_SRC=src; ROWS=[];
  if(src===EMBED.source){ROWS=prep(EMBED.rows);}
  else if(LISTS[src]){
    try{const r=await fetch(LISTS[src]);ROWS=prep(await r.json());}catch(e){ROWS=[];}
  }
  if(CUR_SRC!==src) return;
  onClientInput(); renderMap(); renderSeen();
}

/* ---------- кто уже был: журнал устройства + таблица ---------- */
let SHEET=[], SHEET_AT=null, SHEET_ERR="";
function parseCSV(t){const out=[];let row=[],f="",q=false;for(let i=0;i<t.length;i++){const c=t[i];
  if(q){if(c==='"'){if(t[i+1]==='"'){f+='"';i++;}else q=false;}else f+=c;}
  else if(c==='"')q=true; else if(c===","){row.push(f);f="";} else if(c==="\\n"){row.push(f);out.push(row);row=[];f="";} else if(c!=="\\r")f+=c;}
  if(f||row.length){row.push(f);out.push(row);}return out;}
async function loadSheet(){
  try{const r=await fetch(SHEET_CSV,{cache:"no-store"});if(!r.ok)throw new Error(r.status);
    const rows=parseCSV(await r.text()).slice(1);
    SHEET=rows.filter(r=>r[1]).map(r=>({date:r[0],client:r[1],niche:r[2],site:r[3],contact:r[4],meeting:r[5],source:r[6],from:"таблица"}));
    SHEET_AT=new Date(); SHEET_ERR="";
  }catch(e){SHEET_ERR="таблица недоступна — показываю отметки этого устройства";}
  renderMap(); renderSeen(); onClientInput(true);
}
function visitsFor(src){
  const sk=srcKey(src);
  const loc=LS.get(VISIT_KEY,[]).filter(v=>srcKey(v.source)===sk).map(v=>Object.assign({from:"это устройство"},v));
  const sh=SHEET.filter(v=>srcKey(v.source)===sk || (sk && String(v.source).toLowerCase().indexOf(sk)>=0));
  return loc.concat(sh);
}
function sameClient(v,r){
  const vk=key(v.client), vh=host(v.site);
  if(v.stand && r.stand && v.client===r.name) return true;
  if(vk && vk===r.k) return true;
  if(vh && r.h && vh===r.h) return true;
  if(vk.length>=4 && r.k.length>=4 && (vk.indexOf(r.k)>=0 || r.k.indexOf(vk)>=0)) return true;
  return false;
}
function visitsOf(r){return visitsFor(CUR_SRC).filter(v=>sameClient(v,r));}
function fmtDate(s){
  if(!s) return "";
  let m=String(s).match(/^(\\d{1,2})\\/(\\d{1,2})\\/(\\d{4})(?:\\s+(\\d{1,2}):(\\d{2}))?/);
  if(m) return m[2].padStart(2,"0")+"."+m[1].padStart(2,"0")+(m[4]?" "+m[4].padStart(2,"0")+":"+m[5]:"");
  const d=new Date(s); if(!isNaN(d)) return d.toLocaleString("ru-RU",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
  return String(s);
}
function seenHTML(vs){return vs.map(v=>`<div class="r"><b>${esc(fmtDate(v.date||v.t))}</b> · ${esc(v.from)}${v.contact?` · ${esc(v.contact)}`:""}${v.meeting?`<br>Договорились: ${esc(v.meeting)}`:""}</div>`).join("");}

/* ---------- поиск клиента ---------- */
let SEL=null, ACT=-1, SUGG=[];
function score(q,r){
  const qn=norm(q), qt=tr(qn), qk=qt.replace(/ /g,"");
  if(!qk) return 0;
  if(r.k===qk) return 100;
  if(r.nw.startsWith(qn)||r.tw.startsWith(qt)) return 80;
  if((" "+r.nw).indexOf(" "+qn)>=0||(" "+r.tw).indexOf(" "+qt)>=0) return 65;
  if(r.k.indexOf(qk)>=0) return 50;
  /* сайт: домен сравниваем в той же транслитерации, что и запрос (dkhoon → dhoon), и по отдельным словам */
  const hk=r.h?tr(r.h).replace(/[^a-z0-9]/g,""):"", hb=hk.replace(/(com|ru|ae|net|org|pro|shop|store|info)$/,"");
  if(hk && qk.length>=3 && (hk.indexOf(qk)>=0 || (hb.length>=5 && qk.indexOf(hb)>=0))) return 45;
  if(hk && qt.split(" ").some(w=>w.length>=4 && hk.indexOf(w)>=0)) return 40;
  const d=Math.max(dice(qk,r.k), ...r.tw.split(" ").map(w=>dice(qk,w)));
  return d>=.45?Math.round(d*40):0;
}
function onClientInput(keep){
  const q=$("client").value;
  if(SEL && q!==SEL.name){SEL=null;}
  renderCard();
  const st=$("cstat");
  if(!q.trim()){st.className="stt mute";st.textContent=ROWS.length?`В каталоге ${ROWS.length} участников — начните писать название`:"Для этой выставки каталога нет — впишите клиента вручную";hideSug();renderSeen();return;}
  if(SEL){st.className="stt ok";st.textContent=`✓ Есть в списке участников · стенд ${SEL.stand||"—"} · эшелон ${SEL.prio}${SEL.top?" ★":""}`;hideSug();renderSeen();return;}
  SUGG=ROWS.map(r=>[score(q,r),r]).filter(x=>x[0]>0).sort((a,b)=>b[0]-a[0]).slice(0,7).map(x=>x[1]);
  const exact=SUGG.find(r=>r.k===key(q));
  if(exact && !keep){pick(exact);return;}
  if(!ROWS.length){st.className="stt mute";st.textContent="Каталога участников нет — клиент уйдёт как новый";}
  else if(SUGG.length){st.className="stt no";st.innerHTML=`Точного совпадения нет — выберите из списка или <span class="fix" id="asNew">оставить как новый клиент</span>`;}
  else {st.className="stt no";st.textContent="✗ Нет в списке участников — проверьте написание. Если всё верно, заполните сайт и нишу ниже.";}
  if(document.activeElement===$("client")) showSug();
  $("newf").classList.toggle("on", !SEL);
  renderSeen();
}
function showSug(){
  const box=$("sug"); ACT=-1;
  if(!SUGG.length){hideSug();return;}
  box.innerHTML=SUGG.map((r,i)=>{const v=visitsOf(r).length;return `<div class="sg-it" data-i="${i}"><span class="pr ${r.prio}">${r.prio}</span><span class="nm">${esc(r.name)}${r.top?" ★":""}</span>${v?'<span class="pr V">был</span>':""}<span class="sd">${esc(r.stand||"")}</span></div>`}).join("");
  box.classList.add("on");
}
function hideSug(){$("sug").classList.remove("on");}
function pick(r){
  SEL=r; $("client").value=r.name;
  $("site").value=cleanSite(r.site);
  $("niche").value=[r.hall, r.meta].filter(Boolean).join(" · ");
  hideSug(); onClientInput(); draftSave();
}
function renderCard(){
  const c=$("card");
  if(!SEL){c.classList.remove("on");$("newf").classList.toggle("on", !!$("client").value.trim());return;}
  $("newf").classList.remove("on");
  c.classList.add("on");
  const r=SEL;
  $("cardH").innerHTML=`<span class="pr ${r.prio}">${r.prio}</span>${esc(r.name)}${r.top?" ★":""}`;
__CARDM__
__CARDD__
}
function renderSeen(){
  const box=$("seen"); let vs=[];
  if(SEL) vs=visitsOf(SEL);
  else {const qk=key($("client").value); if(qk.length>=3) vs=visitsFor(CUR_SRC).filter(v=>{const k=key(v.client);return k===qk||(qk.length>=4&&k.length>=4&&(k.indexOf(qk)>=0||qk.indexOf(k)>=0));});}
  if(!vs.length){box.classList.remove("on");box.innerHTML="";return;}
  box.innerHTML=`<div class="t">Уже подходили — ${vs.length} ${vs.length===1?"раз":"раза"}</div>`+seenHTML(vs);
  box.classList.add("on");
}
$("client").addEventListener("input",()=>{onClientInput();draftSave();});
$("client").addEventListener("focus",()=>{if(!SEL&&SUGG.length)showSug();});
$("client").addEventListener("blur",()=>setTimeout(hideSug,180));
$("client").addEventListener("keydown",e=>{
  const its=[...$("sug").querySelectorAll(".sg-it")]; if(!its.length) return;
  if(e.key==="ArrowDown"||e.key==="ArrowUp"){e.preventDefault();ACT=(ACT+(e.key==="ArrowDown"?1:-1)+its.length)%its.length;its.forEach((x,i)=>x.classList.toggle("act",i===ACT));}
  else if(e.key==="Enter"&&ACT>=0){e.preventDefault();pick(SUGG[ACT]);}
});
$("sug").addEventListener("mousedown",e=>{const it=e.target.closest(".sg-it");if(it){e.preventDefault();pick(SUGG[+it.dataset.i]);}});
$("cstat").addEventListener("click",e=>{if(e.target.id==="asNew"){SUGG=[];hideSug();$("cstat").className="stt no";$("cstat").textContent="Новый клиент — не из каталога. Впишите сайт и нишу, если знаете.";$("newf").classList.add("on");}});
$("cardMore").addEventListener("click",()=>$("cardD").classList.toggle("open"));
$("cardEdit").addEventListener("click",()=>$("cardEditBox").classList.toggle("on"));
$("cardClear").addEventListener("click",()=>{SEL=null;$("client").value="";$("site").value="";$("niche").value="";onClientInput();$("client").focus();draftSave();});

/* ---------- быстрые ответы ---------- */
document.querySelectorAll(".chips[data-for]").forEach(box=>{
  const ta=$(box.dataset.for), single=box.dataset.single==="1";
  box.addEventListener("click",e=>{
    const b=e.target.closest(".chip"); if(!b) return;
    const t=b.dataset.v;
    if(single){box.querySelectorAll(".chip").forEach(x=>{if(x!==b)x.classList.remove("on")});b.classList.toggle("on");ta.value=b.classList.contains("on")?t:"";draftSave();return;}
    const parts=ta.value.split(/;\\s*/).map(s=>s.trim()).filter(Boolean);
    const i=parts.indexOf(t);
    if(i>=0){parts.splice(i,1);b.classList.remove("on");} else {parts.push(t);b.classList.add("on");}
    ta.value=parts.join("; ")+(t.endsWith(":")&&i<0?" ":"");
    if(t.endsWith(":")&&i<0){ta.focus();ta.setSelectionRange(ta.value.length,ta.value.length);}
    draftSave();
  });
  ta.addEventListener("input",()=>syncChips(box));
});
function syncChips(box){const ta=$(box.dataset.for);const parts=ta.value.split(/;\\s*/).map(s=>s.trim());
  box.querySelectorAll(".chip").forEach(b=>b.classList.toggle("on",parts.indexOf(b.dataset.v.replace(/:$/,":"))>=0||(box.dataset.single==="1"&&ta.value===b.dataset.v)));}

/* ---------- черновик ---------- */
const FIELDS=["source","source_other","client","site","niche","site_new","niche_new","contact","meeting","comment",...Object.keys(QCODES),...XKEYS.map(k=>"x_"+k)];
function draftSave(){const d={};FIELDS.forEach(k=>{const e=$(k);if(e)d[k]=e.value});d._sel=SEL?SEL.name:"";LS.set(DRAFT_KEY,d);}
function draftLoad(){const d=LS.get(DRAFT_KEY,{});FIELDS.forEach(k=>{const e=$(k);if(e&&d[k])e.value=d[k]});return d;}
document.addEventListener("input",e=>{if(e.target.id!=="client")draftSave();});

/* ---------- отправка с очередью (у стендов бывает без связи) ---------- */
function outbox(){return LS.get(OUTBOX_KEY,[]);}
function showQueue(){const n=outbox().length;const q=$("queue");q.hidden=!n;q.textContent=n?`В очереди на отправку: ${n} — уйдут сами, когда появится связь`:"";}
/* Таблица читает текст с «+ = - @» в начале как формулу (+7… → #ERROR!) — апостроф делает его текстом */
const asText=v=>typeof v==="string"?(/^[-=+@]/.test(v.trim())?"'"+v.trim():v):(v&&typeof v==="object"?Object.fromEntries(Object.entries(v).map(([k,x])=>[k,asText(x)])):v);
async function post(p){await fetch(WEBHOOK_URL,{method:"POST",mode:"no-cors",headers:{"Content-Type":"text/plain;charset=utf-8"},body:JSON.stringify(asText(p))});}
async function flush(){
  let q=outbox(); if(!q.length) return;
  const rest=[];
  for(const p of q){try{await post(p);}catch(e){rest.push(p);}}
  LS.set(OUTBOX_KEY,rest); showQueue();
  if(rest.length<q.length) setTimeout(loadSheet,6000);
}
window.addEventListener("online",flush);
const val=id=>($(id)?$(id).value.trim():"");
$("send").addEventListener("click",async()=>{
  const st=$("status"), btn=$("send");
  const source=$("source").value==="__other__"?val("source_other"):$("source").value;
  const client=val("client");
  if(!source){st.className="st err";st.textContent="Выберите выставку.";$("source").focus();return;}
  if(!client){st.className="st err";st.textContent="Впишите клиента.";$("client").focus();return;}
  const answers={}; let filled=0;
  Object.keys(QCODES).forEach(id=>{const v=val(id);if(v){answers[QCODES[id]]=v;filled++;}});
  if(!filled && !val("contact") && !val("meeting")){st.className="st err";st.textContent="Запишите хоть что-то: ответ, контакт или договорённость.";return;}
  const site=SEL?(val("site")||cleanSite(SEL.site)):(val("site_new")||"не записан");
  let niche=SEL?val("niche"):val("niche_new");
  const tags=[];
  if(SEL){tags.push("стенд "+(SEL.stand||"—"),"эшелон "+SEL.prio+(SEL.top?"★":""));} else if(ROWS.length) tags.push("нет в каталоге");
  const xl=XKEYS.map(k=>val("x_"+k)).filter(Boolean);
  const comment=val("comment");
  niche=[niche||"не записана"].concat(tags).join(" · ")+(xl.length?" · экспресс: "+xl.join(", "):"")+(comment?" · комментарий: "+comment:"");
  const p={client,niche,site,contact:val("contact"),meeting:val("meeting"),answers,source,sentAt:new Date().toISOString()};
  btn.disabled=true; st.className="st"; st.textContent="Отправляю…";
  const vs=LS.get(VISIT_KEY,[]); vs.push({client,stand:SEL?SEL.stand:"",site,source,t:p.sentAt,contact:p.contact,meeting:p.meeting}); LS.set(VISIT_KEY,vs);
  let queued=false;
  try{await post(p);}catch(e){const q=outbox();q.push(p);LS.set(OUTBOX_KEY,q);queued=true;}
  st.className=queued?"st err":"st ok";
  st.textContent=queued?`Связи нет: «${client}» в очереди, уйдёт сам. Стенд уже отмечен фиолетовым.`
                       :`Готово: «${client}» в таблице (${filled} из ${Object.keys(QCODES).length} ответов). Стенд отмечен фиолетовым на карте.`;
  FIELDS.filter(k=>k!=="source"&&k!=="source_other").forEach(k=>{const e=$(k);if(e)e.value="";});
  document.querySelectorAll(".chip.on").forEach(b=>{if(!b.dataset.m)b.classList.remove("on")});
  SEL=null; onClientInput(); draftSave(); showQueue(); renderMap(); renderSeen();
  btn.disabled=false;
  if(!queued) setTimeout(loadSheet,6000);
});

/* ---------- карта ---------- */
let MF="all";
function renderMap(){
  const vis=r=>visitsOf(r).length>0;
  const groups={}; let nV=0;
  ROWS.forEach(r=>{const g=r.row+"|"+r.code;(groups[g]=groups[g]||{row:r.row,code:r.code,n:r.n,items:[]}).items.push(r);});
  const cells=Object.values(groups);
  const rows={};
  cells.forEach(c=>{
    c.v=c.items.some(vis); if(c.v) nV++;
    c.prio=c.items.map(r=>r.prio).sort()[0]; c.top=c.items.some(r=>r.top);
    (rows[c.row]=rows[c.row]||[]).push(c);
  });
  const vCount=ROWS.filter(vis).length;
  const bd=$("bdV"); bd.hidden=!vCount; bd.textContent=vCount;
  const show=c=>MF==="all"||(MF==="V"?c.v:MF==="left"?!c.v:__SEGSHOW__(c.prio===MF||c.items.some(r=>r.prio===MF)));
  const keys=Object.keys(rows).sort((a,b)=>a==="—"?1:b==="—"?-1:a.localeCompare(b,"en",{numeric:true}));
  $("map").innerHTML=ROWS.length?keys.map(k=>`<div class="mrow"><div class="rl">${esc(k.replace("·"," ")+(k.indexOf("·")>=0?"xx":""))}</div><div class="cells">${
    rows[k].sort((a,b)=>a.n-b.n).map(c=>`<button class="cell ${c.v?"V":c.prio}${c.top?" top":""}${show(c)?"":" dim"}" data-g="${esc(c.row+"|"+c.code)}">${esc(c.code==="—"?"?":c.code)}${c.items.length>1?`<span class="n">×${c.items.length}</span>`:""}</button>`).join("")
  }</div></div>`).join(""):'<p class="mapnote">Для этой выставки каталога участников нет.</p>';
  $("map").groups=groups;
__MAPC__
__MAPSEGLINE__
  $("mapnote").innerHTML=ROWS.length?`${ROWS.length} участников: A — ${c.A||0}, B — ${c.B||0}, C — ${c.C||0}.__SEGNOTE__ Уже были: <b>${vCount}</b>. Схема разложена по номерам стендов (ряд = буква и сотня номера): официальный план зала организатор не публикует, так что это ориентир по рядам, а не чертёж.`:"";
  const route=ROWS.filter(r=>(r.prio==="A"||r.top)&&!vis(r)).sort((a,b)=>(b.top-a.top)||a.row.localeCompare(b.row,"en",{numeric:true})||a.n-b.n);
  $("route").innerHTML=route.length?route.map(r=>`<div class="it" data-i="${r.i}"><span class="s">${esc(r.stand||"—")}</span><span class="pr ${r.prio}">${r.prio}</span><span class="nm">${esc(r.name)}${r.top?" ★":""}</span></div>`).join(""):'<p class="mapnote">Все из эшелона A пройдены.</p>';
  $("sync").textContent=SHEET_ERR||(SHEET_AT?`Отметки из таблицы обновлены в ${SHEET_AT.toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"})}; обновляются раз в полторы минуты.`:"Загружаю отметки из таблицы…");
}
$("fbar").addEventListener("click",e=>{const b=e.target.closest(".chip");if(!b)return;MF=b.dataset.m;$("fbar").querySelectorAll(".chip").forEach(x=>x.classList.toggle("on",x===b));renderMap();});
function openPop(items){
  $("pop").innerHTML=`<button class="x" id="popX">×</button>`+items.map(r=>{const vs=visitsOf(r);return `<div class="it"><div class="ttl"><span class="pr ${r.prio}">${r.prio}</span>${esc(r.name)}${r.top?" ★":""}</div>
__POPM__
__POPV__
    ${vs.length?`<div class="v">Уже были: ${vs.map(v=>esc(fmtDate(v.date||v.t))+(v.meeting?" — "+esc(v.meeting):"")).join("; ")}</div>`:""}
    <button class="go" data-i="${r.i}">${vs.length?"Ещё раз к ним — открыть опрос":"Подойти — открыть опрос"}</button></div>`}).join("");
  $("pop").classList.add("on");
}
$("map").addEventListener("click",e=>{const b=e.target.closest(".cell");if(!b)return;openPop($("map").groups[b.dataset.g].items);});
$("route").addEventListener("click",e=>{const it=e.target.closest(".it");if(it)openPop([ROWS[+it.dataset.i]]);});
$("pop").addEventListener("click",e=>{
  if(e.target.id==="popX"){$("pop").classList.remove("on");return;}
  const g=e.target.closest(".go"); if(g){$("pop").classList.remove("on");pick(ROWS[+g.dataset.i]);showTab("form");window.scrollTo(0,0);}
});

/* ---------- вкладки ---------- */
function showTab(t){
  document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("on",x.dataset.t===t));
  document.querySelectorAll(".pane").forEach(x=>x.classList.toggle("on",x.id==="p-"+t));
  try{sessionStorage.setItem("expo_tab",t)}catch(e){}
  if(t==="map"&&(!SHEET_AT||Date.now()-SHEET_AT>30000)) loadSheet();
}
document.querySelectorAll(".tab").forEach(x=>x.addEventListener("click",()=>showTab(x.dataset.t)));

__MGRJS__
/* ---------- старт ---------- */
const srcSel=$("source"), srcOther=$("source_other");
function srcToggle(){srcOther.style.display=srcSel.value==="__other__"?"block":"none";}
srcSel.addEventListener("change",()=>{srcToggle();SEL=null;draftSave();loadList(srcSel.value);});
const d=draftLoad(); if(!srcSel.value) srcSel.value=EVENT_SOURCE; srcToggle();
document.querySelectorAll(".chips[data-for]").forEach(syncChips);
/* ссылка с карты залов: presenter.html?c=<клиент>&s=<стенд> — сразу опрос по этому клиенту */
const UP=new URLSearchParams(location.search), UPC=(UP.get("c")||"").trim();
if(UPC&&srcSel.value!==EVENT_SOURCE){srcSel.value=EVENT_SOURCE;srcToggle();}
loadList(srcSel.value).then(()=>{
  if(UPC){const s=UP.get("s")||"";const r=ROWS.find(x=>x.name===UPC&&(!s||x.stand===s))||ROWS.find(x=>x.name===UPC);
    if(r) pick(r); else {SEL=null;$("client").value=UPC;onClientInput(true);draftSave();}
    history.replaceState(null,"",location.pathname);return;}
  if(d._sel){const r=ROWS.find(x=>x.name===d._sel); if(r){SEL=r; onClientInput(true);}} });
let tab="form"; try{tab=sessionStorage.getItem("expo_tab")||"pitch"}catch(e){tab="pitch"}
if(UPC) tab="form";
showTab(tab);
showQueue(); flush(); loadSheet();
setInterval(()=>{if(!document.hidden) loadSheet();},90000);
document.addEventListener("visibilitychange",()=>{if(!document.hidden){loadSheet();flush();}});
</script>
</body>
</html>
"""


# Варианты seg-блоков короткой версии. has_seg=False (BUYBRAND, ПаркЗоо, Дентал-Экспо и др.) —
# вывод ОБЯЗАН оставаться байт-в-байт как до появления сегментов; has_seg=True без ev["seg_ui"] —
# прежние общие тексты; InterCHARM передаёт ev["seg_ui"] с текстами правил Никиты от 13.10.2026.
SEG_NONE = {
    "dicts": "", "chips": "", "show": "", "mapc": '  const c={A:0,B:0,C:0}; ROWS.forEach(r=>c[r.prio]=(c[r.prio]||0)+1);',
    "mapsegline": "", "segnote": "", "prepseg": "", "popv": "",
    "cardm": '  $("cardM").innerHTML=[`стенд ${esc(r.stand||"—")}`, esc(r.hall), esc(r.meta), r.site?`<a href="${esc(r.site.startsWith("http")?r.site:"http://"+r.site)}" target="_blank" rel="noopener">${esc(r.h)}</a>`:"сайта нет"].filter(Boolean).join(" · ");',
    "cardd": '  $("cardD").textContent=r.descr||""; $("cardD").classList.remove("open");',
    "popm": '    <div class="m">стенд ${esc(r.stand||"—")} · ${esc([r.hall,r.meta].filter(Boolean).join(" · "))}</div>',
}
SEG_OLD = {
    "dicts": ('const SEG_LABELS={clickout:"Никита · Click Out",mp:"Андрей · внешний трафик",both:"Оба: Андрей + Никите тоже",none:"Никому",unknown:"Не определено"};\n'
              'const SEG_PITCH={clickout:"Питч: Click Out — реклама на маркетплейсах ведёт на собственный сайт/магазин/запись.",mp:"Питч: внешний трафик из Директа, ЯПС и VK на карточки/брендовые листинги маркетплейсов.",both:"Основной владелец Андрей: компания на маркетплейсах. Есть свой магазин — Никите тоже.",none:"Низкий приоритет: нет своего канала продаж и маркетплейсов.",unknown:"Проверить у стенда: есть ли собственный заказ и/или карточки на маркетплейсах."};'),
    "chips": '<button class="chip" data-m="clickout">Никита</button><button class="chip" data-m="mp">Андрей</button><button class="chip" data-m="both">оба</button><button class="chip" data-m="unknown">не определено</button>',
    "show": '["clickout","mp","both","unknown","none"].includes(MF)?c.items.some(r=>r.seg===MF):',
    "line": ' Никита — ${s.clickout||0}, Андрей — ${s.mp||0}, оба — ${s.both||0}, не определено — ${s.unknown||0}.',
}
SEG_COMMON = {
    "mapc": '  const c={A:0,B:0,C:0}, s={clickout:0,mp:0,both:0,unknown:0,none:0}; ROWS.forEach(r=>{c[r.prio]=(c[r.prio]||0)+1;if(r.seg)s[r.seg]=(s[r.seg]||0)+1});',
    "segnote": '${segLine}',
    "prepseg": '  seg:r.seg||"",seg_evidence:r.seg_evidence||"",mp:r.mp||[],own_shop:!!r.own_shop,app:!!r.app,',
    "cardm": '  $("cardM").innerHTML=[`стенд ${esc(r.stand||"—")}`, esc(r.hall), esc(r.meta), r.seg?esc(SEG_LABELS[r.seg]||r.seg):"", r.mp&&r.mp.length?"МП: "+esc(r.mp.join(", ")):"", r.own_shop?"свой магазин":"", r.app?"приложение":"", r.site?`<a href="${esc(r.site.startsWith("http")?r.site:"http://"+r.site)}" target="_blank" rel="noopener">${esc(r.h)}</a>`:"сайта нет"].filter(Boolean).join(" · ");',
    "cardd": '  $("cardD").textContent=[SEG_PITCH[r.seg]||"", r.seg_evidence||"", r.descr||""].filter(Boolean).join(" "); $("cardD").classList.remove("open");',
    "popm": '    <div class="m">стенд ${esc(r.stand||"—")} · ${esc([r.hall,r.meta,SEG_LABELS[r.seg]||""].filter(Boolean).join(" · "))}</div>',
    "popv": '    ${r.seg?`<div class="v">${esc(SEG_PITCH[r.seg]||"")} ${esc(r.seg_evidence||"")}</div>`:""}',
}


def seg_tokens(has_seg, su):
    """Значения токенов __SEG*__ под выставку: без seg — байт-в-байт старое, с seg — общее или ev['seg_ui']."""
    if not has_seg:
        v = dict(SEG_NONE)
    else:
        v = dict(SEG_COMMON)
        v["dicts"] = su.get("dicts") or SEG_OLD["dicts"]
        v["chips"] = su.get("chips") or SEG_OLD["chips"]
        v["show"] = (su["show"] + ":") if su.get("show") else SEG_OLD["show"]
        line = su.get("line") or SEG_OLD["line"]
        v["mapsegline"] = '  const segLine=ROWS.some(r=>r.seg)?`' + line + '`:"";'
    return v


def _chips(target, opts, single=False):
    attr = ' data-single="1"' if single else ""
    return (f'<div class="chips" data-for="{target}"{attr}>'
            + "".join(f'<button class="chip" type="button" data-v="{html.escape(o)}">{html.escape(o)}</button>' for o in opts)
            + "</div>")


def _pitch_html(pt):
    """Питч другого менеджера в той же разметке, что основной."""
    h = [f'<h2>{pt.get("title", "Питч за минуту")}</h2>',
         '<div class="lbl">Открытие · 30 секунд</div>',
         f'<div class="say">{pt["opener"]}<div class="hook">{pt["hook"]}</div></div>']
    for lbl, key in (("Три вопроса вместо презентации", "value"), ("Предложение", "offer")):
        if pt.get(key):
            h.append(f'<div class="lbl">{lbl}</div><ul class="dots">' + "".join(f"<li>{v}</li>" for v in pt[key]) + "</ul>")
    h.append('<div class="lbl">Цель контакта — договориться</div><ol class="goal">' + "".join(f"<li>{v}</li>" for v in pt["goal"]) + "</ol>")
    h.append('<div class="lbl">Возражения</div>' + "".join(f'<details class="ob"><summary>{q}</summary><p>{a}</p></details>' for q, a in pt["objections"]))
    if pt.get("facts"):
        h.append('<div class="lbl">Если спросят</div><ul class="dots">' + "".join(f"<li>{v}</li>" for v in pt["facts"]) + "</ul>")
    if pt.get("more"):
        h.append(f'<p class="more">{pt["more"]}</p>')
    return "\n  ".join(h)


def mgr_tokens(ev, sh):
    """Выбор «Кто заполняет» (ev["managers"]), питч второго менеджера (sh["alt"]) и ссылка на план залов
    (ev["plan_map"]). Выбор хранится на устройстве в localStorage "expo_manager" — его же читает map.html.
    При отправке к источнику дописывается « · <менеджер>»: по нему строки уходят на вкладки таблицы."""
    out = {}
    if ev.get("plan_map"):
        out["__MAPLINK__"] = (f'  <p class="mapnote"><a href="{ev["plan_map"]}"><b>Официальный план залов с метками →</b></a> '
                              'цвет — чей клиент, фиолетовый — уже подходили. Ниже — схема по номерам стендов.</p>\n')
    mg = ev.get("managers") or []
    if not mg:
        return out
    chips = "".join(f'<button class="chip" type="button" data-m="mgr" data-mgr="{html.escape(m)}">{html.escape(m)}</button>' for m in mg)
    out["__MGRHTML__"] = (f'  <div class="fld" id="mgrbox"><label class="fl">Кто заполняет *</label><div class="chips" id="mgr">{chips}</div>'
                          '<div class="stt mute" id="mgrhint"></div></div>\n')
    alt = sh.get("alt") or {}
    if alt:
        out["__PITCHALT__"] = "".join(f'<div class="pitchalt" data-for-mgr="{html.escape(m)}" hidden>\n  {_pitch_html(pt)}\n</div>\n' for m, pt in alt.items())
    owner = ev.get("seg_owner") or {}
    out["__MGRJS__"] = ("/* ---------- кто заполняет ---------- */\n"
        "const MGR_KEY=\"expo_manager\", MGRS=" + json.dumps(mg, ensure_ascii=False) + ", SEG_OWNER=" + json.dumps(owner, ensure_ascii=False) + ";\n"
        "let MGR=LS.get(MGR_KEY,\"\"); if(MGRS.indexOf(MGR)<0) MGR=\"\";\n"
        "function mgrRender(){\n"
        "  document.querySelectorAll(\"#mgr .chip\").forEach(b=>b.classList.toggle(\"on\",b.dataset.mgr===MGR));\n"
        "  $(\"mgrhint\").textContent=MGR?\"Анкеты уходят на вкладку «\"+EVENT_SOURCE.split(\"·\")[0].trim()+\" — \"+MGR+\"» таблицы. Выбор запомнен на этом телефоне.\":\"Выберите себя один раз — телефон запомнит.\";\n"
        "  const alt=[...document.querySelectorAll(\".pitchalt\")], mine=alt.find(a=>a.dataset.forMgr===MGR);\n"
        "  [...$(\"p-pitch\").children].forEach(e=>{if(!e.classList.contains(\"pitchalt\"))e.hidden=!!mine;});\n"
        "  alt.forEach(a=>a.hidden=a!==mine);\n"
        "  if(typeof renderCard===\"function\") renderCard();\n"
        "}\n"
        "$(\"mgr\").addEventListener(\"click\",e=>{const b=e.target.closest(\".chip\");if(!b)return;MGR=b.dataset.mgr;LS.set(MGR_KEY,MGR);mgrRender();});\n"
        "$(\"send\").addEventListener(\"click\",e=>{if(!MGR){e.stopImmediatePropagation();const st=$(\"status\");st.className=\"st err\";st.textContent=\"Выберите, кто заполняет: \"+MGRS.join(\" или \")+\".\";$(\"mgrbox\").scrollIntoView({block:\"center\"});}},true);\n"
        "const _post=post; post=function(p){const q=Object.assign({},p);if(MGR&&String(q.source||\"\").indexOf(\" · \"+MGR)<0&&srcKey(q.source)===srcKey(EVENT_SOURCE))q.source=q.source+\" · \"+MGR;return _post(q);};\n"
        "const _renderCard=renderCard; renderCard=function(){_renderCard();const own=SEL&&SEL.seg?SEG_OWNER[SEL.seg]:\"\";\n"
        "  if(SEL&&MGR&&own&&own!==MGR){$(\"cardD\").textContent=\"Это клиент: \"+own+\" — возьмите контакт и передайте. \"+$(\"cardD\").textContent;}};\n"
        # Карта: сегмент — отдельный фильтр SF поверх эшелона и «были / не были» (MF), а не взаимоисключающий.
        # По умолчанию — сегменты того, кто заполняет (Никита: clickout+both, Андрей: mp+both).
        "const MGR_SEGS={}; Object.keys(SEG_OWNER).forEach(s=>{(MGR_SEGS[SEG_OWNER[s]]=MGR_SEGS[SEG_OWNER[s]]||[]).push(s)}); Object.keys(MGR_SEGS).forEach(m=>MGR_SEGS[m].push(\"both\"));\n"
        "let SF=MGR&&MGR_SEGS[MGR]?\"seg:\"+MGR_SEGS[MGR].join(\"+\"):\"\";\n"
        "const segOk=r=>!SF||SF.slice(4).split(\"+\").indexOf(r.seg)>=0;\n"
        "function sfChips(){$(\"fbar\").querySelectorAll('.chip[data-m^=\"seg:\"]').forEach(b=>b.classList.toggle(\"on\",b.dataset.m===SF));}\n"
        "$(\"fbar\").addEventListener(\"click\",e=>{const b=e.target.closest(\".chip\");if(!b||b.dataset.m.indexOf(\"seg:\")!==0)return;\n"
        "  e.stopImmediatePropagation();SF=SF===b.dataset.m?\"\":b.dataset.m;sfChips();renderMap();},true);\n"
        "const _renderMap=renderMap; renderMap=function(){_renderMap();sfChips();if(!SF)return;\n"
        "  const g=$(\"map\").groups||{};\n"
        "  $(\"map\").querySelectorAll(\".cell\").forEach(b=>{const c=g[b.dataset.g];if(c&&!c.items.some(segOk))b.classList.add(\"dim\");});\n"
        "  $(\"route\").querySelectorAll(\".it\").forEach(it=>{const r=ROWS[+it.dataset.i];if(r&&!segOk(r))it.remove();});};\n"
        "const _mgrRender=mgrRender; mgrRender=function(){_mgrRender();if(MGR&&MGR_SEGS[MGR]){SF=\"seg:\"+MGR_SEGS[MGR].join(\"+\");renderMap();}};\n"
        "mgrRender();\n")
    return out


def build_short(ev, source_options, webhook, lists):
    """ev — словарь события с ключом "short"; lists — {source: "../slug/exhibitors.json"} для выставок с каталогом."""
    sh = ev["short"]
    rows = json.loads((ROOT / ev["slug"] / "exhibitors.json").read_text(encoding="utf-8"))
    has_seg = any("seg" in r for r in rows)
    ekeys = ("name", "stand", "site", "prio", "top", "hall", "meta", "tags", "descr")
    if has_seg:
        ekeys += ("seg", "seg_evidence", "mp", "own_shop", "app")
    embed = [{k: (r.get(k)[:260] if k == "descr" else r.get(k)) for k in ekeys}
             for r in rows]
    qs = "".join(
        f'<div class="q"><div class="qq"><b>{i+1:02d}</b>{html.escape(q["q"])}</div>{_chips(f"a{i+1}", q["chips"])}'
        f'<textarea class="ft" id="a{i+1}" placeholder="ответ своими словами"></textarea></div>'
        for i, q in enumerate(sh["questions"]))
    xa = "".join(
        f'<div><label class="fl">{html.escape(lbl)}</label>{_chips(f"x_{k}", opts, single=True)}<input type="hidden" id="x_{k}"></div>'
        for k, lbl, opts in sh["express"])
    src_opts = "".join(f'<option{" selected" if o == ev["source"] else ""}>{html.escape(o)}</option>' for o in source_options)
    js = lambda v: json.dumps(v, ensure_ascii=False).replace("</", "<\\/")
    rep = {
        "__TITLE__": f'{ev["name"]} · Click Out — короткая версия ведущего',
        "__CSS__": CSS,
        "__EVCHIP__": html.escape(f'{ev["name"]} · {ev["dates"]}'),
        "__OPENER__": sh["opener"],
        "__HOOK__": sh["hook"],
        "__VALUE__": "".join(f"<li>{v}</li>" for v in sh["value"]),
        "__GOAL__": "".join(f"<li>{v}</li>" for v in sh["goal"]),
        "__OBJ__": "".join(f'<details class="ob"><summary>{q}</summary><p>{a}</p></details>' for q, a in sh["objections"]),
        "__FACTS__": "".join(f"<li>{v}</li>" for v in sh["facts"]),
        "__SRC_OPTS__": src_opts,
        "__NICHE_PH__": html.escape(ev.get("niche_placeholder", "")),
        "__QS__": qs,
        "__XA__": xa,
        "__MCHIPS__": "".join(f'<button class="chip" type="button" data-v="{html.escape(o)}">{html.escape(o)}</button>' for o in sh["meeting_chips"]),
        "__WEBHOOK__": js(webhook),
        "__SHEET__": SHEET_ID,
        "__EVENT_SOURCE__": js(ev["source"]),
        "__LISTS__": js(lists),
        "__EMBED__": js(embed),
        "__QCODES__": js({f"a{i+1}": q["code"] for i, q in enumerate(sh["questions"])}),
        "__XKEYS__": js([k for k, _, _ in sh["express"]]),
        "__SLUG__": ev["slug"],
    }
    # Сегмент-тексты и фильтр карты: выставкам без seg — байт-в-байт старые страницы,
    # InterCHARM подставляет ev["seg_ui"] (правила Никиты от 13.10.2026).
    sv = seg_tokens(has_seg, ev.get("seg_ui") or {})
    rep["__SEGCHIPS__"] = sv["chips"]
    rep["__SEGSHOW__"] = sv["show"]
    rep["__MAPC__"] = sv["mapc"]
    rep["__SEGNOTE__"] = sv["segnote"]
    rep["__CARDM__"] = sv["cardm"]
    rep["__CARDD__"] = sv["cardd"]
    rep["__POPM__"] = sv["popm"]
    if has_seg:
        rep["__SEGDICTS__"] = sv["dicts"]
        rep["__PREPSEG__"] = sv["prepseg"]
        rep["__MAPSEGLINE__"] = sv["mapsegline"]
        rep["__POPV__"] = sv["popv"]
    else:
        # строчные токены удаляются вместе с переводом строки (иначе осталась бы пустая строка)
        rep["__SEGDICTS__\n"] = ""
        rep["__PREPSEG__\n"] = ""
        rep["__MAPSEGLINE__\n"] = ""
        rep["__POPV__\n"] = ""
    mt = mgr_tokens(ev, sh)
    for k in ("__MGRHTML__", "__PITCHALT__", "__MAPLINK__", "__MGRJS__"):
        if mt.get(k):
            rep[k] = mt[k]
        else:
            rep[k + "\n"] = ""   # выставки без менеджеров — байт-в-байт как раньше
    out = PAGE
    for k, v in rep.items():
        out = out.replace(k, v)
    return out
