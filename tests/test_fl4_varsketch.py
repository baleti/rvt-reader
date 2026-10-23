"""Regression (corpus 2026-10-23): Revit 2014-2017 VarSketch VarParam.m_pSubst (kind 0e, flags 4) is a nullable pointer slot.
Run: RVT_NOFAST=1 python3 tests/test_fl4_varsketch.py  (Autodesk sample families 2016/2017 must decode with 0 real record errors)"""
import sys, os, glob
os.environ.setdefault('RVT_NOFAST', '1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import rvt_entities as E
bad = 0
for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'samples-rfa', '*201[67].rfa'))):
    x = E.extract(f, want_all=True)
    e = [k[1] for k, v in x['recs'].items() if v.get('error') and k[0] != 0]
    print(os.path.basename(f), 'real errors', len(e)); bad += len(e)
sys.exit(1 if bad else 0)
