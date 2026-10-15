import sys, os, struct, itertools, math
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_scan as S, rvt_decode as D, rvt2text as T
p='exp_out/e1.rvt'; o,cls,ids=S.load(p); sch=D.Schema(cls); W=4
tags={c['name']:i+12 for i,c in enumerate(cls)}
buf=None
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    for chunk in T.segments(o.openstream(pn).read()):
        for i in range(0,len(chunk)-24):
            if struct.unpack_from('<I',chunk,i+4)[0]==2471 and struct.unpack_from('<H',chunk,i+16)[0]==tags['Level']: buf=(chunk,i); break
        if buf: break
    if buf: break
chunk,i0=buf
FACE0=i0+429; PLANE2=i0+599; END=i0+704
class Fail(Exception): pass
def run(variant):
    order, bodies, pre, suf = variant
    d=D.Dec(sch,idsize=W); d.maxh=4; d.hints={}
    def obj(p, tag, depth=0):
        if depth>6: raise Fail('depth')
        ci=tag-12; chain=sch.chain(ci)
        if order=='derived': chain=chain[::-1]
        out={}; allpend=[]
        for k in chain:
            pend=[]
            for f in sch.c[k]['fields']:
                try: out[sch.c[k]['name']+'.'+f['name']], p = d.value(chunk,p,f,pend,[f['name']])
                except (D.Desync,struct.error,IndexError): raise Fail('field '+f['name'])
            if bodies=='per_class':
                for slot,t in pend:
                    v,p=obj(p,t,depth+1); slot['obj']=v
            else: allpend+=pend
        for slot,t in allpend:
            v,p=obj(p,t,depth+1); slot['obj']=v
        return out,p
    p=FACE0+pre
    try:
        v,q=obj(p,tags['Face'])
    except Fail as e: return None
    q+=suf
    return q
res=[]
for order in ('derived','base'):
    for bodies in ('per_class','at_end'):
        for pre in range(0,10):
            for suf in range(0,6):
                q=run((order,bodies,pre,suf))
                res.append((abs(q-PLANE2) if q is not None else 9999, order,bodies,pre,suf,q))
res.sort(); 
for r in res[:12]: print(r)
