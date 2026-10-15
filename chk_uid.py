import sys,glob,os,collections
sys.path.insert(0,'.')
import rvt_uid, ifcguid
res=collections.defaultdict(lambda:[0,0,0,0,0]); bad=[]; sto=collections.Counter()
for g in sorted(glob.glob('gt4/*.tsv')):
    b=os.path.basename(g)[:-4]; y,rest=b.split('_',1)
    f=glob.glob('corpus/%s/%s'%(y,rest))
    if not f: continue
    u=rvt_uid.unique_ids(f[0]); gt={};ifc={}
    for ln in open(g,encoding='utf-8'):
        q=ln.rstrip('\n').split('\t')
        if q[0]=='E' and len(q)>8: gt[int(q[1])]=q[8]
        elif q[0]=='P' and len(q)>5 and q[2]=='-1019000': ifc[int(q[1])]=q[5]
    r=res[y]; r[0]+=len(gt); r[1]+=sum(1 for k,v in gt.items() if u.get(k)==v)
    for k,v in ifc.items():
        if k in u:
            r[2]+=1; r[3]+= ifcguid.from_unique(u[k])==v
    for k,v in gt.items():
        if u.get(k)!=v and len(bad)<6: bad.append((b[:30],k,v,u.get(k)))
for y,r in sorted(res.items()): print(y,'uid %d/%d'%(r[1],r[0]),'ifc %d/%d'%(r[3],r[2]))
for x in bad: print(x)
