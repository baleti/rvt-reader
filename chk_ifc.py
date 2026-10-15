import sys,glob,os,json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import rvt_ifc
g=sys.argv[1]; b=os.path.basename(g)[:-4]; y,rest=b.split('_',1)
f=glob.glob('corpus/%s/%s'%(y,rest))
if not f: sys.exit()
out=rvt_ifc.ifc_guids(f[0]); ifc={}
for ln in open(g,encoding='utf-8'):
    q=ln.rstrip('\n').split('\t')
    if q[0]=='P' and len(q)>5 and q[2]=='-1019000': ifc[int(q[1])]=q[5]
ok=sum(1 for k,v in ifc.items() if out.get(k)==v)
print(json.dumps({'f':b,'y':y,'ok':ok,'n':len(ifc),'miss':sum(1 for k in ifc if k not in out)}))
