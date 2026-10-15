import sys,os,resource; sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
def rss(t): print(t,'maxrss %.2f GB'%(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20),flush=True)
import rvt_entities as E_
x=E_.extract(sys.argv[1],want_all=True,slim=lambda c: 'Curve' in c or c in ('DetailLine','ModelLine','SymbolicCurve')); rss('slim extract %d recs'%len(x['recs']))
