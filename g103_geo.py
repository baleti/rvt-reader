import sys,zlib,olefile,struct,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import rvt2text as T, rvt_scan as S, rvt_decode as D
f,pn,k,ri=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
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
            buf=b'\x00\x00\x00\x00'+out; p=0
            for j in range(ri+1): r,q=dec.record(buf,p,False); p=q if j<ri else p
            fl=r['fields']
            print('id',r['id'],{a:fl[a] for a in ('m_elementId','m_gElemType','m_flags','m_bBox','m_tightbBox') if a in fl})
            geos=[]
            def w(o,path):
                if isinstance(o,dict):
                    if 'm_pFaces' in o or 'm_pEdges' in o: geos.append((path,o))
                    for a,b in o.items():
                        if b is not None: w(b,path+'/'+a[2:6])
                elif isinstance(o,list):
                    for i2,b in enumerate(o): w(b,path+'[%d]'%i2)
            w(fl,'')
            print('geometry nodes',len(geos))
            for path,g in geos[:3]:
                print(path[-60:],'faces',len(g.get('m_pFaces') or []),'edges',len(g.get('m_pEdges') or []))
                for fc in (g.get('m_pFaces') or [])[:2]:
                    fc=fc.get('obj',fc); sf=fc.get('m_pSurf'); sf=sf.get('obj',sf) if sf else None
                    print('   face surf',{a:str(b)[:60] for a,b in (sf or {}).items()})
            break
        n+=1
    last_end=end; pos=end
