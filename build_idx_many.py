import sys,os,collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import g103_get as GG
tot=collections.Counter()
for f in sys.argv[1:]:
    r=GG.cached_index(f); c=collections.Counter()
    for i,v in r.items():
        for k in ('Plane','CylSurf','ConeSurf','RuledSurf','SurfRev','HermiteSurf','OffsetSurf','SharedSurface','TempImportNurbsSurf','GNurbSpline','GHermiteSpline','GEllipse','GArc','GCylindricalHelix','GOffsetCurve','Geometry','GPolyMesh'):
            if v['bodies'].get(k): c[k]+=v['bodies'][k]
    print(os.path.basename(f),len(r),dict(c),flush=True)
