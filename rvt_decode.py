#!/usr/bin/env python3
"""Schema-driven decoder for Revit element instances (experimental).
Model (4-byte ElementId era):
  record  := [u32 A][u32 id][u32 s1][u32 s2][u16 class tag] fixed-part pointer-bodies
  fixed   := fields of the class chain, base class first, in schema order
  ref     (flags 00) -> embedded struct of the referenced class, inline
  ref<vector>/<set>  -> [u32 count] + count embedded structs
  ref* ** ***        -> slot: u32 0 = null | u32 0xffffffff + u16 class tag = object whose body comes AFTER the fixed part (deferred, slot order)
"""
import struct, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STRCAP = 4000000   # max string length in records; the extensible-storage schema scanner lowers it (rvt_es.find_schemas)

class Desync(Exception): pass

class EID(int):
    """an ElementId value (so later stages can tell ids from plain integers)"""
    __slots__ = ()
    def __repr__(s): return 'EID(%d)' % int(s)


import json as _json
def load_hints(path=None):
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_hints.json')
    try: return _json.load(open(path))
    except Exception: return {}


class Schema:
    def __init__(s, classes):
        s.c = classes; s.by = {c['name']: i for i, c in enumerate(classes)}; s._chain = {}
    def idx(s, tag): return tag - 12
    def chain(s, i):
        c = s._chain.get(i)
        if c is not None: return c
        c = s._chain[i] = s._chain_build(i); return c
    def _chain_build(s, i):
        out = []
        while True:
            out.append(i); pt = s.c[i]['parent'] & 0x7fff
            if not pt: break
            i = pt - 12
        return out[::-1]
    def name(s, tag):
        i = tag - 12
        return s.c[i]['name'] if 0 <= i < len(s.c) else '#%d' % tag

PRIM = {1: ('<B', 1), 2: ('<B', 1), 3: ('<h', 2), 4: ('<I', 4), 5: ('<I', 4), 6: ('<f', 4), 7: ('<d', 8), 0x0a: ('<H', 2), 0x0b: ('<Q', 8)}

