import sys, os, pickle, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_inventory as I
def get(path):
    key = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', hashlib.md5((path + str(os.path.getmtime(path)) + 'v4' + str(int(os.path.getmtime(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_decode.py'))))).encode()).hexdigest() + '.pkl')
    if os.path.exists(key): return pickle.load(open(key, 'rb'))
    os.environ['RVT_GEOM'] = '1'
    cls, ids, recs, st = I.inventory(path)
    last = {k: v[-1] for k, v in recs.items()}
    hdr = st.pop('_hdr', {})
    for r in last.values(): r.pop('where', None)
    data = {'cls_names': [c['name'] for c in cls], 'ids': ids, 'last': last, 'hdr': hdr, 'stats': dict(st)}
    pickle.dump(data, open(key, 'wb')); return data
if __name__ == '__main__':
    for p in sys.argv[1:]: d = get(p); print(os.path.basename(p), len(d['last']))
