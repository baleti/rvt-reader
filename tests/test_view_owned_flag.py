# regression: view-owned FamilyInstance box gets 'view_owned_2d'; model instances do not. Uses synthetic ctx (no client data).
import sys,os; sys.path.insert(0,os.path.expanduser('~/rvt-research'))
import rvt_geometry as G, rvt_decode as D
class C:
    def __init__(s,sym): s.sym=sym
    def rec(s,i): return s.sym if i==5 else None
    level={}; own={}
def mk(ov):
    f={'m_pInstanceInfo':{'m_Trf':{'m_3x3':[[1,0,0],[0,1,0],[0,0,1]],'m_or':[0,0,0]},'m_symbolId':5},'m_ownerDBViewId':D.EID(ov)}
    return {'class':'FamilyInstance','fields':f}
sym={'class':'FamilySymbol','fields':{'m_outline':{'m_minmax':[[0,0,0],[1,1,1]]}}}
try:
    a=G.instance_box(C(sym),1,mk(549871)); b=G.instance_box(C(sym),2,mk(0xFFFFFFFF))
except Exception as e: print('SKIP/ERR',type(e).__name__,e); raise
assert 'view_owned_2d' in a['flags'] and 'view_owned_2d' not in b['flags'], (a['flags'],b['flags']); print('ok')
