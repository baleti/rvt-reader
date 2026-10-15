import sys,glob,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import olefile, fmt_parser as fp, export_schemas as ES
from rvtfmt import inflate_stream
def load_schema(p):
    o=olefile.OleFileIO(p); cls,_=fp.parse(inflate_stream(o.openstream('Formats/Latest').read())[1]); return cls
def tn(cls,f):
    t=ES.tname(f['types'],f)
    if 'ref' in f:
        r=f['ref']; inl=bool(r&0x8000); r&=0x7fff
        t+=' -> '+(cls[r-12]['name'] if 12<=r<12+len(cls) else '#%d'%r)+(' (inline)' if inl else '')
    return t
def show(cls,n):
    by={c['name']:i for i,c in enumerate(cls)}
    c=cls[by[n]]; pt=c['parent']&0x7fff
    print('##',n,'tag',by[n]+12,'parent',(cls[pt-12]['name'] if pt else '-'),'X',c['X'],'Y',c['Y'],'M',c.get('M'))
    for f in c['fields']: print('    ',f['name'],tn(cls,f),'T=%#x'%f['T'])
if __name__=='__main__':
    cls=load_schema(glob.glob(sys.argv[1])[0])
    for n in sys.argv[2:]: show(cls,n)
