import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ["RVT_GEOM"]="1"
import rvt_xcache, rvt_scan as S
f=sys.argv[1]
x=rvt_xcache.get_x(f); recs={}
for (e,c),r in x["recs"].items(): recs.setdefault(e,r)
o,cls,ids=S.load(f)
tot=0; cc=collections.Counter(); nf=0
for e,r in recs.items():
    if r["class"]=="Family":
        fd=r["fields"].get("m_oFamDoc")
        if not fd: continue
        nf+=1
        for p in fd["obj"]["m_big2SmallMap2"]:
            s=int(p["second"]["m_id"]); tot+=1
            cc[recs[s]["class"] if s in recs else ("<missing inTable>" if s in ids else "<missing notInTable>")]+=1
print("families",nf,"mapped elements",tot); print(cc.most_common(25))
