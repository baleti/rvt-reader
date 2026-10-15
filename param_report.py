"""per-year parameter reproduction (OBJECTIVES.md #2): BEFORE dir (old rules) vs AFTER dir (current rules), exact and exact+approx (Double within 1e-4),
and the bucket breakdown of what is still not reproduced: (a) lookup candidates, (b) geometry-derived, (c) MEP engine, (d) other.
usage: param_report.py [BEFORE_DIR AFTER_DIR [TOPN]]   (default pout_before pout)"""
import json,glob,os,re,collections,sys
sys.path.insert(0,'/home/user1/rvt-research')
exec(open('/home/user1/rvt-research/agg_pout.py').read().split("files=sorted")[0])
corp={os.path.basename(p):p.split('/')[-2] for p in glob.glob('/home/user1/rvt-research/corpus/*/*')}
bdir,adir=(sys.argv[1],sys.argv[2]) if len(sys.argv)>2 else ('pout_before','pout'); topn=int(sys.argv[3]) if len(sys.argv)>3 else 25
def load(d):
    st=collections.defaultdict(collections.Counter); un=collections.defaultdict(collections.Counter); ub=collections.defaultdict(collections.Counter); files=collections.Counter()
    for f in glob.glob(d+'/*.json'):
        j=json.load(open(f)); y=corp.get(j['file'],'?'); files[y]+=1
        for k,n in j['rows']:
            cls,gcls,pid,nm,stg,s=k; st[y][s]+=n; st[y]['ALL']+=n; st[y][stg+':'+s]+=n; st[y][stg]+=n
            if s not in ('ok','approx'): b=bucket(nm,stg); un[b][(nm,stg)]+=n; ub[y][b]+=n
    return st,un,ub,files
B,_,_,_=load(bdir); A,un,ub,files=load(adir)
pc=lambda c,k,t='ALL': 100*c[k]/max(1,c[t])
print('year files    values  before%  exact%  exact+approx%   Double / Integer / String / ElementId exact%   not reproduced: a_lookup b_geom c_mep d_other (% of values)')
for y in sorted(A):
    a=A[y]; b=B.get(y)
    print('%s %4d %9d   %6s  %6.1f   %6.1f        %s     %s'%(y,files[y],a['ALL'],'%.1f'%pc(b,'ok') if b and b['ALL'] else 'n/a',pc(a,'ok'),100*(a['ok']+a['approx'])/max(1,a['ALL']),
        ' / '.join('%.1f'%pc(a,s+':ok',s) for s in ('Double','Integer','String','ElementId')),
        ' '.join('%.1f'%(100*ub[y][k]/max(1,a['ALL'])) for k in ('a_lookup_candidate','b_geom','c_mep','d_other'))))
T=collections.Counter()
for y in A: T.update(A[y])
print('ALL  %4d %9d            %6.1f   %6.1f'%(sum(files.values()),T['ALL'],pc(T,'ok'),100*(T['ok']+T['approx'])/max(1,T['ALL'])))
for bk in sorted(un):
    print('==',bk,sum(un[bk].values()))
    for (nm,stg),n in un[bk].most_common(topn): print('  %7d %s [%s]'%(n,nm,stg))
