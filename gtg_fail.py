import json,glob,sys
for f in sorted(glob.glob(sys.argv[1])):
    for l in open(f):
        r=json.loads(l)
        if len(sys.argv)>2 and r['cls'] not in sys.argv[2].split(','): continue
        if r['status']!='mesh': print(f.split('/')[-1][:-6],r['eid'],r['cls'],r['status'],'rvol %.4f'%r['rvol']); continue
        okv=r.get('mvol') is not None and ((r['rvol']>0 and abs(r['mvol']/r['rvol']-1)<=.02) or (r.get('sheet') and abs(r['rvol'])<1e-6))
        oka=r.get('marea') is not None and r['rarea']>0 and abs(r['marea']/r['rarea']-1)<=.03
        okc=None
        if r.get('mcent') and r.get('rbb'):
            dg=sum((x-y)**2 for x,y in zip(r['rbb'][0],r['rbb'][1]))**.5
            okc=any(ref and sum((x-y)**2 for x,y in zip(r['mcent'],ref))**.5<=.01*dg for ref in (r.get('rcent'),r.get('rcent_world'),r.get('rcent_chain')))
        if r.get('sheet') and r.get('mbb') and r.get('rbb'):
            dg=sum((x-y)**2 for x,y in zip(r['rbb'][0],r['rbb'][1]))**.5 or 1.0
            okc=max(abs(a-b) for a,b in zip(r['mbb'][0]+r['mbb'][1],r['rbb'][0]+r['rbb'][1]))<=0.01*dg
        if not (okv and oka and okc):
            print(f.split('/')[-1][:-6],r['eid'],r['cls'],r['source'],'closed',r['closed'],'vol %.4f/%s'%(r['rvol'],r.get('mvol') and round(r['mvol'],4)),'area %.3f/%s'%(r['rarea'],r.get('marea') and round(r['marea'],3)),'cent',okc)
