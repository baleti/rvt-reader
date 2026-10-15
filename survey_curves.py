import sys,os,collections,json
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E
rvt=sys.argv[1]
x=E.extract(rvt,want_all=True)
ks=collections.Counter(); ex={}
def walk(o,cl):
    if isinstance(o,dict):
        if 'm_endParams' in o or 'm_origin' in o:
            key=(cl,tuple(sorted(k for k,v in o.items() if v is not None)))
            ks[key]+=1; ex.setdefault(key,o)
        for v in o.values(): walk(v,cl)
    elif isinstance(o,list):
        for v in o: walk(v,cl)
for (e,c),r in x['recs'].items(): walk(r['fields'],c)
for k,n in ks.most_common(40): print(n,k[0],k[1])
json.dump({'|'.join([k[0]]+list(k[1])):str(v)[:600] for k,v in ex.items()},open('survey_ex.json','w'),indent=1)
