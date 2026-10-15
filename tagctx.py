import sys,os,struct,collections
sys.path.insert(0,'/home/user1/rvt-research')
import numpy as np, olefile, rvt_scan as S, rvt2text as T
f,pn,name=sys.argv[1:4]; n=int(sys.argv[4]) if len(sys.argv)>4 else 6
o,cls,ids=S.load(f); tag=[i+12 for i,c in enumerate(cls) if c['name']==name][0]
print(name,hex(tag),[ (fl['name'],hex(fl['T'])) for fl in cls[tag-12]['fields']][:10], 'parent',cls[(cls[tag-12]['parent']&0x7fff)-12]['name'])
ch=T.joined(o.openstream(pn).read())
pat=struct.pack('<H',tag); pos=[]; j=ch.find(pat)
while j>=0 and len(pos)<4000:
    pos.append(j); j=ch.find(pat,j+1)
print(len(pos),'raw hits')
for p in pos[:n]: print(p,ch[p-12:p+40].hex(' '))
