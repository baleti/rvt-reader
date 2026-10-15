"""Learn field->parameter mapping (per class + universal '*') from xcache'd files; split.json train set; sampled per class."""
import sys, os, json, random, collections, tempfile
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_xcache, rvt_map2 as M, eval_gt as G
split = json.load(open('split.json')); which = sys.argv[1]; out = sys.argv[2]; per_class = int(sys.argv[3]) if len(sys.argv) > 3 else 40
pairs = split['train'] if which == 'train' else split['train'] + split['test']
class Shim:
    @staticmethod
    def get(path):
        x = rvt_xcache.get_x(path); last = {}
        for (eid, c), r in x['recs'].items(): last.setdefault(eid, r)
        return {'last': last, 'hdr': {e: {'fields': f} for e, f in x['eh'].items()}}
M.rvt_cache = Shim
rnd = random.Random(7); tmp = tempfile.mkdtemp(); sp = []; sp_u = []
for rvt, tsv in pairs:
    d = Shim.get(rvt); E, P = G.load_gt(tsv)
    byc = collections.defaultdict(list)
    for eid in E:
        if eid in d['last']: byc[d['last'][eid]['class']].append(eid)
    keep = set()
    for c, l in byc.items(): keep |= set(rnd.sample(l, min(per_class, len(l))))
    lines = [ln for ln in open(tsv, encoding='utf-8') if (ln.split('\t')[0] in ('E', 'P')) and int(ln.split('\t')[1]) in keep] if True else []
    fn = os.path.join(tmp, os.path.basename(tsv)); open(fn, 'w', encoding='utf-8').writelines(lines); sp.append((rvt, fn))
    # universal: all classes mapped to '*'
M.UNIV = len(sys.argv) > 4 and sys.argv[4] == 'univ'
res, api, tot = M.learn2(sp)
json.dump({'mapping': res, 'api_class': api, 'elements': tot}, open(out, 'w'))
print('classes', len(res), 'rules', sum(len(v) for v in res.values()))
