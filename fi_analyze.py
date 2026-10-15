import json,glob,collections,sys
cl=sys.argv[1] if len(sys.argv)>1 else 'FamilyInstance'
kinds={}
rows=[]
for f in sorted(glob.glob('fidfull3/*.jsonl')):
    b=f.split('/')[-1].replace('.jsonl','.tsv'); k={}
    for ln in open('gt4/'+b,encoding='utf-8'):
        if ln.startswith('E\t'): q=ln.split('\t'); k[int(q[1])]=q[7].strip() if len(q)>7 else ''
    for l in open(f):
        r=json.loads(l)
        if r['cls']==cl and k.get(r['eid'])!='type' and r['status']=='mesh' and r.get('gtv'): r['f']=b[:12]; rows.append(r)
c=collections.Counter(); ex=collections.defaultdict(list)
for r in rows:
    if r.get('vol') is None: key=('open', r['source'], 'unsup' if r.get('unsup') else '')
    else:
        ratio=r['vol']/r['gtv']; key=('closed ok',r['source']) if abs(ratio-1)<=0.02 else ('closed off %s'%('x2' if abs(ratio-2)<.05 else 'x0.5' if abs(ratio-.5)<.03 else '<0.9' if ratio<.9 else '>1.1' if ratio>1.1 else '2-10%'), r['source'])
    c[key]+=1; ex[key].append((r['f'],r['eid'],round(r['vol'],3) if r.get('vol') else None,round(r['gtv'],3),r['ntri'],round(r['iou'] or 0,3)))
for k,n in c.most_common(): print(n,k,ex[k][:2])
