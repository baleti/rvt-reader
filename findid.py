import sys,struct,glob,olefile
sys.path.insert(0,"/home/user1/rvt-research")
import rvt2text as T
from rvtfmt import inflate_stream
f=sys.argv[1]; ids=[int(a) for a in sys.argv[2].split(',')]
o=olefile.OleFileIO(f)
for e in o.listdir(streams=True):
    nm="/".join(e)
    try: d=T.joined(o.openstream(nm).read()) if nm.startswith("Partitions") else inflate_stream(o.openstream(nm).read())[1]
    except Exception: continue
    for v in ids:
        for fmt in ("<I","<Q"):
            b=struct.pack(fmt,v); j=d.find(b); c=0
            while j>=0 and c<3:
                print(nm,v,fmt,j,d[max(0,j-12):j+28].hex(" ")); c+=1; j=d.find(b,j+1)