class Dec:
    def __init__(s, schema, idsize=4, trace=False):
        s._gg = os.environ.get('RVT_GG', '0'); s._m = os.environ.get('RVT_M'); s.s = schema; s.idsize = idsize; s.maxh = 2; s.defined = {1, 2}; s.backref = True; s.es_schemas = {}; s.hints = load_hints(); s.trace = trace; s.log = []
    # ---- primitives
    def prim(s, b, p, kind):
        if kind == 9: return b[p:p + 16].hex(), p + 16
        if kind == 8:
            n = struct.unpack_from('<I', b, p)[0]
            if n > STRCAP or p + 4 + 2 * n > len(b): raise Desync('string length %d at %d' % (n, p))
            return b[p + 4:p + 4 + 2 * n].decode('utf-16le', 'replace'), p + 4 + 2 * n
        if kind == 5 and os.environ.get('RVT_K5') == 'skip': return 0, p
        if kind in PRIM:
            fmt, sz = PRIM[kind]
            if p + sz > len(b): raise Desync('past end')
            return struct.unpack_from(fmt, b, p)[0], p + sz
        raise Desync('unknown kind %#x' % kind)
    # ---- one value of field f starting at p; pend collects deferred pointer bodies
    def value(s, b, p, f, pend, path, lvl=0):
        types = f['types']; ns = f.get('ns') or [None] * len(types)
        T = types[lvl]; kind = T & 0xff; fl = (T >> 8) & 0xff
        n = ns[lvl] if lvl < len(ns) else None
        last = lvl == len(types) - 1
        ref = f.get('ref') if (lvl == 0 or last) and 'ref' in f else f.get('ref2')
        if kind == 0x0d:                          # array of the next level; fixed length n, or u32 count prefix
            if fl & 0x10 and not fl & 0x40: cnt = n
            else:
                cnt = struct.unpack_from('<I', b, p)[0]; p += 4
                if cnt > 1000000: raise Desync('array count %d' % cnt)
            out = []
            for _ in range(cnt):
                v, p = s.value(b, p, f, pend, path, lvl + 1); out.append(v)
            return out, p
        if fl & 0x10 and not fl & 0x40:           # fixed array of this element type
            out = []
            for _ in range(n):
                v, p = s.elem(b, p, kind, fl & ~0x10, ref, pend, path); out.append(v)
            return out, p
        return s.elem(b, p, kind, fl, ref, pend, path)
    def elem(s, b, p, kind, fl, ref, pend, path):
        if kind == 0x0e:
            if (fl & 0xf0) == 0x50 and (fl & 0x0f):   # set/vector of pointers: count + slots (0x51 set, 0x54 vector, ...)
                n = struct.unpack_from('<I', b, p)[0]; p += 4
                if n == 0xffffffff: return None, p
                if n > 1000000: raise Desync('set count %d at %d (%s)' % (n, p - 4, '.'.join(path)))
                out = []
                for _ in range(n):
                    v, p = s.slot(b, p, (fl & 0x0f) if (fl & 0x0f) in (1, 2, 3) else 1, pend, path); out.append(v)
                return out, p
            if fl in (1, 2, 3):                   # pointer slot
                return s.slot(b, p, fl, pend, path)
            if fl == 4 and not os.environ.get('RVT_NOFL4'):   # 2014-2017: flag 4 = nullable pointer slot (VarParam.m_pSubst), bm3fam 2026-10-23
                return s.slot(b, p, 1, pend, path)
            ref = (ref or 0) & 0x7fff
            if fl == 0x50:                        # vector of embedded structs
                n = struct.unpack_from('<I', b, p)[0]; p += 4
                if n == 0xffffffff: return None, p
                if n > 1000000: raise Desync('vector count %d at %d (%s)' % (n, p - 4, '.'.join(path)))
                out = []
                for _ in range(n):
                    v, p = s.struct(b, p, ref - 12, pend, path); out.append(v)
                return out, p
            if fl == 0:
                return s.struct(b, p, ref - 12, pend, path)
            raise Desync('flags %#x kind 0e' % fl)
        if fl in (0x50, 0x51):                    # vector of primitives
            n = struct.unpack_from('<I', b, p)[0]; p += 4
            if kind in (1, 2) :                       # byte blobs (images, zips): keep as bytes, length bounded by the buffer
                if p + n > len(b): raise Desync('byte vector count %d past end' % n)
                return bytes(b[p:p + n]), p + n
            if n > 1000000: raise Desync('prim vector count %d' % n)
            out = []
            for _ in range(n):
                v, p = s.prim(b, p, kind); out.append(v)
            return out, p
        return s.prim(b, p, kind)
    def es_slot(s, b, p, pend, path):
        """extensible-storage entity pointer: [u32 0 | u32 handle][16-byte schema GUID]; body = values in schema entry order (queued)"""
        v = struct.unpack_from('<I', b, p)[0]
        if v == 0: return None, p + 4
        g = b[p + 4:p + 20].hex()
        slot = {'handle': v, 'es': g}; pend.append((slot, ('ES', g))); return slot, p + 20
    ES_PRIM = {'int': ('<i', 4), 'short': ('<h', 2), 'char': ('<B', 1), 'bool': ('<B', 1), 'double': ('<d', 8), 'float': ('<f', 4)}
    def es_value(s, b, p, tname, pend, path):
        if tname == 'TCHAR' or tname == 'AString': return s.prim(b, p, 8)
        if tname in s.ES_PRIM:
            fmt, sz = s.ES_PRIM[tname]; return struct.unpack_from(fmt, b, p)[0], p + sz
        if tname == 'GUIDvalue': return b[p:p + 16].hex(), p + 16
        if tname == 'ElementId':
            w = s.idsize; return EID(struct.unpack_from('<I' if w == 4 else '<Q', b, p)[0]), p + w
        if tname == 'XYZ': return list(struct.unpack_from('<3d', b, p)), p + 24
        if tname == 'UV': return list(struct.unpack_from('<2d', b, p)), p + 16
        if tname == 'ESEntity': return s.es_slot(b, p, pend, path)
        raise Desync('ES type %s' % tname)
    def es_body(s, b, p, guid, pend, path):
        sc = s.es_schemas.get(guid)
        if sc is None: raise Desync('unknown ES schema %s' % guid)
        out = {}
        for f in sorted(sc['m_fields'], key=lambda f: f['m_entryIndex']):
            cont = f['m_containerType']; tn = f['m_fieldTypeName']
            if cont == 0: out[f['m_fieldName']], p = s.es_value(b, p, tn, pend, path)
            elif cont == 1:
                n = struct.unpack_from('<I', b, p)[0]; p += 4
                if n > 1000000: raise Desync('ES array count')
                arr = []
                for _ in range(n):
                    v, p = s.es_value(b, p, tn, pend, path); arr.append(v)
                out[f['m_fieldName']] = arr
            elif cont == 2:
                m = re.match(r'std::pair<\s*(\w+)\s*,\s*(\w+)\s*>', tn)
                if not m: raise Desync('ES map type %s' % tn)
                n = struct.unpack_from('<I', b, p)[0]; p += 4
                if n > 1000000: raise Desync('ES map count')
                mp = []
                for _ in range(n):
                    k, p = s.es_value(b, p, m.group(1), pend, path); v, p = s.es_value(b, p, m.group(2), pend, path); mp.append((k, v))
                out[f['m_fieldName']] = mp
        return out, p
    def slot(s, b, p, stars, pend, path):
        v = struct.unpack_from('<I', b, p)[0]
        if v == 0: return None, p + 4
        if v != 0xffffffff:
            if (s.backref and v in s.defined) or stars == 3:      # back-reference to a handle already defined (doc=1, element=2, ...)
                return {'ref': v}, p + 4
            s.defined.add(v)                      # first appearance defines the object (tag follows, body queued)
        tag = struct.unpack_from('<H', b, p + 4)[0]
        if v == 0xffffffff and not (12 <= tag < 12 + len(s.s.c)): return None, p + 4      # a 4-byte null (-1), not followed by a tag
        if not 12 <= tag < 12 + len(s.s.c): raise Desync('pointer tag %d at %d (%s)' % (tag, p, '.'.join(path)))
        slot = {'handle': v, 'ptr': tag}; pend.append((slot, tag)); return slot, p + 6
    def struct(s, b, p, ci, pend, path, top_out=None):
        if not 0 <= ci < len(s.s.c): raise Desync('bad class index %d' % ci)
        # embedded ElementId/Identifier collapse to an int
        out = {} if top_out is None else top_out
        GG = s._gg
        if GG == 'auto' and top_out is None and any(s.s.c[k]['name'] == 'GeomGenerator' for k in s.s.chain(ci)) and not getattr(s, '_in_try', False):
            best = None
            for skip in (0, 9, 8, 10, 12):
                s._in_try = True
                try:
                    pend2 = []
                    v2, p2 = s.struct(b, p + skip, ci, pend2, path)
                    if all(12 <= t < 12 + len(s.s.c) for _, t in pend2): best = (skip, v2, p2, pend2); break
                except Exception: pass
                finally: s._in_try = False
            if best:
                skip, v2, p2, pend2 = best
                pend.extend(pend2); v2['_ggSkip'] = skip
                return v2, p2
        elif GG not in ('0', 'auto', 'h1') and top_out is None and any(s.s.c[k]['name'] == 'GeomGenerator' for k in s.s.chain(ci)):
            out['_ggPrefix'] = b[p:p + int(GG)].hex(); p += int(GG)
        H = s._m
        if H and top_out is None:
            chain = s.s.chain(ci); ms = [(s.s.c[k]['name'], s.s.c[k].get('M') or 0) for k in chain]
            skip = 0
            if H == 'A':   # nearest class (self upward) with nonzero M, words
                for k in reversed(chain):
                    if (s.s.c[k].get('M') or 0): skip = 4 * s.s.c[k]['M']; break
            elif H == 'B':
                for k in reversed(chain):
                    if (s.s.c[k].get('M') or 0): skip = s.s.c[k]['M']; break
            elif H == 'C': skip = sum(4 * (s.s.c[k].get('M') or 0) for k in chain)
            elif H == 'D': skip = sum((s.s.c[k].get('M') or 0) for k in chain)
            if skip: out['_prefix'] = b[p:p + skip].hex(); p += skip
        chain = s.s.chain(ci)
        hint = None
        if top_out is None:
            for k in reversed(chain):
                h = s.hints.get(s.s.c[k]['name'])
                if h: hint = h; break
        skipf = set()
        if hint:
            pre = hint.get('prefix', 0)
            if pre: out['_prefix'] = b[p:p + pre].hex(); p += pre
            if hint.get('order') == 'derived': chain = list(reversed(chain))
            elif hint.get('first'):
                first = [k for k in chain if s.s.c[k]['name'] in hint['first']]; chain = first + [k for k in chain if k not in first]
            skipf = set(hint.get('skip', []))
        for k in chain:
            for f in s.s.c[k]['fields']:
                if f['name'] in skipf or (s.s.c[k]['name'] + '.' + f['name']) in skipf: continue
                p0 = p
                try:
                    if s.s.c[k]['name'] == 'ESEntity' and f['name'] == 'm_blob':
                        out[f['name']], p = s.es_slot(b, p, pend, path); continue
                    out[f['name']], p = s.value(b, p, f, pend, path + [s.s.c[k]['name'], f['name']])
                    if s.trace: s.log.append((len(path), s.s.c[k]['name'] + '.' + f['name'], p0, p, str(out[f['name']])[:60]))
                except Desync as e:
                    if '@@' not in str(e): raise Desync('%s @@ %s.%s T=%#x at %d: %s' % (str(e), s.s.c[k]['name'], f['name'], f['T'], p, b[p:p+24].hex(' ')))
                    raise
        if hint and hint.get('suffix'): p += hint['suffix']
        nm = s.s.c[ci]['name']
        if nm == 'ElementId' and len(out) == 1:
            (v,) = out.values()
            if isinstance(v, dict) and len(v) == 1: v = next(iter(v.values()))
            return EID(v) if isinstance(v, int) else v, p
        return out, p
    STOP = () if os.environ.get('RVT_GEOM') else ('GeomStepList', 'GeomTable')
    def body(s, b, p, tag, path, top=False):
        """Decode the top-level object, then its pointer bodies breadth-first (FIFO): bodies referenced by a body are queued
        after all bodies referenced by the object itself."""
        from collections import deque
        pend = []
        if hasattr(s, 'visited'): s.visited.append(s.s.name(tag))
        part = {}
        try:
            v, p = s.struct(b, p, tag - 12, pend, path, top_out=part)
        except Desync as e:
            e.partial = part; raise
        q = deque(pend)
        while q:
            slot, t = q.popleft()
            if isinstance(t, tuple):
                npend = []
                try: obj, p = s.es_body(b, p, t[1], npend, path + ['*ES'])
                except (Desync, struct.error) as e:
                    slot['obj'] = None; s.err = str(e); return v, p, False
                slot['obj'] = obj; q.extend(npend); continue
            if s.s.name(t) in s.STOP:
                slot['obj'] = '<geometry not decoded>'; return v, p, False
            if hasattr(s, 'visited'): s.visited.append(s.s.name(t))
            npend = []
            try:
                obj, p = s.struct(b, p, t - 12, npend, path + ['*%s' % s.s.name(t)])
            except Desync as e:
                slot['obj'] = None; s.err = str(e); return v, p, False
            slot['obj'] = obj
            q.extend(npend)
        return v, p, True
    def record(s, b, p, short=False):
        """header: [u32 A][id][u64 stamp][u16 tag]  (short=True: [u32 A][id][u32 stamp][u16 tag])"""
        W = s.idsize; sl = 4 if short else 8
        eid = struct.unpack_from('<I' if W == 4 else '<Q', b, p + 4)[0]; tag = struct.unpack_from('<H', b, p + 4 + W + sl)[0]
        s.err = None; s.maxh = 2; s.defined = {1, 2}; s.visited = []
        body0 = p + 4 + W + sl + 2
        try:
            obj, q, complete = s.body(b, body0, tag, [s.s.name(tag)], top=True)
        except Desync as e:
            part = getattr(e, 'partial', None)
            if not part or 'm_id' not in part: raise
            return {'id': eid, 'tag': tag, 'class': s.s.name(tag), 'fields': part, 'complete': False, 'error': str(e)[:200], 'short': short}, p
        return {'id': eid, 'tag': tag, 'class': s.s.name(tag), 'fields': obj, 'complete': complete, 'error': s.err, 'bodies': s.visited, 'short': short}, q


# ---- optional Rust record decoder (~/src/rvt-core); the Python Dec above stays the reference oracle and the fallback ----
try:
    if os.environ.get('RVT_NOFAST'): raise ImportError
    import rvt_core as _RC
except Exception:
    _RC = None

class FastDec(Dec):
    """Dec whose record() runs in Rust when the default configuration applies (no hints / experiments, input is a bytes object)"""
    def __init__(s, schema, idsize=4, trace=False):
        super().__init__(schema, idsize, trace)
        s._rd = _RC.RecDecoder(schema.c, idsize, list(s.STOP), STRCAP, EID, Desync)
        s._es = {}
    @property
    def es_schemas(s): return s._es
    @es_schemas.setter
    def es_schemas(s, v):
        s._es = v
        if hasattr(s, '_rd'): s._rd.set_es(v)
    def record(s, b, p, short=False):
        if s.hints or s._gg != '0' or s._m or s.trace or not isinstance(b, bytes): return super().record(b, p, short)
        s._rd.set_strcap(STRCAP)
        return s._rd.record(b, p, short)

def make_dec(schema, idsize=4, trace=False):
    return FastDec(schema, idsize, trace) if _RC is not None else Dec(schema, idsize, trace)
