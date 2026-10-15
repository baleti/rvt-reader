import sys,os,collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E
x=E.extract(sys.argv[1],want_all=True)
tot=collections.Counter(); face=collections.Counter(); bod=collections.defaultdict(collections.Counter)
for (e,c),r in x['recs'].items():
    tot[c]+=1
    b=collections.Counter(r['bodies'])
    if b.get('Face'): face[c]+=1
    for k,v in b.items():
        if k in('Face','Edge','EdgeLoop','Plane','Geometry','GLine','GGroup','GFilling','Cylinder','Cone','Torus','Line','Arc','Spline','BRep','Body','Shell','Solid','FacetedTopology11'): bod[c][k]+=v
for c,n in face.most_common(25): print(c,n,'of',tot[c],dict(bod[c]))
print('classes with any geometry bodies, no Face:',[ (c,tot[c]) for c in bod if c not in face][:15])
