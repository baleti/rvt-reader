#!/usr/bin/env python3
"""Decode Global/Latest (the ADocument root object): [u32 class tag][fixed part][bodies breadth-first]."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olefile, fmt_parser as fp
from rvtfmt import inflate_stream
import rvt_decode as D, rvt_scan as S
def decode_global(path, stream='Global/Latest'):
    o = olefile.OleFileIO(path)
    cls, _ = fp.parse(inflate_stream(o.openstream('Formats/Latest').read())[1]); sch = D.Schema(cls); W = S.id_size(cls)
    pre, d, un = inflate_stream(o.openstream(stream).read())
    tag = struct.unpack_from('<I', d, 0)[0]
    dec = D.Dec(sch, idsize=W); dec.STOP = (); dec.visited = []; dec.err = None; dec.maxh = 2
    try:
        v, p, complete = dec.body(d, 4, tag, [sch.name(tag)], top=True)
    except D.Desync as e:
        return dict(error=str(e)[:300], partial=getattr(e, 'partial', None), len=len(d), cls=cls, sch=sch)
    return dict(class_=sch.name(tag), fields=v, end=p, len=len(d), complete=complete, err=dec.err, cls=cls, sch=sch, data=d)
if __name__ == '__main__':
    r = decode_global(sys.argv[1])
    print({k: r[k] for k in r if k in ('class_', 'end', 'len', 'complete', 'err', 'error')})
