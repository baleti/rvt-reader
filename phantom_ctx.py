import sys,struct,olefile
import numpy as np
sys.path.insert(0,"/home/user1/rvt-research")
import rvt2text as T
f,lo,hi=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]); pn=sys.argv[4]
o=olefile.OleFileIO(f); d=T.joined(o.openstream(pn).read())
for a in range(8):
    m=(len(d)-a)//8; arr=np.frombuffer(d,dtype="<u8",count=m,offset=a)
    for h in np.nonzero((arr>=lo)&(arr<=hi))[0]:
        p=int(h)*8+a; print(p,int(arr[h]),d[max(0,p-24):p+32].hex(" "))
