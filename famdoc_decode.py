import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ["RVT_GEOM"]="1"
import rvt_xcache, rvt_scan as S, rvt_entities as E
f=sys.argv[1]
x=rvt_xcache.get_x(f); recs={}
for (e,c),r in x["recs"].items(): recs.setdefault(e,r)
small=set()
for e,r in recs.items():
    if r["class"]=="Family" and r["fields"].get("m_oFamDoc"):
        for p in r["fields"]["m_oFamDoc"]["obj"]["m_big2SmallMap2"]: small.add(int(p["second"]["m_id"]))
print("small ids",len(small))
# extend idarr via monkeypatching S.load
_old=S.load
def load2(path):
    o,cls,ids=_old(path); return o,cls,ids|small
S.load=load2; E.S.load=load2
y=E.extract(f,want_all=True,only_ids=small)
cc=collections.Counter(c for (e,c) in y["recs"]); print("decoded",len(y["recs"]),cc.most_common(25))
bad=collections.Counter(r["error"][:40] for r in y["recs"].values() if not r["complete"]); print("incomplete",sum(bad.values()),bad.most_common(3))
