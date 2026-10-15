import os, sys, pickle, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault('RVT_GEOM', '1')
import rvt_entities as E
try: sys.path.append(os.path.expanduser('~/src/rvt-core/python')); import rvt_fast as _F
except Exception: _F = None
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xcache')
def get_x(path):
    if _F is not None and _F.on():                                     # Rust fast extraction (binary cache; identical content, c4-rust RUST_INTEGRATION.md 2026-10-13)
        try:
            x = _F.extract(path, want_all=True); x.pop('sch', None); return x
        except Exception: pass
    os.makedirs(D, exist_ok=True)
    st = os.stat(path); k = hashlib.sha1(('%s|%d|%d|%d' % (path, st.st_size, int(st.st_mtime), int(os.path.getmtime(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_decode.py'))))).encode()).hexdigest()
    f = os.path.join(D, k + '.pkl')
    if os.path.exists(f):
        return pickle.load(open(f, 'rb'))
    x = E.extract(path, want_all=True)
    x.pop('sch', None)
    pickle.dump(x, open(f + '.tmp', 'wb'), protocol=5); os.replace(f + '.tmp', f)
    return x

def get_x_ro(path):
    """READ-ONLY records (shared within the process when the Rust path is on, c2-rust RUST_INTEGRATION.md 'Proposed hook 2'): callers must not mutate them"""
    if _F is not None and _F.on():
        try: return _F.extract_shared(path)
        except Exception: pass
    return get_x(path)
