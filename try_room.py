import sys,glob,struct,json
sys.path.insert(0,'/home/user1/rvt-research')
import rvt_decode as D, rvt_scan as S, rvt2text as T
p=glob.glob('/home/user1/rvt-research/samples/2015_1_*.rvt')[0]
o,cls,ids=S.load(p); sch=D.Schema(cls); dec=D.Dec(sch)
tag_room=sch.by['RoomElem']+12
for pn in [x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')]:
    if pn!='Partitions/874': continue
    for si,chunk in enumerate(T.segments(o.openstream(pn).read())):
        if si!=1: continue
        i=chunk.find(struct.pack('<I',527776))
        while i>=0:
            if struct.unpack_from('<H',chunk,i+12)[0]==tag_room:
                try:
                    r,q=dec.record(chunk,i-4); print('decoded',r['class'],r['id'],'consumed',q-(i-4),'bytes')
                    f=r['fields']
                    print(json.dumps({k:v for k,v in f.items() if k in ('m_point','m_levelId','m_id','m_assocLevelId','m_pParamValueSetAString','m_pParamValueSetDouble','m_pParamValueSetInt','m_pParamValueSetElementId')},default=str)[:3000])
                except D.Desync as e: print('DESYNC',e)
                break
            i=chunk.find(struct.pack('<I',527776),i+1)
