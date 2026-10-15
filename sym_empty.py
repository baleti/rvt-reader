import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import rvt_elemmesh as EM, rvt_entities as E_
f=sys.argv[1]; doc=EM.Doc(f); x=E_.extract(f,extra=('FamilySymbol',))
c=collections.Counter(); ex={}
for (eid,cl),r in x['recs'].items():
    if eid not in doc.res: c['no record']+=1; continue
    b=doc.res[eid]['bodies']; m=EM.element_mesh(doc,eid)
    if m['tris']: c['mesh']+=1; continue
    k=('Geometry' if b.get('Geometry') else 'no Geometry', 'faces' if b.get('Face') else 'no faces', 'lines' if (b.get('GLine') or b.get('GArc')) else 'no lines', 'instance' if b.get('GInstance') else '')
    c[k]+=1; ex.setdefault(k,(eid,doc.res[eid]['size'],dict(list(b.items())[:8])))
for k,n in c.most_common(): print(n,k,ex.get(k))
