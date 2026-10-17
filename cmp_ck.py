import json,sys,os
# compare fidck vs fidfull9 per file: elements whose status/iou/volume error changed
def load(p): 
    d={}
    for l in open(p):
        try: r=json.loads(l)
        except: continue
        d[r['eid']]=r
    return d
for f in sorted(os.listdir('fidck')):
    if not f.endswith('.jsonl'): continue
    a=load('fidfull9/'+f); b=load('fidck/'+f); n=w=bt=0; worse=[]
    for e,r in b.items():
        o=a.get(e)
        if not o: continue
        def err(x):
            v,g=x.get('vol'),x.get('gtv')
            return abs(v/g-1) if v and g else None
        n+=1; eo,en=err(o),err(r)
        if eo is not None and en is not None:
            if en<eo-0.005: bt+=1
            elif en>eo+0.005: w+=1; worse.append((e,r['cls'],round(eo,3),round(en,3)))
    print(f,'n',n,'better',bt,'worse',w); print(worse[:8])
