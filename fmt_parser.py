#!/usr/bin/env python3
"""Strict recursive-descent parser for decompressed Formats/Latest. Experimental grammar, see NOTES.md."""
import struct, sys, re
IDENT = re.compile(rb'[A-Za-z_][A-Za-z0-9_:<>, *&]*')
class Bad(Exception): pass
class P:
    def __init__(s,b,T=(6,4,6),guid=True): s.b=b; s.p=0; s.classes=[]; s.trace=[]; s.T=T; s.ctx='top'; s.guid=guid
    def u16(s): v=struct.unpack_from('<H',s.b,s.p)[0]; s.p+=2; return v
    def u32(s): v=struct.unpack_from('<I',s.b,s.p)[0]; s.p+=4; return v
    def name(s,w):
        L=s.u16() if w==2 else s.u32()
        if not (1<=L<=120) or not IDENT.fullmatch(s.b[s.p:s.p+L]): raise Bad(f'bad name len={L} at {s.p}')
        n=s.b[s.p:s.p+L].decode(); s.p+=L; return n
    def record(s,ctx='top'):
        start=s.p; n=s.name(2); c={'name':n,'off':start,'fields':[]}; s.classes.append(c)
        c['parent']=s.u16(); c['X']=s.u16()
        if c['parent']&0x8000: c['parent_def']=s.record('parent')['name']
        c['Y']=s.u16(); cnt=s.u32(); c['count']=cnt
        for _ in range(cnt): c['fields'].append(s.field())
        if s.guid:
            n=s.u32()
            if n>60000: raise Bad(f'bad guid count {n} at {s.p}')
            c['guids']=[s.b[s.p+16*i:s.p+16*i+16].hex() for i in range(n)]
            s.p+=16*n
            if s.p>len(s.b): raise Bad('past end')
        if ctx!='field': c['M']=s.u16()
        return c
    def ftype(s,f):
        T=s.u32(); kind=T&0xff; flags=(T>>8)&0xff; f.setdefault('types',[]).append(T)
        if flags&0x10 and not flags&0x40:
            f['n']=s.u32(); f.setdefault('ns',[]).append(f['n'])
        else: f.setdefault('ns',[]).append(None)
        if kind==0x0e and (flags&0x0f)==0:
            ref=s.u16(); f['ref']=ref
            if ref&0x8000: s.u16(); f['def']=s.record('field')['name']
        elif kind==0x0d:
            f['k']=s.u32(); f['mark']=s.b[s.p] if hasattr(s,'b') else None; s.p+=1; s.ftype(f)
            if (f['types'][-1]&0xff)==0x0e: f['ref2']=s.u16()
    def field(s):
        n=s.name(4); f={'name':n}; s.ftype(f); f['T']=f['types'][0]; return f
def run(path,T=(6,4,6),quiet=False):
    b=open(path,'rb').read(); p=P(b,T); p.p=2
    try:
        while p.p<len(b):
            if not any(b[p.p:]): break      # trailing zero terminator
            p.record()
        if not quiet: print('OK consumed',p.p,'of',len(b),'classes',len(p.classes))
    except Exception as e:
        if not quiet: print('FAIL',e,'at',p.p,'of',len(b),'classes so far',len(p.classes))
        if not quiet: print(' last:',[ (c['name'],c.get('count'),[f['name'] for f in c['fields']][-3:]) for c in p.classes[-4:]])
        if not quiet: print(' ctx:',b[max(0,p.p-48):p.p].hex(),'|',b[p.p:p.p+48].hex())
    return p
if __name__=='__main__': run(sys.argv[1])


def _parse_raw(b):
    """Parse a decompressed Formats/Latest stream. Tries the layout with and without per-class GUID tables;
    returns (classes, variant) for the variant that consumes the whole stream (trailing zeros allowed)."""
    last=None
    for guid in (True,False):
        p=P(b,(6,4,6),guid); p.p=2
        try:
            while p.p<len(b):
                if not any(b[p.p:]): break
                p.record()
            return p.classes,{'guid_tables':guid}
        except Exception as e: last=(e,p)
    raise Bad(f'no layout fits: {last[0]} (classes so far {len(last[1].classes)})')


import hashlib as _h, os as _os, pickle as _pk
_CD = _os.path.expanduser('~/.cache/rvt-schema')
def parse(b):
    """cached by content hash (schemas are identical across files of one Revit build): Formats/Latest parse costs ~0.5 s each"""
    if _os.environ.get('RVT_NOCACHE'): return _parse_raw(b)
    k = _h.sha1(bytes(b)).hexdigest(); fn = _os.path.join(_CD, 'fmt-' + k + '.pkl')
    try:
        with open(fn, 'rb') as fh: return _pk.load(fh)
    except Exception: pass
    r = _parse_raw(b)
    try:
        _os.makedirs(_CD, exist_ok=True); tmp = fn + '.%d.tmp' % _os.getpid()
        with open(tmp, 'wb') as fh: _pk.dump(r, fh, protocol=5)
        _os.replace(tmp, fn)
    except Exception: pass
    return r
