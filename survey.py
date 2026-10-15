import sys,glob,re,olefile,zlib,os
sys.path.insert(0,'/home/user1/rvt-research')
from rvt_extract import inflate_chunks
for f in sorted(glob.glob('samples/*'))+glob.glob('F106*.rvt'):
    try: o=olefile.OleFileIO(f)
    except Exception as e: print(os.path.basename(f)[:40],'NOT OLE',e); continue
    ss=['/'.join(e) for e in o.listdir(streams=True)]
    bi=o.openstream('BasicFileInfo').read() if 'BasicFileInfo' in ss else b''
    t=bi.decode('utf-16le','ignore') if bi[1:2]==b'\x00' or True else ''
    ver=re.findall(r'(?:Autodesk Revit|Format|^|\s)(20\d\d)',t)[:2] or re.findall(r'20\d\d',t)[:2]
    build=re.findall(r'\d{8}_\d{4}\([^)]*\)',t)
    ok=[];bad=[]
    for s in ss:
        if s.startswith(('Formats/','Global/','Partitions/')):
            d=o.openstream(s).read(); r=inflate_chunks(d)
            (ok if len(r)>0 else bad).append(s.split('/')[-1])
    print(f"{os.path.basename(f)[:34]:34} ver={ver} build={build[:1]} streams={len(ss)} ok={len(ok)} bad={bad}")
    print('     ',[s for s in ss if not s.startswith('Partitions')])
