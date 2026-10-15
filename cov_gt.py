#!/usr/bin/env python3
"""cov_gt.py: join per-id decode status (COV_IDSTAT json) with the Revit element dump -> % of Revit's elements fully decoded, per year/class."""
import sys, os, json, glob, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_gt as G
def main():
    rows = collections.defaultdict(lambda: [0, 0, 0, 0]); byclass = collections.defaultdict(lambda: collections.Counter()); errs = collections.defaultdict(collections.Counter)
    for st in sorted(glob.glob('idstat/*.json')):
        m = re.match(r'(\d{4})_(\d+)_(.*)\.json', os.path.basename(st))
        if not m: continue
        y, idx, name = m.groups()
        tsvs = glob.glob(f'gt4/{y}_{idx}_*.tsv')
        if not tsvs: continue
        E, P = G.load_gt(tsvs[0]); d = json.load(open(st)); status = d['status']; err = d['err']
        for eid, e in E.items():
            v = status.get(str(eid), -1)
            r = rows[y]; r[0] += 1; r[1] += v >= 1; r[2] += v == 2; r[3] += v == -1
            if v < 2:
                byclass[y][e['cls']] += 1
                if str(eid) in err: errs[y][tuple(err[str(eid)])] += 1
    print('year  revit_elements  complete%  exact%  not_found')
    for y in sorted(rows):
        r = rows[y]; print(f'{y}  {r[0]:10d}   {100*r[1]/r[0]:7.2f}  {100*r[2]/r[0]:7.2f}  {r[3]}')
    if '-v' in sys.argv:
        for y in sorted(rows): print(y, 'unresolved API classes:', byclass[y].most_common(6), 'errors:', errs[y].most_common(4))
main()
