import sys,zlib,olefile,struct,os,collections,pickle
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import rvt2text as T, rvt_scan as S, rvt_decode as D
f=sys.argv[1]; out_pkl=sys.argv[2]; maxrec=int(sys.argv[3]) if len(sys.argv)>3 else 10**9
o,cls,ids=S.load(f); W=S.id_size(cls); sch=D.Schema(cls); dec=D.Dec(sch,idsize=W)
import rvt_es as ES
try: dec.es_schemas=ES.load(f)[0]
except Exception: dec.es_schemas={}
import g103_get as GG
res={}; stats=collections.Counter(); errs=collections.Counter()
for pn in sorted(n for n in ['/'.join(e) for e in o.listdir(streams=True)] if n.startswith('Partitions/')):
    P=GG.Part(o,pn)
    for gi,(ch,ks) in enumerate(P.groups):
        if ch!=103: continue
        out=P.group(gi); buf=b'\x00\x00\x00\x00'+out; p=0; stats['groups']+=1
        while p<len(buf)-30:
            try: r,q=dec.record(buf,p,False)
            except Exception as e: errs[repr(e)[:60]]+=1; break
            stats['records']+=1
            if r['complete']: stats['complete']+=1
            fl=r['fields']
            res[r['id']]=dict(pn=pn,seg=gi,off=p,bbox=fl.get('m_bBox'),tight=fl.get('m_tightbBox'),etype=fl.get('m_gElemType'),bodies=dict(collections.Counter(r['bodies'])),size=q-p,complete=r['complete'])
            p=q
            if stats['records']>=maxrec: break
        if stats['records']>=maxrec: break
pickle.dump(res,open(out_pkl,'wb'))
print(dict(stats),errs.most_common(3),len(res))
