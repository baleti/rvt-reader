# regression for the BM3-driven reader fixes (synthetic records only, no client data):
# BaseRailing bbox-only box, SWall prefers closed-shell mesh, DesignOption id-0 phantom dropped (ProjectPhase id 0 kept), design_option API
import sys,os; sys.path.insert(0,os.path.expanduser(os.environ.get('RVT_CODE','~/rvt-research')))
import rvt_geometry as G, rvt_elemmesh as EM
class Ctx:
    def __init__(s,recs): s.recs=recs
    def rec(s,i): return s.recs.get(i)
# 1. empty mesh + stored bbox + symbol_no_graphics -> box; without the flag stays None
G._docs['synthetic.rvt'] = object()                                          # no real Doc needed
rec={'class':'BaseRailing','fields':{}}
EM.element_mesh = lambda d, e: {'tris': [], 'flags': ['symbol_no_graphics'], 'bbox': [[0, 0, 0], [0.25, 16, 0.16]]}
r = G._mesh_geometry('synthetic.rvt', 7, rec)
assert r and r['confidence'] == 'box' and r['bbox'] == [[0, 0, 0], [0.25, 16, 0.16]] and 'symbol_no_graphics' in r['flags'], r
EM.element_mesh = lambda d, e: {'tris': [], 'flags': [], 'bbox': [[0, 0, 0], [1, 1, 1]]}
assert G._mesh_geometry('synthetic.rvt', 7, rec) is None                       # e.g. unbounded room: still no geometry
EM.element_mesh = lambda d, e: {'tris': [], 'flags': ['symbol_no_graphics'], 'bbox': [[0, 0, 0], [0, 0, 0]]}
assert G._mesh_geometry('synthetic.rvt', 7, rec) is None                       # degenerate bbox: no box
# 2. SWall: parametric 'approx' is replaced by a closed-shell mesh, kept when the mesh is not closed
swall = {'class': 'SWall', 'fields': {}}
G.get_ctx = lambda f: Ctx({9: swall})
G.BUILDERS = dict(G.BUILDERS); G.BUILDERS['SWall'] = lambda c, e, r_: G._res(c, e, r_, 'approx', [], ['no_joins'])
G._mesh_geometry = lambda f, e, rc: G._res(None, e, rc, 'mesh_approx', [], ['saved_graphics_tessellation', 'closed_shell'])
assert G.element_geometry('synthetic.rvt', 9)['confidence'] == 'mesh_approx'
G._mesh_geometry = lambda f, e, rc: G._res(None, e, rc, 'mesh_approx', [], ['saved_graphics_tessellation'])
assert G.element_geometry('synthetic.rvt', 9)['confidence'] == 'approx'          # mesh not a closed shell: parametric wall stays
# 3+4. design options
recs = {0: {'class': 'DesignOption', 'fields': {}},
        100: {'class': 'DesignOption', 'fields': {'m_strName': 'Empty', 'm_DesignOptionSetId': 99}},
        101: {'class': 'DesignOption', 'fields': {'m_strName': 'Option 2', 'm_DesignOptionSetId': 99}},
        99: {'class': 'DesignOptionSet', 'fields': {'m_strName': 'Set A', 'm_mainDesignOption': 100}},
        5: {'class': 'ProjectPhase', 'fields': {'m_name': 'New Construction'}},
        6: {'class': 'SWall', 'fields': {'m_designOptionId': 101}},
        7: {'class': 'SWall', 'fields': {'m_designOptionId': 0xFFFFFFFF}},
        8: {'class': 'SWall', 'fields': {'m_designOptionId': 0xFFFFFFFFFFFFFFFF}}}
class C2(Ctx):
    pass
# ctx.recs keyed like the real index: eid -> {'class','fields'}
recs[0] = {'class': 'DesignOption', 'fields': {}}
G.get_ctx = lambda f: C2(recs)
ix = G.file_geometry_index('synthetic.rvt')
assert 0 not in ix and 100 in ix and 5 in ix, ix
recs2 = dict(recs); recs2[0] = {'class': 'ProjectPhase', 'fields': {'m_name': 'New Construction'}}
G.get_ctx = lambda f: C2(recs2)
assert 0 in G.file_geometry_index('synthetic.rvt')                              # ProjectPhase id 0 is real
G.get_ctx = lambda f: C2(recs)
do = G.design_options('synthetic.rvt')
assert set(do) == {100, 101} and do[100]['main'] and not do[101]['main'] and do[101]['set_name'] == 'Set A' and do[100]['name'] == 'Empty', do
assert G.design_option('synthetic.rvt', 6) == 101 and G.design_option('synthetic.rvt', 7) is None and G.design_option('synthetic.rvt', 8) is None
print('ok')
