import sys, glob, re, os, collections, json
sys.path.insert(0, '/home/user1/rvt-research')
import rvt_entities as R, eval_gt as G
def gt_sets(tsv):
    E, P = G.load_gt(tsv); s = collections.defaultdict(set)
    for i, e in E.items():
        c = e['cls']; n = e['name']
        if c == 'Level': s['levels'].add(n)
        elif c == 'Grid': s['grids'].add(n)
        elif c == 'Phase': s['phases'].add(n)
        elif c == 'Material': s['materials'].add(n)
        elif c == 'Family': s['families'].add(n)
        elif c == 'ViewSheet':
            s['sheets'].add(n)
        elif c in ('ViewPlan', 'ViewSection', 'View3D', 'ViewSchedule', 'ViewDrafting', 'ViewSheet', 'View', 'ViewPlanType'): s['views'].add(n)
        elif c == 'Room':
            num = next((v for b, nm, st, v in P[i] if nm == 'Number'), ''); nme = next((v for b, nm, st, v in P[i] if nm == 'Name'), n); s['rooms'].add((num, nme))
    return s
rows = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))
for line in open(sys.argv[1]):
    f = line.strip(); m = re.match(r'.*corpus/(\d{4})/(\d+)_', f); y, i = m.groups(); t = glob.glob(f'gt4/{y}_{i}_*.tsv')
    if not t: continue
    g = gt_sets(t[0]); r = R.parse(f)
    ours = {'levels': {l['name'] for l in r['levels']}, 'grids': set(r['grids']), 'phases': set(r['phases']), 'materials': set(r['materials']), 'families': set(r['families']),
            'sheets': {s['name'] for s in r['sheets']}, 'views': {v['name'] for v in r['views'] if v['name'] != '???'} | {s['name'] for s in r['sheets']}, 'rooms': {(str(x['number']), x['name']) for x in r['rooms'] if x['kind'] == 'Room'}}
    for k in ours:
        a, b = g.get(k, set()), ours[k]; rows[y][k][0] += len(a & b); rows[y][k][1] += len(a); rows[y][k][2] += len(b)
for y in sorted(rows):
    print(y, {k: f'R{100*v[0]/max(v[1],1):.0f}/P{100*v[0]/max(v[2],1):.0f} (gt {v[1]})' for k, v in rows[y].items()})
