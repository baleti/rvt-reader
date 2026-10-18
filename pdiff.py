"""pdiff.py OLD_DIR NEW_DIR [name-substring]: per (class,name,stage) change in ok counts for files present in both dirs (NEW restricted); prints worse and better"""
import json,glob,os,sys,collections
a,b=sys.argv[1:3]; flt=sys.argv[3] if len(sys.argv)>3 else ''
def ld(d,fs):
    c=collections.Counter()
    for f in fs:
        j=json.load(open(os.path.join(d,f)))
        for k,n in j['rows']:
            c[(k[0],k[3],k[4],'ok' if k[5] in('ok',) else 'bad')]+=n
    return c
fs=[os.path.basename(f) for f in glob.glob(b+'/*.json') if os.path.exists(os.path.join(a,os.path.basename(f)))]
A=ld(a,fs); B=ld(b,fs); tot=0
keys=set(k[:3] for k in list(A)+list(B))
for k in sorted(keys):
    d=B[k+('ok',)]-A[k+('ok',)]
    if d and flt in k[1]: print('%+6d'%d,k); tot+=d
print('net',tot,'files',len(fs),'ok A',sum(v for k,v in A.items() if k[3]=='ok'),'ok B',sum(v for k,v in B.items() if k[3]=='ok'),'total',sum(A.values()))
