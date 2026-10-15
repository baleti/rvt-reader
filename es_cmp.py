import sys,os,glob,time,olefile
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_NOCACHE']='1'
import rvt_es as ES, es_ref, rvt_decode as D, rvt_scan as S, fmt_parser as fp
from rvtfmt import inflate_stream
files=sorted(glob.glob('/home/user1/rvt-research/corpus/20*/*.rvt'))
import random; random.Random(3).shuffle(files)
ok=bad=0
for f in files[:int(sys.argv[1])]:
    o=olefile.OleFileIO(f); cls,_=fp.parse(inflate_stream(o.openstream('Formats/Latest').read())[1]); sch=D.Schema(cls); W=S.id_size(cls)
    d=inflate_stream(o.openstream('Global/Latest').read())[1]
    t=time.time(); new=ES.find_schemas(d,sch,W); t1=time.time()-t
    t=time.time(); ref=es_ref.find_ref(ES,D,d,sch,W); t2=time.time()-t
    if new==ref: ok+=1
    else: bad+=1; print('DIFF',f,len(new),len(ref))
    print(os.path.basename(f)[:30],'len',len(d),'new',round(t1,1),'ref',round(t2,1),'same' if new==ref else 'DIFF',flush=True)
print('same',ok,'diff',bad)
