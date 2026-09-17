import re, subprocess, json, html, os, sys
from concurrent.futures import ThreadPoolExecutor
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
BASE="https://icatalog.expocentr.ru/ru/exhibitions/"
EXPOS={"md":"f33d0462-98f8-11ef-80ce-a0d3c1fab97f","cjf":"f33d0460-98f8-11ef-80ce-a0d3c1fab97f"}
def get(url):
    r=subprocess.run(["curl","-sL","--max-time","60","-A",UA,url],capture_output=True)
    return r.stdout.decode('utf-8','ignore')
links={}
for key,eid in EXPOS.items():
    urls=[BASE+eid, BASE+eid+"/list", BASE+eid+"/alphabet"]+[BASE+eid+f"?&hallid={h}" for h in (40,41,42,43)]
    found={}
    for u in urls:
        s=get(u)
        for m in re.finditer(r'https://icatalog\.expocentr\.ru/ru/exhibitions/'+eid+r'/exhibitors/(\d+)\?&?stand=([0-9A-Z,]+)',s):
            found.setdefault(m.group(1),m.group(2))
        print(key,u,"->",len(found),file=sys.stderr)
    links[key]=found
json.dump(links,open('icat_links.json','w'))
def fetch(args):
    key,eid,iid,stand=args
    fn=f"icat/{key}_{iid}.html"
    if not os.path.exists(fn) or os.path.getsize(fn)<10000:
        s=get(f"{BASE}{eid}/exhibitors/{iid}?&stand={stand}")
        open(fn,'w',encoding='utf-8').write(s)
    return fn
jobs=[(k,EXPOS[k],i,st) for k in links for i,st in links[k].items()]
print("total pages to fetch:",len(jobs),file=sys.stderr)
with ThreadPoolExecutor(12) as ex:
    list(ex.map(fetch,jobs))
FIELDS=["Стенд","Страна","Город","Адрес","Телефон","Сайт","E-mail","Описание","Рубрики"]
def parse(fn):
    s=open(fn,encoding='utf-8',errors='ignore').read()
    s=re.sub(r'<script.*?</script>|<style.*?</style>|<!--.*?-->','',s,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',s))
    L=[l.strip() for l in t.split('\n') if l.strip() and l.strip()!='-->']
    try:
        i=next(k for k,l in enumerate(L) if l.startswith('Стенд:'))
    except StopIteration:
        return None
    name=L[i-1]
    d={"name":name}
    j=i
    while j<len(L) and not L[j].startswith('Предоставленная информация'):
        l=L[j]
        if l.endswith(':') and l[:-1] in FIELDS:
            f=l[:-1]; j+=1; vals=[]
            while j<len(L) and not (L[j].endswith(':') and L[j][:-1] in FIELDS) and not L[j].startswith('Предоставленная информация'):
                vals.append(L[j]); j+=1
            d[f]=vals if f=="Рубрики" else " ".join(vals)
        else:
            j+=1
    return d
out={}
for k in links:
    rows=[]
    for iid in links[k]:
        d=parse(f"icat/{k}_{iid}.html")
        if d: d["id"]=iid; rows.append(d)
    rows.sort(key=lambda r:r.get("Стенд",""))
    out[k]=rows
    json.dump(rows,open(f'{k}_exhibitors.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
    from collections import Counter
    print(f"== {k}: parsed {len(rows)} of {len(links[k])}; countries:",Counter(r.get('Страна','') for r in rows).most_common(6),
          "; with site:",sum(1 for r in rows if r.get('Сайт')),"; with descr:",sum(1 for r in rows if r.get('Описание')),file=sys.stderr)
