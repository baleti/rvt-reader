import sys,collections,os; sys.path.insert(0,'/home/user1/rvt-research')
import rvt_params as RP, rvt_elemmesh as EM, rvt_geomparams as GP, rvt_xcache
path,gt=sys.argv[1:3]; lim=int(sys.argv[3]) if len(sys.argv)>3 else 150
g=collections.defaultdict(dict)
for l in open(gt):
    p=l.rstrip('\n').split('\t')
    if p[0]=='P' and len(p)>5 and p[3] in('Area','Category','Family and Type'): g[int(p[1])][p[3]]=p[5]
x=rvt_xcache.get_x_ro(path)
recs={}
for (eid,c),r in x['recs'].items(): recs.setdefault(eid,(c,r))
doc=EM.Doc(path)
cnt=collections.Counter(); st=collections.defaultdict(collections.Counter); ex=collections.defaultdict(list)
for eid,(c,r) in recs.items():
    if c!='FamilyInstance' or eid not in g or 'Area' not in g[eid] or eid not in doc.res: continue
    cat=int(g[eid].get('Category','0') or 0)
    if cnt[cat]>=lim: continue
    cnt[cat]+=1
    try: gp=GP.geom_params(doc,eid,r['fields'],cat,'FamilyInstance')
    except Exception as e: st[cat]['err']+=1; continue
    v=gp.get('Area'); t=float(g[eid]['Area'])
    if v is None: st[cat]['none']+=1
    elif abs(v-t)<=0.02*max(abs(t),1e-9): st[cat]['ok']+=1
    else:
        st[cat]['bad']+=1
        if len(ex[cat])<3: ex[cat].append((eid,round(v,5),round(t,5)))
for cat in st: print(cat,dict(st[cat]),ex[cat])
