import sys,glob,os,re,collections,json,time
sys.path.insert(0,'/home/user1/rvt-research')
import rvt_fail as F
p=sys.argv[1]; t=time.time()
try:
    cls,ids,ok,fails=F.failures(p)
    bad=[e for e in fails if e not in ok]
    sig=collections.Counter()
    for e in bad:
        c,m=fails[e][-1]; sig[(c,re.sub(r'\d+','N',m.split('@@')[-1].split(' at ')[0].strip())[:70] if '@@' in m else re.sub(r'\d+','N',m)[:50])]+=1
    nofind=len(ids)-len(ok)-len(bad)
    r={'file':os.path.basename(p),'ids':len(ids),'decoded':len(ok),'failing':len(bad),'never_candidate':nofind,'secs':round(time.time()-t),'top':[(list(k),v) for k,v in sig.most_common(6)]}
except Exception as e: r={'file':os.path.basename(p),'error':repr(e)[:200]}
print(json.dumps(r))
