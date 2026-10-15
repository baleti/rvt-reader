import sys,glob,struct,collections,re
sys.path.insert(0,'/home/user1/rvt-research')
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
def failures(path, limit_ids=None):
    o,cls,ids=S.load(path); IDW=S.id_size(cls); IDF='<I' if IDW==4 else '<Q'; sch=D.Schema(cls); dec=D.Dec(sch,idsize=IDW); et=I.element_tags(cls)
    ok=set(); fails=collections.defaultdict(list)
    for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
        for si,chunk in enumerate(T.segments(o.openstream(pn).read())):
            for i in range(0,len(chunk)-20):
                eid=struct.unpack_from('<I',chunk,i+4)[0]
                if eid not in ids: continue
                tag=struct.unpack_from('<H',chunk,i+16)[0]
                if tag not in et: continue
                try:
                    r,q=dec.record(chunk,i)
                    if r['fields'].get('m_id')==eid: ok.add(eid)
                except Exception as e:
                    fails[eid].append((sch.name(tag),str(e)))
    return cls,ids,ok,fails
if __name__=='__main__':
    cls,ids,ok,fails=failures(glob.glob(sys.argv[1])[0])
    bad=[e for e in fails if e not in ok]
    print(len(ids),'ids;',len(ok),'decoded;',len(bad),'only-failing')
    sig=collections.Counter()
    for e in bad:
        c,m=fails[e][-1]
        m2=re.sub(r'\d+','N',m.split('@@')[-1].split(' at ')[0].strip()) if '@@' in m else re.sub(r'\d+','N',m)[:60]
        sig[(c,m2)]+=1
    for (c,m),n in sig.most_common(30): print(n,c,'|',m)
