import json,sys
b=sys.argv[1]
def L(p): return {(r.get('eid')):r for r in map(json.loads,open(p))}
o=L(b+'_old.jsonl'); n=L(b+'_new.jsonl'); d=0
for k in o:
    a,c=o[k],n.get(k)
    if c is None: print('missing',k); continue
    for f in ('mvol','marea','closed','ntri'):
        if a.get(f)!=c.get(f): d+=1; print(k,f,a.get(f),c.get(f)); break
print(b,'rows',len(o),'changed',d)
