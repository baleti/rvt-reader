"""Per-element face material check: set/multiset of Revit's FMAT material ids vs ours (material_for_face over element_brep faces incl. instances)"""
import sys, os, collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_materials as RM, rvt_elemmesh as E
f=sys.argv[1]; y=f.split('/')[-2]; tsv='/home/user1/rvt-research/gt_mat/%s_%s.tsv'%(y,os.path.basename(f))
want=collections.defaultdict(collections.Counter)
for l in open(tsv):
    t=l.rstrip('\n').split('\t')
    if t[0] in ('FMAT','FMATPAINTED'):
        eid=int(t[1].split('.')[0]); mid=t[2].split('=')[1]; want[eid][int(mid) if mid not in ('','-1') else None]+=1
d=E.Doc(f); n=same=sub=0; bad=[]
for eid,w in list(want.items())[:int(sys.argv[2]) if len(sys.argv)>2 else 10**9]:
    br=E.element_brep(d,eid); c=collections.Counter()
    def add(faces,sid):
        for fc in faces: c[RM.material_for_face(f,sid,fc['handle'])]+=1
    add(br['faces'],eid)
    def rec(insts):
        for i in insts: add(i['faces'],i['symbol_id']); rec(i.get('instances',[]))
    rec(br['instances']); n+=1
    ws=set(w); cs=set(c)
    if ws==cs: same+=1
    elif ws<=cs: sub+=1
    else: bad.append((eid,dict(w),dict(c)))
print('elements',n,'same material set',same,'oracle set is subset of ours',sub,'other',len(bad))
for b in bad[:6]: print(b)
