import sys,os,resource,time,threading
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
def mon():
    while True:
        print('rss',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss//1024,'MB',flush=True); time.sleep(10)
threading.Thread(target=mon,daemon=True).start()
import rvt_entities as E
t=time.time(); x=E.extract(sys.argv[1],extra=('FamilyInstance',)); print('done',len(x['recs']),time.time()-t,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss//1024,'MB')
