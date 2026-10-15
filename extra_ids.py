import sys,struct,glob,collections
sys.path.insert(0,'/home/user1/rvt-research')
import olefile, rvt_scan as S
from rvtfmt import inflate_stream
f=sys.argv[1]; want=set(int(a) for a in sys.argv[2].split(','))
o,cls,ids=S.load(f); et=inflate_stream(o.openstream('Global/ElemTable').read())[1]
n=(len(et)-6)//40
cols=collections.defaultdict(set)
for k in range(n):
    for c in range(0,40,4):
        cols[c].add(struct.unpack_from('<Q',et,6+40*k+c)[0])
for c in sorted(cols):
    ex={v for v in cols[c] if v not in ids and 0<v<max(ids)+10}
    print(c,len(ex),len(ex&want),'of',len(want))
