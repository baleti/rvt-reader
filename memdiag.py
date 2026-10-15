import sys,os,resource; sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
def rss(t): print(t,'maxrss %.2f GB'%(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20),flush=True)
f=sys.argv[1]; import rvt_xcache,gc,rvt_elemmesh as EM
d=EM.Doc(f); rss('Doc'); x=rvt_xcache.get_x(f); rss('get_x (%d recs)'%len(x['recs'])); c={k:v for k,v in x['recs'].items() if 'Curve' in k[1]}; del x; gc.collect(); rss('filtered')
d.cls(1); rss('census')
for e in list(d.res)[:3000:10]:
    try: EM.element_mesh(d,e)
    except Exception: pass
rss('meshed')
