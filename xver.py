import sys,glob,re,olefile,os,json,collections,zlib
sys.path.insert(0,'/home/user1/rvt-research')
from rvt_extract import inflate_chunks,u16
import parse_formats as pf
res={}
for f in sorted(glob.glob('samples/*'))+['F106-LAC724-MOD-AR-00061.rvt']:
    o=olefile.OleFileIO(f); rd=lambda s:o.openstream(s).read()
    bi=rd('BasicFileInfo').decode('utf-16le','ignore'); build=(re.findall(r'(\d{8})_\d{4}',bi) or ['?'])[0]
    fm=inflate_chunks(rd('Formats/Latest')); t=pf.scan(fm)
    cls=[x[2] for x in t if x[0]=='class']; fld=[x[2] for x in t if x[0]=='field']
    pt=inflate_chunks(rd('Global/PartitionTable')); views=[s for s in set(u16(pt)) if s.startswith(('View "','Family'))]
    dit=collections.Counter(u16(inflate_chunks(rd('Global/DocumentIncrementTable'))))
    part=sum(len(inflate_chunks(rd(s))) for s in ['/'.join(e) for e in o.listdir(streams=True)] if s.startswith('Partitions/'))
    res[f]=set(cls)
    print(f"{os.path.basename(f)[:30]:30} build={build} fmt={len(fm):7} classes={len(cls):4} fields={len(fld):5} views/fam={len(views):4} editors={len(dit):2} partitions_raw={part/1e6:6.1f}MB")
base=res['F106-LAC724-MOD-AR-00061.rvt']
print('\nclass-name overlap with 2025 file:')
for f,s in res.items(): print(f"  {os.path.basename(f)[:30]:30} {len(s&base)}/{len(s)} shared; only-here={len(s-base)}")
