"""per-triangle materials (element_mesh 'mat') vs Revit's face materials (gt_mat FMAT rows): same material SET per element (detail Fine)"""
import sys, os, collections
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_elemmesh as E
f = sys.argv[1]; y = f.split('/')[-2]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
tsv = '/home/user1/rvt-research/gt_mat/%s_%s.fmatall.tsv' % (y, os.path.splitext(os.path.basename(f))[0])
if not os.path.exists(tsv) or os.environ.get('FMAT_SAMPLE'): tsv = '/home/user1/rvt-research/gt_mat/%s_%s.tsv' % (y, os.path.basename(f))
print('oracle', os.path.basename(tsv))
want = collections.defaultdict(collections.Counter); cls = {}
for l in open(tsv):
    t = l.rstrip('\n').split('\t')
    if t[0] == 'FMATEL': cls[int(t[1])] = t[2] + '/' + t[3]
    if t[0] in ('FMAT', 'FMATPAINTED'):
        eid = int(t[1].split('.')[0]); mid = t[2].split('=')[1]; want[eid][int(mid) if mid not in ('', '-1') else -1] += 1
d = E.Doc(f); n = same = 0; bad = []; per = collections.Counter(); perok = collections.Counter()
for eid, w in list(want.items())[:N]:
    m = E.element_mesh(d, eid, detail=3); got = set(m.get('mat') or [])
    n += 1; k = cls.get(eid, '?'); per[k] += 1
    if set(w) == got: same += 1; perok[k] += 1
    else: bad.append((eid, k, sorted(set(w)), sorted(got)))
print('elements', n, 'same material set', same)
for k in per: print('  %-40s %d/%d' % (k, perok[k], per[k]))
for b in bad[:15]: print(b)
