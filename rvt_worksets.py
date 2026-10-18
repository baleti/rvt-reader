"""Worksets of a workshared .rvt.
worksets(path) -> {guid_hex: {'id', 'name', 'kind' (0 user workset; other values = standard / family / view worksets), 'default_visible'}}   (guid_hex = the 16 GUID bytes as stored, lowercase hex = the keys of the per-view
  m_worksetVisibilityPGUIDMap / WorksetVisibilitySettingsElem.m_invisibleWorksets[].m_guid.m_guid)
element_worksets(path) -> {element id: workset id}
Layout (verified 2024 + 2026 vg_worksets scenes against Revit's WORKSET / WSELEM rows, every element): Global/PartitionTable holds the workset entries
  [u32 1][GUID 16][u32 workset id][u32 0x205][u32 0x205][u32 ffffffff (view worksets: owner id)][u32 kind][u8 0][u32 nchars][UTF-16 name]  (the GUID belongs to the entry whose name FOLLOWS it);
Global/ElemTable (8-byte-id files: 40-byte records from offset 6) holds each element's workset id in the last u32 of its record (+36). 4-byte-id files (<= 2023: 28-byte records): last u32 (+24) assumed, not verified (no oracle)."""
import struct, olefile
from rvt_scan import inflate_stream

def _partition(path):
    o = olefile.OleFileIO(path); return o, inflate_stream(o.openstream('Global/PartitionTable').read())[1]

def worksets(path, invisible=None):
    o, d = _partition(path); out = {}; first = True
    for i in range(36, len(d) - 8):
        if d[i] != 0: continue
        n = struct.unpack_from('<I', d, i + 1)[0]
        if not 0 < n < 150 or i + 5 + 2 * n > len(d): continue
        kp = i - 4; kind = struct.unpack_from('<I', d, kp)[0]
        if kind > 5000: continue
        raw = d[i + 5:i + 5 + 2 * n]
        try: nm = raw.decode('utf-16-le')
        except Exception: continue
        if not nm.isprintable() or not nm.strip(): continue
        if struct.unpack_from('<I', d, kp - 36)[0] != 1 and not (first and kp < 64): continue     # [u32 1][GUID] precede regular entries; the first entry of the table has a different header
        first = False
        wid = struct.unpack_from('<I', d, kp - 16)[0]; guid = d[kp - 32:kp - 16].hex()
        out[guid] = {'id': wid, 'name': nm, 'kind': kind, 'default_visible': True}
    if invisible is None: invisible = default_invisible(path)
    for g in invisible:
        if g in out: out[g]['default_visible'] = False
    return out

def default_invisible(path):
    import rvt_materials as RM
    r = set()
    for e, rec in RM._ctx(path).recs.items():
        if rec['class'] == 'WorksetVisibilitySettingsElem':
            for g in rec['fields'].get('m_invisibleWorksets') or []:
                v = (g.get('m_guid') or {}).get('m_guid') if isinstance(g, dict) else None
                if isinstance(v, (bytes, bytearray)): v = v.hex()
                if v: r.add(str(v).lower())
    return r

def element_worksets(path):
    o = olefile.OleFileIO(path); et = inflate_stream(o.openstream('Global/ElemTable').read())[1]
    out = {}
    rec = 40 if all(struct.unpack_from('<I', et, 6 + k * 40)[0] == struct.unpack_from('<I', et, 6 + k * 40 + 20)[0] for k in range(min(8, (len(et) - 6) // 40))) else 28      # 40-byte records repeat the id at +20
    n = (len(et) - 6) // rec
    for k in range(n):
        b = 6 + k * rec
        if rec == 40: out[struct.unpack_from('<Q', et, b)[0]] = struct.unpack_from('<I', et, b + 36)[0]
        else: out[struct.unpack_from('<I', et, b)[0]] = struct.unpack_from('<I', et, b + 24)[0]
    return out
