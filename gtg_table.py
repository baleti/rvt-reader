"""ACCEPTANCE-style table from gt_geom comparison rows (gtg_*.jsonl): per class % of elements with volume<=2%, area<=3%, centroid<=1% of the bbox diagonal, all three."""
import json, glob, sys, collections
files = sys.argv[1:] or sorted(glob.glob('/home/user1/rvt-research/gtg/*.jsonl'))
st = collections.defaultdict(collections.Counter)
for f in files:
    for l in open(f):
        r = json.loads(l); c = r['cls']; st[c]['n'] += 1
        if r['status'] != 'mesh': st[c][r['status']] += 1; continue
        ok_v = bool(r.get('mvol') is not None and ((r['rvol'] > 0 and abs(r['mvol'] / r['rvol'] - 1) <= 0.02) or (r.get('sheet') and abs(r['rvol']) < 1e-6)))
        ok_a = r.get('marea') is not None and r['rarea'] > 0 and abs(r['marea'] / r['rarea'] - 1) <= 0.03
        ok_c = False
        if r.get('mcent') and r.get('rbb'):
            dg = sum((x - y) ** 2 for x, y in zip(r['rbb'][0], r['rbb'][1])) ** .5
            for ref in (r.get('rcent'), r.get('rcent_world'), r.get('rcent_chain')):
                if ref and sum((x - y) ** 2 for x, y in zip(r['mcent'], ref)) ** .5 <= 0.01 * dg: ok_c = True
        if r.get('sheet') and r.get('mbb') and r.get('rbb'):                      # no centroid for zero-volume sheets in the oracle: compare the bounding boxes instead
            dg = sum((x - y) ** 2 for x, y in zip(r['rbb'][0], r['rbb'][1])) ** .5 or 1.0
            ok_c = max(abs(a - b) for a, b in zip(r['mbb'][0] + r['mbb'][1], r['rbb'][0] + r['rbb'][1])) <= 0.01 * dg
        st[c]['vol'] += ok_v; st[c]['area'] += ok_a; st[c]['cent'] += ok_c; st[c]['all'] += ok_v and ok_a and ok_c
print('%-26s %5s %7s %7s %7s %7s   (volume<=2%%, area<=3%%, centroid<=1%% diag, all three; of elements with a solid in the Revit oracle)' % ('class', 'n', 'vol', 'area', 'cent', 'all'))
for c, d in sorted(st.items(), key=lambda a: -a[1]['n']):
    n = d['n']; print('%-26s %5d %6.1f%% %6.1f%% %6.1f%% %6.1f%%  no-graphics %d empty %d' % (c, n, 100 * d['vol'] / n, 100 * d['area'] / n, 100 * d['cent'] / n, 100 * d['all'] / n, d['no_saved_graphics'], d['empty_mesh']))
