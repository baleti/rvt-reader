import os,signal,sys
me=os.getpid(); pp=os.getppid(); pats=sys.argv[1:]
for p in os.listdir('/proc'):
    if not p.isdigit() or int(p) in (me,pp): continue
    try: cl=open('/proc/%s/cmdline'%p,'rb').read().decode(errors='replace').replace('\0',' ')
    except Exception: continue
    if 'killproc' in cl or 'zsh' in cl.split(' ')[0] or 'claude' in cl[:40]: continue
    if any(x in cl for x in pats):
        print('kill',p,cl[:70])
        try: os.kill(int(p),signal.SIGTERM)
        except Exception as e: print(e)
