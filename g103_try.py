import sys,zlib,olefile,struct,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import rvt2text as T, rvt_scan as S, rvt_decode as D
f,pn,k=sys.argv[1],sys.argv[2],int(sys.argv[3])
o,cls,ids=S.load(f); W=S.id_size(cls); sch=D.Schema(cls); dec=D.Dec(sch,idsize=W)
import rvt_es as ES
try: dec.es_schemas=ES.load(f)[0]
except Exception: dec.es_schemas={}
data=T.strip_pages(o.openstream(pn).read()); GZ=T.GZ
pos=0; last_end=0; n=0
while True:
    i=data.find(GZ,pos)
    if i<0: break
    d=zlib.decompressobj(-15)
    try: out=d.decompress(data[i+10:])
    except zlib.error: pos=i+4; continue
    end=len(data)-len(d.unused_data); gap=data[last_end:i]
    if len(gap)>=8 and struct.unpack_from('<Q',gap,len(gap)-8)[0]==103:
        if n==k:
            buf=b'\x00\x00\x00\x00'+out; p=0; cnt=0
            while p<len(buf)-30 and cnt<400:
                try: r,q=dec.record(buf,p,False)
                except Exception as e: print('ERR at',p,repr(e)[:100]); break
                if cnt<6 or not r['complete']: print('rec',cnt,'id',r['id'],'class',r['class'],'complete',r['complete'],'err',(r.get('error') or '')[:80],'len',q-p,'bodies',collections.Counter(r['bodies']).most_common(6))
                p=q; cnt+=1
                # next record header begins at q; our header expects [A u32][id..]; there is no A in channel 103 -> shift by inserting zeros
            break
        n+=1
    last_end=end; pos=end
