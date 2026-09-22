import re, html, glob, json
from collections import Counter
rows=[]
for fn in sorted(glob.glob('parkzoo/*.html')):
    if fn.endswith('_list_sample.html'): continue
    s=open(fn,encoding='utf-8',errors='ignore').read()
    s=re.sub(r'<script.*?</script>|<style.*?</style>|<!--.*?-->','',s,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',s)); L=[l.strip() for l in t.split('\n') if l.strip()]
    idx=next((k for k,l in enumerate(L) if re.match(r'^\d[A-Z]\d{1,3}(\s*[,/]|$)',l) or re.match(r'^[A-Z]?\d[A-Z]\d{2}.*/\s*зал',l)),None)
    if idx is None or idx<2: continue
    stand=L[idx]; country=L[idx-1]; name=L[idx-2]
    j=idx+1; descr=[]
    while j<len(L) and L[j] not in ('Вид деятельности','Представляемые группы товара','Контакты','Читать описание целиком'): descr.append(L[j]); j+=1
    def section(title, stops):
        try: k=L.index(title)
        except ValueError: return []
        k+=1
        if k<len(L) and L[k]==':': k+=1
        out=[]
        while k<len(L) and L[k] not in stops: out.append(L[k]); k+=1
        return out
    prof=section('Вид деятельности',{'Представляемые группы товара','Контакты','Вернуться к списку'})
    prods=section('Представляемые группы товара',{'Контакты','Вернуться к списку'})
    site=''; m=re.search(r'Веб-сайт:\s*\n?\s*(\S+)',t); site=m.group(1) if m else ''
    phones=re.findall(r'Телефон:\s*\n?\s*([+\d][\d ()\-]{6,})',t); emails=sorted(set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+',t))-{'info@parkzoo.ru'})
    addr=section('Контакты',{'Веб-сайт:','Телефон:','E-mail:','Вернуться к списку'})
    city=''
    for a in addr:
        mm=re.search(r'Россия,\s*(?:[^,]+область,\s*|[^,]+край,\s*|Республика [^,]+,\s*)?([^,]+)',a)
        if mm: city=mm.group(1).strip(); break
    hall=(re.search(r'зал\s*(\d)',stand) or [None,''])[1]
    rows.append({"name":name,"country":country,"stand":stand,"hall":hall,"descr":re.sub(r'\s+',' ',' '.join(descr)).strip(),"products":prods,"profile":prof,"site":site,"city":city,"_emails":emails,"_phones":phones,"_addr":addr})
json.dump(rows,open('pz_rows.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print("parsed",len(rows)); print("countries:",Counter(r['country'] for r in rows).most_common(10)); print("profiles:",Counter(p for r in rows for p in r['profile']).most_common(15))
print("halls:",Counter(r['hall'] for r in rows)); print("with site:",sum(1 for r in rows if r['site']))
print("products:",Counter(p for r in rows for p in r['products']).most_common(30))
ecom=re.compile(r'интернет-магазин|маркетплейс|ozon|wildberries|озон|розничн|сеть (магазинов|зоомагазинов)|зоомагазин|ветеринарн\w+ (клиник|центр)|груминг|приют|фонд',re.I)
print("ecom/retail signal:",sum(1 for r in rows if ecom.search(r['descr'])))
for r in rows[:3]: print(r['name'],'|',r['country'],'|',r['stand'],'|',r['profile'],'|',r['site'],'|',r['city'])
