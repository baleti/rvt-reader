import json,glob,re,collections,os,sys
d=sys.argv[1] if len(sys.argv)>1 and not sys.argv[1].startswith('-') else 'cov3'
per=collections.defaultdict(lambda:[0,0,0,0]); err=collections.defaultdict(collections.Counter)
for f in sorted(glob.glob(d+'/*.json')):
    try: r=json.loads(open(f).read())
    except Exception: continue
    m=re.search(r'corpus_(\d{4})_',os.path.basename(f)); y=m.group(1) if m else 'other'
    per[y][0]+=r['records']; per[y][1]+=r['complete']; per[y][2]+=r['exact_fit']; per[y][3]+=1
    for (c,e),n in r['top_err']: err[y][(c,e)]+=n
print('year files  records   complete%  exact-fit%')
for y in sorted(per):
    a=per[y]; print(f'{y}  {a[3]:3d} {a[0]:9d}   {100*a[1]/max(a[0],1):6.2f}    {100*a[2]/max(a[0],1):6.2f}')
if '-v' in sys.argv:
    for y in sorted(err): print(y,err[y].most_common(5))
