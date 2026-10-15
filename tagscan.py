import sys,os,struct,collections
sys.path.insert(0,'/home/user1/rvt-research')
import numpy as np, olefile, rvt_scan as S, rvt2text as T
f=sys.argv[1]; pn=sys.argv[2]; kws=sys.argv[3:]
o,cls,ids=S.load(f); names={i+12:c['name'] for i,c in enumerate(cls)}
ch=T.joined(o.openstream(pn).read()); print(len(ch))
tags={t:n for t,n in names.items() if any(k==n or n.startswith(k) for k in kws)}
cnt=collections.Counter()
for a in (0,1):
    u=np.frombuffer(ch,dtype='<u2',count=(len(ch)-a)//2,offset=a)
    for t,n in tags.items():
        cnt[n]+=int((u==t).sum())
print(sorted(cnt.items(),key=lambda x:-x[1])[:25])
