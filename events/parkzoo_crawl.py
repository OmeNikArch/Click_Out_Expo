import re, subprocess, json, html, os, sys
from concurrent.futures import ThreadPoolExecutor
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
BASE="https://lk.parkzoo.ru"
def get(url):
    r=subprocess.run(["curl","-sL","--max-time","60","-A",UA,url],capture_output=True); return r.stdout.decode('utf-8','ignore')
comp={}  # url -> {stand info from listing}
start=0; empty=0
while start<2000:
    s=get(f"{BASE}/expositions/exposition/6608?start={start}")
    found=set(re.findall(r'/companies/company/\d+-[^"#?]+\.html',s))
    new=found-set(comp)
    if not new:
        empty+=1
        if empty>=2: break
    else:
        empty=0
    for u in new: comp[u]={}
    # capture listing text near each link: hall/stand
    txt=html.unescape(re.sub(r'<[^>]+>','\n',re.sub(r'<script.*?</script>','',s,flags=re.S)))
    print(f"start={start}: +{len(new)} total={len(comp)}",file=sys.stderr)
    start+=8
open('parkzoo/_list_sample.html','w',encoding='utf-8').write(s)
json.dump(sorted(comp),open('pz_urls.json','w'))
def fetch(u):
    fn="parkzoo/"+u.split('/')[-1]
    if not os.path.exists(fn) or os.path.getsize(fn)<5000:
        open(fn,'w',encoding='utf-8').write(get(BASE+u))
    return fn
with ThreadPoolExecutor(12) as ex: files=list(ex.map(fetch,sorted(comp)))
print("fetched",len(files),file=sys.stderr)
