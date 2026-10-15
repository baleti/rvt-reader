import sys,glob,re,collections,json,os
sys.path.insert(0,'/home/user1/rvt-research')
import rvt_inventory as I
p=sys.argv[1]
cls,ids,recs,st=I.inventory(p)
last={k:v[-1] for k,v in recs.items()}
sig=collections.Counter(); ncomp=0; ex={}
for r in last.values():
    if r.get('complete'): ncomp+=1; continue
    m=r.get('error') or ''
    if '@@' in m: key=re.sub(r'\d+','N',m.split('@@')[1].split(' at ')[0].strip())[:90]
    elif m: key=re.sub(r'\d+','N',m)[:70]
    else: key='<geometry stop>'
    sig[key]+=1; ex.setdefault(key,(r['id'],r['class']))
print(json.dumps({'file':os.path.basename(p),'records':len(last),'complete':ncomp,'top':[(k,v,ex[k]) for k,v in sig.most_common(25)]}))
