import sys,struct,glob,olefile
sys.path.insert(0,"/home/user1/rvt-research")
import rvt2text as T
from rvtfmt import inflate_stream
f=sys.argv[1]; lo,hi=int(sys.argv[2]),int(sys.argv[3])
o=olefile.OleFileIO(f)
for e in o.listdir(streams=True):
    nm="/".join(e)
    try: d=T.joined(o.openstream(nm).read()) if nm.startswith("Partitions") else inflate_stream(o.openstream(nm).read())[1]
    except Exception: continue
    for fmt,w in (("<Q",8),("<I",4)):
        c=0
        for a in range(w):
            import numpy as np
            m=(len(d)-a)//w
            arr=np.frombuffer(d,dtype="<u8" if w==8 else "<u4",count=m,offset=a)
            hit=np.nonzero((arr>=lo)&(arr<=hi))[0]
            c+=len(hit)
            if len(hit) and nm.startswith("Global"):
                print(nm,w,a,[int(arr[h]) for h in hit[:6]], [int(h)*w+a for h in hit[:3]])
        if c: print(nm,fmt,"hits",c)
