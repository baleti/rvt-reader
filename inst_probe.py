import sys,struct,glob,json,collections
sys.path.insert(0,'/home/user1/rvt-research')
import olefile, rvt2text as T
def load_parts(p):
    o=olefile.OleFileIO(p); parts=[]
    for pn in [x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')]:
        parts+= [(pn,c) for c in T.segments(o.openstream(pn).read())]
    return parts
def gt_of(pat,kind):
    f=glob.glob('/home/user1/rvt-research/groundtruth2/'+pat)[0]
    o=json.load(open(f,encoding='utf-8-sig'))['output']
    return [l.split('\t') for l in o.splitlines() if l.startswith(kind)]
