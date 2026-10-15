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
chunk,i0=buf; FACE0=i0+429; PLANE2=i0+599; END=i0+704
class Fail(Exception): pass
def ok(v):
    import rvt_solve as V
    return V.plausible(v)
def run(opts):
    d=D.Dec(sch,idsize=W); d.maxh=4; d.hints={}
    def obj(p, tag, depth=0):
        name=sch.name(tag); op=opts.get(name, ('base','at_end',0,0))
        order,mode,pre,suf=op
        if depth>6: raise Fail
        p+=pre
        chain=sch.chain(tag-12)
        if order=='derived': chain=chain[::-1]
        out={}; allp=[]
        for k in chain:
            pend=[]
            for f in sch.c[k]['fields']:
                try: out[sch.c[k]['name']+'.'+f['name']], p = d.value(chunk,p,f,pend,[f['name']])
                except (D.Desync,struct.error,IndexError): raise Fail
            if mode=='per_class':
                for slot,t in pend:
                    v,p=obj(p,t,depth+1); slot['obj']=v
            else: allp+=pend
        for slot,t in allp:
            v,p=obj(p,t,depth+1); slot['obj']=v
        if not ok(out): raise Fail
        return out,p+suf
    try:
        v,q=obj(FACE0,tags['Face'])
        if q!=PLANE2 and True: pass
        # then plane #2
        v2,q2=obj(q,tags['Plane'])
        return q,q2
    except Fail: return None
best=[]
opt=[(o_,m,pre,suf) for o_ in ('base','derived') for m in ('per_class','at_end') for pre in range(0,9) for suf in range(0,3)]
cnt=0
for fo in opt:
    for po in opt:
        r=run({'Face':fo,'Plane':po}); cnt+=1
        if r: best.append((abs(r[1]-END)+abs(r[0]-PLANE2)*0, abs(r[0]-PLANE2), fo, po, r))
best.sort(); print(cnt,'combos;',len(best),'decodable'); 
for b in best[:10]: print(b)
