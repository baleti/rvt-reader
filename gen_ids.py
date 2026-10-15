import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ["RVT_GEOM"]="1"
import rvt_xcache
f=sys.argv[1]; x=rvt_xcache.get_x(f); recs={}
for (e,c),r in x["recs"].items(): recs.setdefault(e,r)
tot=collections.Counter(); seen=collections.Counter()
for e,r in recs.items():
    if r["class"]!="FamilySymbol": continue
    gt=r["fields"].get("m_pGeomTable"); 
    if not gt: continue
    tb=(gt.get("obj",gt) or {}).get("m_table") or []
    ids=[int(t["m_geomGeneratorId"]) for t in tb if isinstance(t,dict) and "m_geomGeneratorId" in t]
    for i in ids:
        tot["ids"]+=1
        if i==0xffffffff or i==0xffffffffffffffff: tot["none"]+=1
        elif i in recs: tot["in recs"]+=1; seen[recs[i]["class"]]+=1
        else: tot["unknown id"]+=1
print(dict(tot)); print(seen.most_common(10))
sym=[e for e,r in recs.items() if r["class"]=="FamilySymbol"][:3]
for e in sym:
    gt=recs[e]["fields"].get("m_pGeomTable"); tb=(gt.get("obj",gt) or {}).get("m_table") or []
    print(e,[int(t["m_geomGeneratorId"]) for t in tb][:12])
