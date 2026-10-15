import sys,glob,re,collections
sys.path.insert(0,'/home/user1/rvt-research')
import rvt_fail as F
from schema_view import tn
p=glob.glob(sys.argv[1])[0]; want=sys.argv[2:]
cls,ids,ok,fails=F.failures(p); by={c['name']:i for i,c in enumerate(cls)}
seen=set()
for e,lst in fails.items():
    if e in ok: continue
    c,m=lst[-1]
    if '@@' not in m: continue
    fld=m.split('@@')[1].strip().split(' ')[0]
    if fld in seen or not any(w in fld for w in want): continue
    seen.add(fld)
    cn,fn=fld.split('.')[:2]
    print('=====',c,'|',m[:330])
    for fl in cls[by[cn]]['fields']:
        if fl['name']==fn: print('   FIELD',cn+'.'+fn,[hex(t) for t in fl['types']],'ns',fl.get('ns'),'ref',fl.get('ref'),'ref2',fl.get('ref2'),'=>',tn(cls,fl))
