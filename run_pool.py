import sys,os,glob,subprocess
from concurrent.futures import ThreadPoolExecutor
script,outdir=sys.argv[1],sys.argv[2]; nw=int(sys.argv[3]) if len(sys.argv)>3 else 4
os.makedirs(outdir,exist_ok=True)
os.environ.setdefault('XDG_RUNTIME_DIR','/run/user/%d'%os.getuid())
jobs=[]
for g in sorted(glob.glob('gt4/*.tsv')):
    b=os.path.basename(g)[:-4]; y,rest=b.split('_',1)
    f=glob.glob(f'corpus/{y}/{rest}')
    if f: jobs.append((f[0],g,b))
MEM=os.environ.get('POOL_MEM','5G')
def run(j):
    f,g,b=j
    if os.path.exists(f'{outdir}/{b}.out') and os.path.getsize(f'{outdir}/{b}.out')>0: return
    with open(f'{outdir}/{b}.out','w') as o, open(f'{outdir}/{b}.err','w') as e:
        try: subprocess.run(['systemd-run','--user','--scope','-q','-p','MemoryMax='+MEM,'-p','MemorySwapMax=0','nice','-n','10',os.environ.get('PYBIN','/home/user1/occ-env/bin/python'),script,f,g],stdout=o,stderr=e,timeout=1500)
        except subprocess.TimeoutExpired: o.write('')
with ThreadPoolExecutor(nw) as ex: list(ex.map(run,jobs))
open(f'{outdir}/_DONE','w').write('done')
