import sys,zlib,olefile,struct,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import rvt2text as T, rvt_scan as S, rvt_decode as D
f,pn,k,ri=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]); maxd=int(sys.argv[5]) if len(sys.argv)>5 else 12
o,cls,ids=S.load(f); W=S.id_size(cls); sch=D.Schema(cls); dec=D.Dec(sch,idsize=W)
import rvt_es as ES
try: dec.es_schemas=ES.load(f)[0]
except Exception: dec.es_schemas={}
data=T.strip_pages(o.openstream(pn).read()); GZ=T.GZ
pos=0; last_end=0; n=0
def show(o,ind,k=''):
    pad='  '*ind
    if ind>maxd: print(pad+k+': ...'); return
    if isinstance(o,dict):
        keys=[a for a,b in o.items() if b is not None and a not in('handle','ptr')]
        print(pad+k+': {'+','.join(keys[:14])+('...' if len(keys)>14 else '')+'}')
        for a in keys:
            b=o[a]
            if isinstance(b,(dict,list)): show(b,ind+1,a)
            else: print(pad+'  '+a+' = '+str(b)[:60])
    elif isinstance(o,list):
        if o and all(isinstance(a,(int,float)) for a in o): print(pad+k+' '+str(o)[:100]); return
        print(pad+k+'[%d]'%len(o))
        for i,a in enumerate(o[:3]): show(a,ind+1,'[%d]'%i)
    else: print(pad+k+' = '+str(o)[:60])
while True:
    i=data.find(GZ,pos)
    if i<0: break
    d=zlib.decompressobj(-15)
    try: out=d.decompress(data[i+10:])
    except zlib.error: pos=i+4; continue
    end=len(data)-len(d.unused_data); gap=data[last_end:i]
    if len(gap)>=8 and struct.unpack_from('<Q',gap,len(gap)-8)[0]==103:
        if n==k:
            buf=b'\x00\x00\x00\x00'+out; p=0
            for j in range(ri+1): r,q=dec.record(buf,p,False); p=q if j<ri else p
            print('id',r['id'],r['class'],'len',q-p); show(r['fields'],0,'GElement'); break
        n+=1
    last_end=end; pos=end
