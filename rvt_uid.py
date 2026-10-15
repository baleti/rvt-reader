"""UniqueId / IfcGUID derived from the file alone: Global/History tail table of episode GUIDs + ElemTable episode index per element."""
import struct, uuid, olefile
from rvtfmt import inflate_stream
import rvt_scan as S
import ifcguid

def episodes(h, n=None):
    n = (len(h) - 5) // 17 if n is None else n
    out = []
    for i in range(n):
        p = len(h) - 21 - 17 * i
        if p < 0: break
        out.append(str(uuid.UUID(bytes_le=bytes(h[p:p + 16]))))
    return out

def episode_col(path, W):
    o = olefile.OleFileIO(path); et = inflate_stream(o.openstream('Global/ElemTable').read())[1]; out = {}
    if W == 4:
        for k in range((len(et) - 6) // 28):
            r = struct.unpack_from('<7I', et, 6 + 28 * k); out[r[0]] = r[2]
    else:
        for k in range((len(et) - 6) // 40):
            out[struct.unpack_from('<Q', et, 6 + 40 * k)[0]] = struct.unpack_from('<I', et, 6 + 40 * k + 8)[0]
    return out

def unique_ids(path):
    o = olefile.OleFileIO(path); cls = S.load(path)[1]; W = S.id_size(cls)
    h = inflate_stream(o.openstream('Global/History').read())[1]
    col = episode_col(path, W); eps = episodes(h, max(col.values()) + 1); out = {}
    for eid, ix in col.items():
        if ix < len(eps): out[eid] = '%s-%0*x' % (eps[ix], 8, eid & 0xffffffff)
    return out

def ifc_guids(path):
    return {e: ifcguid.from_unique(u) for e, u in unique_ids(path).items()}
