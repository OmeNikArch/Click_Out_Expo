# Официальный план залов InterCHARM 2026 → intercharm/plan/ (картинки залов и координаты стендов).
# Источник — путеводитель организатора (disk.360.yandex.ru/i/7eyblaPyFnXtgw), скачать в cache/intercharm-plan/guide.pdf,
# там же: pdftotext -bbox по страницам планов → p<N>.bbox.html; запуск из cache/intercharm-plan.
import re,json,html,subprocess,collections,sys
HOMO=str.maketrans("АВСЕНКМОРТХавсенкмортх","ABCEHKMOPTXabcehkmoptx")
# страница, зал, рамка плана в пунктах PDF (x0,y0,x1,y1); всё вне рамки — списки компаний
CFG=[(3,13,(10,119,1180,618)),(6,14,(10,90,1180,633)),(9,15,(10,90,1180,619)),(13,17,(210,85,1180,715)),(15,18,(10,85,985,745))]
res={}
for p,hall,(X0,Y0,X1,Y1) in CFG:
    s=open(f"p{p}.bbox.html",encoding="utf-8").read()
    W=[(float(a),float(b),float(c),float(d),html.unescape(t)) for a,b,c,d,t in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',s)]
    st=collections.defaultdict(list)
    for x0,y0,x1,y1,t in W:
        cx,cy=(x0+x1)/2,(y0+y1)/2
        if not (X0<cx<X1 and Y0<cy<Y1): continue
        for tok in re.split(r"[,\s]+",t.strip()):
            n=tok.translate(HOMO).upper()
            if re.fullmatch(rf"{hall}[A-H]\d{{1,3}}[A-Z]?",n): st[n].append((cx,cy))
    sc=150/72; Wp=int((X1-X0)*sc); Hp=int((Y1-Y0)*sc)
    subprocess.run(["pdftoppm","-f",str(p),"-l",str(p),"-r","150","-x",str(int(X0*sc)),"-y",str(int(Y0*sc)),"-W",str(Wp),"-H",str(Hp),"-png","-singlefile","guide.pdf",f"hall-{hall}"],check=True)
    res[str(hall)]={"img":f"hall-{hall}.png","w":Wp,"h":Hp,
        "stands":{k:[round((v[0][0]-X0)/(X1-X0)*100,2),round((v[0][1]-Y0)/(Y1-Y0)*100,2)] for k,v in sorted(st.items())}}
    print(hall,"stands",len(st),"dups",[k for k,v in st.items() if len(v)>1][:8])
json.dump(res,open("plan.json","w"),ensure_ascii=False,indent=0)
