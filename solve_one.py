import sys,os,struct,time
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I, rvt_solve as V
p=sys.argv[1]; want=int(sys.argv[2]); budget=int(sys.argv[3]) if len(sys.argv)>3 else 200000
o,cls,ids=S.load(p); W=S.id_size(cls); F='<I' if W==4 else '<Q'; sch=D.Schema(cls); et=I.element_tags(cls)
dec=D.Dec(sch,idsize=W); dec.STOP=()
sv=V.Solver(dec,ids,et,W,F,budget=budget); sv.nest=os.environ.get('NEST','depth'); sv.rev=os.environ.get('REV')=='1'; dec.backref=os.environ.get('BACKREF','1')=='1'
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    for chunk in T.segments(o.openstream(pn).read()):
        for i in range(0,len(chunk)-24):
            if struct.unpack_from(F,chunk,i+4)[0]==want and struct.unpack_from('<H',chunk,i+12+W)[0] in et:
                t=time.time(); r=sv.solve(chunk,i,D.load_hints())
                print('class',sch.name(struct.unpack_from('<H',chunk,i+12+W)[0]),'end',(r[0]-i) if r and r[0] else None,'nodes',sv.nodes,'secs',round(time.time()-t,1),'dead',len(sv.dead))
                for n,o2 in reversed(sv.chosen): print('  ',n,o2)
                raise SystemExit
