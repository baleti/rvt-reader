import sys,zlib,olefile,struct,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import rvt2text as T, rvt_scan as S, rvt_decode as D
try: sys.path.append(os.path.expanduser('~/src/rvt-core/python')); import rvt_fast as _F
except Exception: _F = None
_cache={}
def load_dec(f):
    o,cls,ids=S.load(f); W=S.id_size(cls); sch=D.Schema(cls); dec=D.make_dec(sch,idsize=W)
    import rvt_es as ES
    try: dec.es_schemas=ES.load(f)[0]
    except Exception: dec.es_schemas={}
    return o,dec
class Part:
    """one partition stream: segment (gzip member) offsets + channel + continuation flags indexed once; members inflated on demand;
    groups = consecutive segments joined while the 'continues into next' flag (bit 1) is set"""
    def __init__(s,o,pn):
        s.data=T.strip_pages(o.openstream(pn).read()); s.members=[]; s.lru=collections.OrderedDict(); mv=memoryview(s.data)
        GZ=T.GZ; pos=0; last_end=0
        while True:
            i=s.data.find(GZ,pos)
            if i<0: break
            d=zlib.decompressobj(-15)
            try: out=d.decompress(mv[i+10:])
            except zlib.error: pos=i+4; continue
            end=len(s.data)-len(d.unused_data); gap=s.data[last_end:i]
            ch=struct.unpack_from('<Q',gap,len(gap)-8)[0] if len(gap)>=8 else None
            fl=struct.unpack_from('<I',gap,len(gap)-24)[0] if len(gap)>=24 else 4
            s.members.append((i,ch,fl)); last_end=end; pos=end
        s.groups=[]; cur=None
        for k,(i,ch,fl) in enumerate(s.members):
            if cur is None: cur=(ch,[])
            cur[1].append(k)
            if not (fl&2): s.groups.append(cur); cur=None
        if cur: s.groups.append(cur)
    def seg(s,k):
        key=('s',k)
        if key in s.lru: s.lru.move_to_end(key); return s.lru[key]
        i,ch,fl=s.members[k]; d=zlib.decompressobj(-15); out=d.decompress(memoryview(s.data)[i+10:])
        s.lru[key]=out
        if len(s.lru)>8: s.lru.popitem(last=False)
        return out
    def group(s,gi):
        key=('g',gi)
        if key in s.lru: s.lru.move_to_end(key); return s.lru[key]
        ch,ks=s.groups[gi]; out=b''.join(s.seg(k) for k in ks); s.lru[key]=out
        if len(s.lru)>8: s.lru.popitem(last=False)
        return out
def part(o,pn):
    key=(id(o),pn)
    if key not in _cache: _cache[key]=Part(o,pn)
    return _cache[key]
def get_record(f,info,o=None,dec=None):
    if _F and _F.on(): return _F.get_record(f, info, o, dec)
    if o is None: o,dec=load_dec(f)
    out=part(o,info['pn']).group(info['seg']); buf=b'\x00\x00\x00\x00'+out
    r,q=dec.record(buf,info['off'],False); return r

def build_index(f, maxrec=10**9):
    if _F and _F.on(): return _F.build_index(f, maxrec)
    """{element id: {pn, seg(group index), off, bbox, tight, etype, bodies, size, complete}} for every channel-103 record"""
    o, dec = load_dec(f); res = {}
    for pn in sorted(n for n in ['/'.join(e) for e in o.listdir(streams=True)] if n.startswith('Partitions/')):
        P = Part(o, pn)
        for gi, (ch, ks) in enumerate(P.groups):
            if ch != 103: continue
            out = P.group(gi); buf = b'\x00\x00\x00\x00' + out; p = 0
            while p < len(buf) - 30:
                try: r, q = dec.record(buf, p, False)
                except Exception: break
                fl = r['fields']
                res[r['id']] = dict(pn=pn, seg=gi, off=p, bbox=fl.get('m_bBox'), tight=fl.get('m_tightbBox'), etype=fl.get('m_gElemType'), bodies=dict(collections.Counter(r['bodies'])), size=q - p, complete=r['complete'])
                p = q
    return res

def cached_index(f):
    import pickle, hashlib
    st = os.stat(f); k = hashlib.sha1(('%s|%d|%d|%d' % (f, st.st_size, int(st.st_mtime), int(os.path.getmtime(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_decode.py'))))).encode()).hexdigest()
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xcache'); os.makedirs(d, exist_ok=True); fn = os.path.join(d, k + '.g103.pkl')
    if os.path.exists(fn): return pickle.load(open(fn, 'rb'))
    res = build_index(f); pickle.dump(res, open(fn + '.tmp', 'wb'), protocol=5); os.replace(fn + '.tmp', fn); return res
