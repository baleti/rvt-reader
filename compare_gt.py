#!/usr/bin/env python3
"""Compare rvt2text.py against ground truth taken from real Revit (groundtruth/*.json = driver output: BFI/SHEET/LEVEL/COUNT lines)."""
import json, glob, os, re, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__)); tot = dict(files=0, ver=0, sheets_gt=0, sheets_hit=0, sheets_extra=0, lv_gt=0, lv_hit=0, exact=0)
for f in sorted(glob.glob(here + '/groundtruth/*.json')):
    j = json.load(open(f, encoding='utf-8-sig')); name = j['file']
    if j['state'] != 'done' or 'ERR\t' in (j['output'] or ''): print('GT FAILED', name); continue
    p = next(q for q in (f'{here}/samples/{name}', f'{here}/samples-rfa/{name}') if os.path.exists(q))
    L = [l.split('\t') for l in j['output'].splitlines()]
    bfi = next(l[1] for l in L if l[0] == 'BFI')
    gs = {(l[1], l[2]) for l in L if l[0] == 'SHEET'}; gl = {l[1] for l in L if l[0] == 'LEVEL'}
    r = subprocess.run([sys.executable, here + '/rvt2text.py', p], capture_output=True, text=True).stdout
    mv = (re.search(r'Revit version: (\S+)', r) or [0, None])[1]
    ms = {(m.group(1), m.group(2).strip()) for m in re.finditer(r'^  Sheet (\S+) - (.*?)(?:  \(issued.*)?$', r, re.M)}
    lines = set(r.splitlines()); lh = sum(1 for l in gl if l in lines)
    tot['files'] += 1; tot['ver'] += str(mv) == bfi; tot['sheets_gt'] += len(gs); tot['sheets_hit'] += len(gs & ms); tot['sheets_extra'] += len(ms - gs)
    tot['lv_gt'] += len(gl); tot['lv_hit'] += lh; tot['exact'] += (gs == ms and str(mv) == bfi)
    print(f"{name[:46]:46} ver {bfi}/{mv} sheets {len(gs & ms)}/{len(gs)} (+{len(ms - gs)} extra) levels {lh}/{len(gl)}" + ('' if gs == ms and str(mv) == bfi else '  <== DIFF'))
print(tot)
