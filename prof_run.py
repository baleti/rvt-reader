import sys,cProfile,pstats,io,time
sys.path.insert(0,'/home/user1/rvt-research')
import rvt2text
f=sys.argv[1]; pr=cProfile.Profile(); t=time.time()
pr.runcall(rvt2text.run,f,30000)
print(f,'wall(profiled)',round(time.time()-t,1),'s')
for key in ('cumulative','tottime'):
    s=io.StringIO(); pstats.Stats(pr,stream=s).sort_stats(key).print_stats(16); print(s.getvalue()[:2600])
