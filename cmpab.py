import json,os,sys
def ld(p): return {tuple(k):n for k,n in json.load(open(p))['rows']}
nd,bd=sys.argv[1],sys.argv[2]
for f in sorted(os.listdir(nd)):
    if not f.endswith('.json'): continue
    b=bd+'/'+f
    if not os.path.exists(b): print('nobase',f); continue
    n=ld(nd+'/'+f); o=ld(b); ok=lambda d:sum(v for k,v in d.items() if k[5]=='ok')
    print(f,'ok',ok(o),'->',ok(n),'of',sum(n.values()))
    for k in n:
        if k[5]!='ok': continue
        kk=k[:5]+('ok',)
        if n[k]<o.get(kk,0): print('  WORSE',k[3:5],k[:3],o[kk],'->',n[k])
    for k in n:
        if k[5]=='ok' and n[k]>o.get(k,0)+20: print('  better',k[3],k[0],k[2],o.get(k,0),'->',n[k])
