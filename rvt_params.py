#!/usr/bin/env python3
"""Per-element parameter dump from a Revit file, no Revit/ODA: stored values (schema-driven), learned field->parameter mapping,
family parameters by caption, geometry-derived values (curve length, MEP elevations/areas, elevation from level), UniqueId and IfcGUID.
usage: rvt_params.py FILE [--json OUT]    (prints a summary; --json writes {id: {...}})"""
import sys, os, json, math, collections, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault('RVT_GEOM', '1')
import rvt_entities as E, rvt_map2 as M, rvt_famparams as F, rvt_geom as Gm, rvt_uid, ifcguid, rvt_ifc

HERE = os.path.dirname(os.path.abspath(__file__))
MAPPING = json.load(open(os.path.join(HERE, 'map3_train.json')))['mapping']
PNAMES = json.load(open(os.path.join(HERE, 'param_names.json')))
_ENUM_FN = os.environ.get('RVT_ENUM_FILE') or os.path.join(HERE, 'enum_rules.json')
ENUM = json.load(open(_ENUM_FN)) if os.path.exists(_ENUM_FN) and not os.environ.get('RVT_NOENUM') else {}     # learn_enum.py: value = table[stored enum field] / per-class constants

def _cast(stg, v):
    try:
        if stg in ('Integer', 'ElementId'): return int(v)
        if stg == 'Double': return float(v)
    except (TypeError, ValueError): return None
    return v

def _sid(v):
    v = int(v); return v - (1 << 64) if v >= 1 << 63 else (v - (1 << 32) if 1 << 31 <= v < 1 << 32 else v)

def stored_params(f, by_name=False):
    """values stored in the element's own parameter sets (m_pParamValueSetDouble/Int/AString/ElementId), keyed by built-in/shared parameter id
    (signed) or, with by_name, by Revit's parameter name (param_names.json); ElementId values are signed ids"""
    out = {}
    sets = [(k, F.S_(f, k, 'm_paramSet')) for k in ('m_pParamValueSetDouble', 'm_pParamValueSetInt', 'm_pParamValueSetAString', 'm_pParamValueSetElementId')]
    sets += [(k, F.S_(f, 'm_oParamSet', k, 'm_paramSet')) for k in ('m_pDoubleParams', 'm_pIntParams', 'm_pAStringParams', 'm_pElementIdParams')]      # PropertySetElement (structural / thermal assets) keeps its values in m_oParamSet
    for k, ps in sets:
        if not isinstance(ps, list): continue
        for e in ps:
            if not isinstance(e, dict) or e.get('m_paramId') is None: continue
            pid = _sid(e['m_paramId']); v = e.get('m_value')
            if isinstance(v, dict): v = v.get('m_id', v)
            if 'ElementId' in k and v is not None:
                try: v = _sid(v)
                except Exception: pass
            if by_name:
                nm = PNAMES.get(str(pid))
                if nm is None: continue
                out[nm] = v
            else: out[pid] = v
    return out

def symbol_params(path, symbol_id, _depth=0):
    """type parameters of a FamilySymbol / element type: {param id: value} from its stored sets plus the family parameters by caption (rvt_famparams)"""
    import rvt_xcache; x = rvt_xcache.get_x_ro(path); r = None
    for (eid, c), rr in x['recs'].items():
        if eid == int(symbol_id): r = rr; break
    if r is None: return {}
    out = stored_params(r['fields'])
    cap = F.captions(x['recs'])
    for k, (v0, vi, vs, ve) in F.named_values({}, cap, r['fields']).items():
        if ve is not None and int(ve) not in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF): v = _sid(ve)          # ElementId parameter (e.g. Glass Pane Material)
        elif vs: v = vs
        elif vi is not None and not v0: v = vi
        else: v = v0
        out.setdefault(k, v)
    for p_ in (F.S_(r['fields'], 'm_pParams', 'm_params') or []):          # built-in type values stored next to the family parameters, keyed by the unsigned negative built-in id (Width, Height, Assembly Code, ...)
        try: bid_ = _sid(p_['m_paramId'])
        except Exception: continue
        if bid_ < -1000 and isinstance(p_.get('m_value'), float):
            v_ = p_['m_str'] if p_.get('m_str') else p_['m_value']
            out.setdefault(bid_, v_)
            if PNAMES.get(str(bid_)): out.setdefault(PNAMES[str(bid_)], v_)
    # derived symbols (per-host variants of a type, e.g. a window symbol cut for one wall) carry m_masterId = the user-visible type: its values apply
    mid = r['fields'].get('m_masterId')
    if mid is not None and int(mid) not in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF) and int(mid) != int(symbol_id) and _depth < 3:
        for k, v in symbol_params(path, int(mid), _depth + 1).items(): out.setdefault(k, v)
    return out

_CCN = None
def _file_year(path):
    try:
        import olefile
        b = olefile.OleFileIO(path).openstream('BasicFileInfo').read()
        m = re.search(r'20\d\d', b.decode('utf-16le', 'replace'))
        return m.group(0) if m else None
    except Exception: return None

def _conceptual_name(path, enum, subcat):
    """ConceptualConstructionType names are built-in strings selected by (enum, mass sub-category): conceptual_construction_names.json (learned from the corpus, one table per Revit year: 2025+ spell the dash as a hyphen)"""
    global _CCN
    if _CCN is None:
        try: _CCN = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conceptual_construction_names.json')))
        except Exception: _CCN = {}
    y = _file_year(path); t = _CCN.get(y) or _CCN.get('2020') or {}
    return t.get('%s|%d' % (enum, subcat & 0xFFFFFFFF))

def params(path, geom=None):
    """geom=True (or env RVT_PARAMS_GEOM=1): also geometry-derived Volume/Area/Length/Width/Height of family instances from the decoded solids
    (rvt_geomparams; meshes every family instance: minutes on large files)"""
    if geom is None: geom = bool(os.environ.get('RVT_PARAMS_GEOM'))
    import rvt_xcache; x = rvt_xcache.get_x_ro(path); recs = {}
    for (eid, c), r in x['recs'].items(): recs.setdefault(eid, r)
    hdr = {eid: {'fields': f} for eid, f in x['eh'].items()}
    src = M.Src(recs, hdr); cap = F.captions(x['recs'])
    lv = {}
    for (eid, c), r in x['recs'].items():
        if c == 'Level':
            o = E.S_(r['fields'], 'm_pSurface', 'm_origin')
            if o: lv[eid] = o[2]
    uid = rvt_uid.unique_ids(path)
    st = rvt_ifc.stored({e: [r] for e, r in recs.items()})
    import rvt_scan as S; own = S.owners(path); out = {}; refelev_ = {}
    for eid, r in recs.items():
        c = r['class']; f = r['fields']; d = {}
        for pid, cands in MAPPING.get(c, {}).items():
            nm = PNAMES.get(pid) if pid != 'NAME' else 'Name'
            if nm is None: continue
            for cd in cands:
                if 'm_pParamValueSet' in cd.get('path', '') or 'm_pParams.obj.m_params[' in cd.get('path', ''):                # positional slots of the stored parameter sets shift per element: use a slot only when it holds this parameter (same id or same name)
                    if pid == 'NAME' or not cd['path'].endswith('.m_value'): continue
                    sp_ = M.resolve(src, eid, cd.get('via', ''), cd['path'][:-len('.m_value')] + '.m_paramId')
                    if sp_ is None: continue
                    sp_ = _sid(sp_)
                    if sp_ != int(pid) and PNAMES.get(str(sp_)) not in (None, nm): continue      # the slot holds another known parameter (rooms: Comments/Floor Finish shift Name/Number)
                if 'default' in cd: d[nm] = cd['default']; break
                v = M.resolve(src, eid, cd.get('via', ''), cd['path'])
                if v is not None and not (isinstance(v, int) and v in M.SENT): d[nm] = v; break
        d.update(stored_params(f, by_name=True))
        sid = F.S_(f, 'm_pInstanceInfo', 'm_symbolId'); sym = recs.get(int(sid), {}).get('fields') if sid is not None else None
        for k, (v0, vi, vs, ve) in F.named_values(f, cap, sym).items():
            if isinstance(v0, (int, float)): d.setdefault(k, float(v0))
        if c in ('RbsPipeCurve', 'RbsDuctCurve', 'RbsConduitCurve', 'CableTray'):
            g_ = Gm.mep_curve(f, c, lv); k_ = g_.pop('_end_k', None); R_ = g_.pop('_end_R', None); d.update(g_)
            t_ = d.get('Insulation Thickness', 0.0)                      # no insulation recorded on the run: the insulation surface is the outer surface
            t_ = float(t_) if isinstance(t_, (int, float)) and not isinstance(t_, bool) else None
            if k_ is not None and t_ is not None:                 # insulation surface = outer radius + thickness
                for nm_ in ('Lower End', 'Upper End'):
                    z_ = d[nm_ + ' Centerline Elevation']; d[nm_ + ' Bottom of Insulation Elevation'] = z_ - (R_ + t_) * k_; d[nm_ + ' Top of Insulation Elevation'] = z_ + (R_ + t_) * k_
        elif c == 'PropertySetElement' and isinstance(d.get('Density'), float):
            d['Unit weight'] = d['Density'] * 9.80665 / 0.3048            # structural asset: Revit shows Unit weight = Density x standard gravity (ft/s2); the stored -1140309 value is stale
        elif c == 'MaterialElem':                                      # MaterialElem.m_pMaterial (decoded and validated 530/530 by rvt_materials)
            mt = F.S_(f, 'm_pMaterial') or {}
            for k_, nm_ in (('m_transparency', 'Transparency'), ('m_smoothness', 'Smoothness'), ('m_shininess', 'Shininess')):
                if isinstance(mt.get(k_), (int, float)) and not isinstance(mt.get(k_), bool): d[nm_] = int(round(mt[k_] * 100)) if isinstance(mt[k_], float) else mt[k_]          # floats are stored 0..1, Revit shows percent
        elif c == 'Rebar':                                             # m_oInstance: nominal bar length, bar positions, layout (measured: Bar Length / Layout Rule exact, Quantity = positions minus excluded first / last bar)
            oi_ = f.get('m_oInstance'); oi_ = oi_.get('obj', oi_) if isinstance(oi_, dict) else None
            if oi_ and isinstance(oi_.get('m_barLength'), float) and isinstance(oi_.get('m_numberOfBarPositions'), int):
                np_ = oi_['m_numberOfBarPositions']; q_ = np_ - (0 if oi_.get('m_includeFirstBar', 1) else 1) - (0 if oi_.get('m_includeLastBar', 1) else 1)
                _setp(d, 'Bar Length', 'Double', oi_['m_barLength']); _setp(d, 'Quantity', 'Integer', q_)
                if isinstance(oi_.get('m_layoutRule'), int): _setp(d, 'Layout Rule', 'Integer', oi_['m_layoutRule'])
                _setp(d, 'Spacing', 'Double', oi_['m_maxSpacing'] if oi_.get('m_layoutRule') in (2, 3) and isinstance(oi_.get('m_maxSpacing'), float) else 0.0)
                _setp(d, 'Total Bar Length', 'Double', q_ * oi_['m_barLength'])
        elif c == 'ReferencePoint':                                      # analytical reference points: Associated Level = the level nearest to the point's z, offset = z - level elevation (2023 rst_advanced samples 4/4 exact; unvalidated at scale)
            o_ = F.S_(f, 'm_Trf', 'm_or') or F.S_(f, 'm_ExplicitTrf', 'm_or')
            if isinstance(o_, list) and len(o_) == 3 and lv:
                z_, e_ = min((abs(z_ - o_[2]), (z_, e_)) for e_, z_ in lv.items())[1]          # the NEAREST level (2023 rst_advanced: 471 on-level + 28 points below a level)
                _setp(d, 'Associated Level', 'ElementId', int(e_)); _setp(d, 'Associated Level Offset', 'Double', o_[2] - z_)
        elif c == 'IndependentTag':                                      # Leader Line: a tagged entity with a non-zero elbow / end offset has a leader (2024 Snowdon Structural samples: offsets 0 -> 0, elbow offset set -> 1)
            te_ = ((f.get('m_taggedEntitiesCell') or {}).get('obj') or {}).get('m_taggedEntities')
            if isinstance(te_, list) and te_:
                ld_ = 0
                for t_ in te_:
                    o_ = (t_.get('obj') if isinstance(t_, dict) else None) or {}
                    for k_ in ('m_elbowOffset', 'm_endOffset'):
                        xyz_ = (o_.get(k_) or {}).get('m_xyz')
                        if isinstance(xyz_, list) and any(isinstance(v_, float) and abs(v_) > 1e-9 for v_ in xyz_): ld_ = 1
                _setp(d, 'Leader Line', 'Integer', ld_)
        if c in ('RoomElem', 'SpaceElem'):                               # default people heat gains (internal units) of every room (1288 of 1288 in the corpus) and 98% of spaces
            for nm_, v_ in (('Latent Heat Gain per person', 630.91814901260966), ('Sensible Heat Gain per person', 788.6476862657621), ('Total Heat Gain per person', 1419.5658352783718)):
                if c == 'RoomElem' or not any(k_.split('|')[0] == nm_ for k_ in d): _setp(d, nm_, 'Double', v_)          # rooms always carry the default (the learned slot guess was wrong for 165 of 323 in rme_basic)
        if c in ('RoomElem', 'SpaceElem') and isinstance(f.get('m_dRoomCavityRatio'), float):       # lighting analysis value stored on the record (rme_basic 2020: 81 of 81 exact)
            _setp(d, 'Room Cavity Ratio', 'Double', f['m_dRoomCavityRatio'])
        elif c == 'AnalyticalMember':                                    # end releases: m_cellList cells with m_releaseType (start, end); fixed (0) = no moment released, otherwise start Mx/My/Mz = 0/1/1, end 1/1/1 (2023 rst_advanced: 393 + 4 + 203 members, all exact)
            rt_ = [((c_.get('obj') if isinstance(c_, dict) else None) or {}).get('m_releaseType') for c_ in (((f.get('m_cellList') or {}).get('obj') or {}).get('m_cells') or [])]
            rt_ = [v_ for v_ in rt_ if isinstance(v_, int)]
            if len(rt_) >= 2:
                for nm_, v_, mm_ in (('Start', rt_[0], (0, 1, 1)), ('End', rt_[1], (1, 1, 1))):
                    _setp(d, nm_ + ' Release', 'Integer', v_)
                    for ax_, m_ in zip('xyz', mm_ if v_ else (0, 0, 0)): _setp(d, '%s M%s' % (nm_, ax_), 'Integer', m_)
        elif c == 'FamilyInstance':
            d.update(Gm.fam_instance(f, lv))
            re_ = d.pop('_refelev', None)
            if re_ is not None: refelev_[eid] = re_
            if sym is not None and isinstance(f.get('m_elevation'), float) and not any(k_.split('|')[0] == 'Head Height' for k_ in d):          # windows / doors: Head Height = sill (m_elevation) + type Height (-1001300)
                for p_ in (F.S_(sym, 'm_pParams', 'm_params') or []):
                    try: bid_ = _sid(p_['m_paramId'])
                    except Exception: continue
                    if bid_ == -1001300 and isinstance(p_.get('m_value'), float): _setp(d, 'Head Height', 'Double', f['m_elevation'] + p_['m_value']); break
            for c_ in (((f.get('m_cellList') or {}).get('obj') or {}).get('m_cells') or []):          # structural members: join cutbacks stored in the cell (m_cutbacks = [start, end]; rst_basic 2020: 139 / 117 members exact)
                cb_ = ((c_.get('obj') if isinstance(c_, dict) else None) or {}).get('m_cutbacks')
                if isinstance(cb_, list) and len(cb_) == 2 and all(isinstance(v_, float) for v_ in cb_):
                    _setp(d, 'Start Join Cutback', 'Double', cb_[0]); _setp(d, 'End Join Cutback', 'Double', cb_[1]); break
            if sym is not None and 'm_isHostPanelSym' in sym:          # curtain panel: its (derived) symbol stores the cell size; wall-type panels report Volume 0
                w = F.S_(sym, 'm_refs'); w = F.S_(w[0], 'm_width') if isinstance(w, list) and w else None
                h = F.S_(sym, 'm_refs'); h = F.S_(h[0], 'm_height') if isinstance(h, list) and h else None
                if isinstance(w, float) and isinstance(h, float):
                    d['Width'], d['Height'] = w, h
                    if w > 0 and h > 0: d['Area'] = w * h
                if sym.get('m_isHostPanelSym') == 1: d['Volume'] = 0.0
        elif c == 'SWall' or c.endswith('CenterLine') or c == 'CurveElem' or c.startswith('AnalyticalModel'):
            cu = Gm.primary_curve(f)
            if cu is not None and Gm.curve_length(cu) is not None: d['Length'] = Gm.curve_length(cu)
            ud = ((f.get('m_data') or {}).get('m_oUserData') or {}) if isinstance(f.get('m_data'), dict) else {}
            ud = ud.get('obj') if isinstance(ud, dict) and 'obj' in ud else ud
            if isinstance(ud, dict) and isinstance(ud.get('m_angle'), float): d['Slope'] = math.tan(ud['m_angle'])      # sketch line of a roof/floor/ceiling: Revit's Slope = rise/run = tan(m_angle)
        wr = f.get('m_witnessRefs')
        if isinstance(wr, list) and wr and 'Dim' in c: d['Count|Integer'] = len(wr)      # dimension strings: Revit's Count = number of references (witness lines)
        # universal lookups (class independent): category and design option come from the element header
        hf = x['eh'].get(eid) or {}
        UNIV = not os.environ.get('RVT_NOUNIV')
        def _sg(v):
            v = int(v); return v - (1 << 64) if v >= 1 << 63 else (v - (1 << 32) if 1 << 31 <= v < 1 << 32 else v)
        if UNIV: cid = hf.get('m_categroryId'); d['Category|ElementId'] = _sg(cid) if cid is not None else -1
        dop = hf.get('m_designOptionId', f.get('m_designOptionId')); dop = _sg(dop) if dop is not None else -1
        if UNIV: d['Design Option|ElementId'] = dop
        if UNIV: d['Design Option|String'] = 'Main Model' if dop == -1 else (recs.get(dop, {}).get('fields', {}).get('m_name') or 'Main Model')
        if eid in uid:
            d['UniqueId'] = uid[eid]; d['IfcGUID'] = st.get(eid) or ifcguid.from_unique(uid[eid])
            o = own.get(eid)
            if not st.get(eid) and c.endswith('CenterLine') and o is not None and o in uid: d['IfcGUID'] = st.get(o) or ifcguid.from_unique(uid[o])
        pre = dict(d)                                                    # values derived before the learned rules: a rule never replaces one of the same storage
        _ok = {'String': str, 'Integer': int, 'Double': float, 'ElementId': int}
        for bip, ru in ENUM.get(c, {}).items():
            nm = PNAMES.get(bip)
            ovr = nm == 'Category' and not os.environ.get('RVT_NOCATOVR')      # learned per-class Category beats the header category (centre lines, views, styles: header holds a sub-category)
            if nm is None: continue
            rs_ = ru['const'][0] if 'const' in ru else (ru.get('identity') or next(iter(ru['table'].values()))[0])
            if not ovr and ((nm + '|' + rs_) in pre or (nm in pre and isinstance(pre[nm], _ok.get(rs_, object)) and not (rs_ == 'Double' and isinstance(pre[nm], bool)))): continue
            if 'const' in ru: v = _cast(*ru['const']); stg_ = ru['const'][0]
            else:
                import learn_enum as _LE
                k = _LE._key(M.resolve(src, eid, ru['via'], ru['path']))
                hit = ru['table'].get(k) if k is not None else None
                if hit is None and ru.get('identity') and k is not None: hit = [ru['identity'], k.strip("'")]
                v = _cast(*hit) if hit else None; stg_ = hit[0] if hit else None
            if v is not None:
                d['%s|%s|%s' % (nm, stg_, bip)] = v                    # parameter-id key: same-name parameters keep separate values
                if nm not in d: d[nm] = v
                if ovr: d['Category|ElementId'] = v
        if c == 'ConceptualConstructionType':                            # energy-analysis construction types: the type name is the symbol name
            sc_ = f.get('m_massSurfaceSubCategoryId')
            nm_ = _conceptual_name(path, f.get('m_conceptualConstructionTypeEnumAsInt'), _sid(sc_)) if sc_ is not None else None
            if isinstance(nm_, str) and nm_: _setp(d, 'Type Name', 'String', nm_)
        if c == 'FamilySymbol':                                          # a symbol's own family parameters (profile dims, door/window widths) by caption: exact, beat the positional learned guesses
            for k_, (v0_, vi_, vs_, ve_) in F.named_values({}, cap, f).items():
                if isinstance(v0_, float) and not vs_ and (ve_ is None or int(ve_) in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF)): _setp(d, k_, 'Double', v0_)
        if c == 'FamilySymbol':                                          # built-in parameters stored in the symbol's own m_pParams (paramId = -bip): thermal / optical values, analytic construction
            for p_ in (F.S_(f, 'm_pParams', 'm_params') or []):
                try: bid_ = _sid(p_['m_paramId'])
                except Exception: continue
                nm_ = PNAMES.get(str(bid_)) if bid_ < -1000 else None
                if nm_ is None or not isinstance(p_.get('m_value'), float): continue
                if p_.get('m_str'): _setp(d, nm_, 'String', p_['m_str'])
                else: _setp(d, nm_, 'Double', p_['m_value'])
                if nm_ in d and not isinstance(d[nm_], str) and p_.get('m_str'): del d[nm_]
            if d.get('Category|ElementId') in (-2000023, -2000014):          # door / window types: Rough Width / Height absent = 0 (765 of 901 corpus values)
                for nm_ in ('Rough Width', 'Rough Height'):
                    if not any(k_.split('|')[0] == nm_ and '|Double' in k_ for k_ in d) and not isinstance(d.get(nm_), float): _setp(d, nm_, 'Double', 0.0)
        out[eid] = {'class': c, 'params': d}
    if geom:
        import rvt_elemmesh as EM, rvt_geomparams as GP
        doc = EM.Doc(path)
        for eid, o in out.items():
            if o['class'] == 'RoomElem' and eid in doc.res:
                try:
                    for k_, v_ in GP.room_params(doc, eid).items(): o['params'][k_] = v_
                except Exception: pass
                continue
            if o['class'] not in ('FamilyInstance', 'SWall') and o['class'] not in GP.HOSTS or eid not in doc.res: continue
            cat = o['params'].get('Category|ElementId', -1)
            try: gp = GP.geom_params(doc, eid, recs[eid]['fields'], cat, o['class'])
            except Exception: continue
            exact = set()
            if 'Width' in o['params'] and 'Height' in o['params']: exact |= {'Width', 'Height', 'Area'}      # curtain panel cell from its symbol (exact)
            if o['params'].get('Volume') == 0.0: exact.add('Volume')                                      # wall-type curtain panel
            for k, v in gp.items():
                if k in ('Width', 'Height') and cat == -2000023 and o['params'].get(k) not in (None, 0, 0.0): continue       # door sizes from the mesh only when the type gives none
                if k not in exact: o['params'][k] = v
    # analytical members take the physical member's Length (FamilyInstance.m_oFamInstUserData.m_analyticalModelId)
    for eid, o in list(out.items()):
        if o['class'] == 'FamilyInstance' and 'Length' in o['params']:
            am = F.S_(recs[eid]['fields'], 'm_oFamInstUserData', 'm_analyticalModelId')
            if am is not None and int(am) in out and out[int(am)]['class'].startswith('AnalyticalModel'): out[int(am)]['params'].setdefault('Length', o['params']['Length'])
    # structural framing: Elevation at Top / Bottom of horizontal members from the reference level + offset, the z justification and the section depth (type Height / Diameter); 0 for sloped members and 'origin' justification (rst_basic 2020 gt: 256+18 members)
    for e_, re_ in refelev_.items():
        o_ = out.get(e_)
        if o_ is None or o_['params'].get('Category|ElementId') != -2001320: continue
        p_ = o_['params']; so_, eo_ = p_.get('Start Level Offset'), p_.get('End Level Offset')
        if not isinstance(so_, float) or not isinstance(eo_, float): continue
        zj_ = p_.get('z Justification|Integer', p_.get('z Justification')); top_ = bot_ = 0.0
        sid_ = F.S_(recs[e_]['fields'], 'm_pInstanceInfo', 'm_symbolId'); sym_ = recs.get(int(sid_), {}).get('fields') if sid_ is not None else None
        dep_ = None
        if sym_ is not None:
            nv_ = F.named_values({}, cap, sym_)
            for k_ in ('Height', 'Diameter', 'Depth', 'h', 'd'):
                if k_ in nv_ and isinstance(nv_[k_][0], float) and nv_[k_][0] > 0: dep_ = nv_[k_][0]; break
        if abs(so_ - eo_) < 1e-6 and dep_ is not None and zj_ in (0, 1, 2):
            zo_ = p_.get('z Offset Value|Double', p_.get('z Offset Value')); z_ = re_ + so_ + (zo_ if isinstance(zo_, float) else 0.0)          # the instance's z offset (e.g. 0.1837 on the 50x200 timbers) shifts the member line
            top_, bot_ = {0: (z_, z_ - dep_), 1: (z_ + dep_ / 2, z_ - dep_ / 2), 2: (z_ + dep_, z_)}[zj_]
        elif abs(so_ - eo_) < 1e-6 and zj_ in (0, 1, 2): continue
        _setp(p_, 'Elevation at Top', 'Double', top_); _setp(p_, 'Elevation at Bottom', 'Double', bot_)
    # reference points: Location Mark = the two nearest non-parallel straight grids with the signed plan offset in mm (positive towards +x / +y), letters before digits, '(0)' omitted (2023 rst_advanced: 467 of 499 exact; curved grids not handled)
    gr_ = []
    for e_, r_ in recs.items():
        if r_['class'] != 'Grid' or e_ not in out: continue
        sf_ = (F.S_(r_['fields'], 'm_pSurface') or {}); sf_ = sf_.get('obj', sf_) if isinstance(sf_, dict) else {}
        nm_ = out[e_]['params'].get('Name')
        if not isinstance(sf_, dict) or 'm_origin' not in sf_ or not isinstance(nm_, str): continue
        for k_ in ('m_xVec', 'm_yVec'):
            v_ = sf_.get(k_)
            if isinstance(v_, list) and len(v_) == 3 and abs(v_[2]) < 1e-6 and math.hypot(v_[0], v_[1]) > 0.5:
                h_ = math.hypot(v_[0], v_[1]); gr_.append((nm_, sf_['m_origin'][0], sf_['m_origin'][1], v_[0] / h_, v_[1] / h_)); break
    if len(gr_) >= 2:
        def _lm_n(g_):
            nx_, ny_ = -g_[4], g_[3]
            return (nx_, ny_) if (nx_ + ny_) > 1e-9 or (abs(nx_ + ny_) <= 1e-9 and nx_ - ny_ > 0) else (-nx_, -ny_)
        def _lm(t_):
            cand_ = sorted(((abs((t_[0] - g_[1]) * _lm_n(g_)[0] + (t_[1] - g_[2]) * _lm_n(g_)[1]), g_) for g_ in gr_), key=lambda z_: z_[0])
            pick_ = []
            for dist_, g_ in cand_:
                if all(abs(g_[3] * q_[3] + g_[4] * q_[4]) < 0.5 for _d, q_ in pick_): pick_.append((dist_, g_))
                if len(pick_) == 2: break
            if len(pick_) < 2: return None
            parts_ = []
            for _d, g_ in pick_:
                mm_ = round(((t_[0] - g_[1]) * _lm_n(g_)[0] + (t_[1] - g_[2]) * _lm_n(g_)[1]) * 304.8)
                parts_.append(g_[0] if mm_ == 0 else '%s(%d)' % (g_[0], mm_))
            return '-'.join(sorted(parts_, key=lambda q_: (q_[0].isdigit(), q_)))
        for e_, o_ in out.items():
            if o_['class'] == 'ReferencePoint': t_ = F.S_(recs[e_]['fields'], 'm_Trf', 'm_or'); nm_ = 'Location Mark'
            elif o_['class'] == 'FamilyInstance' and o_['params'].get('Category|ElementId') == -2001330: t_ = F.S_(recs[e_]['fields'], 'm_pInstanceInfo', 'm_Trf', 'm_or'); nm_ = 'Column Location Mark'      # structural columns: same mark at the column's base point
            else: continue
            if not isinstance(t_, list) or len(t_) < 2: continue
            v_ = _lm(t_)
            if v_: _setp(o_['params'], nm_, 'String', v_)
    if not os.environ.get('RVT_NOHOST'): _host_params(out, recs)
    if not os.environ.get('RVT_NOVIEWSHEET'): _view_sheet_params(out, recs)
    _thermal_params(out, recs); _material_type(out, recs)
    _circuit_params(out, recs); _wire_params(out, recs); _fi_circuit_params(out, recs); _fi_system_params(out, recs); _hub_params(out, recs, _file_year(path))
    # round ducts (type Family Name 'Round Duct'): Area = pi d L and a Diameter, not the rectangular 2 (w + h) L
    for o_ in out.values():
        if o_['class'] != 'RbsDuctCurve': continue
        p_ = o_['params']; t_ = p_.get('Type Id'); fn_ = (out.get(t_) or {}).get('params', {}).get('Family Name') if isinstance(t_, int) else None
        if isinstance(fn_, str) and 'Round' in fn_ and isinstance(p_.get('Width'), float) and isinstance(p_.get('Length'), float):
            p_['Diameter'] = p_['Width']; p_['Area'] = math.pi * p_['Width'] * p_['Length']
    # RebarInSystem (area reinforcement members): bars decoded by rvt_rebar.area_reinforcement_bars (Bar Length, Quantity, Spacing exact on rst_basic 2020; Layout Rule 2)
    ris_ = collections.defaultdict(list)
    for e_, o_ in out.items():
        if o_['class'] == 'RebarInSystem':
            sid_ = recs[e_]['fields'].get('m_systemId')
            if sid_ is not None: ris_[_sid(sid_)].append(e_)
    if ris_ and not os.environ.get('RVT_NORIS'):
        try: import rvt_rebar as RB
        except Exception: RB = None
        for sid_, mem_ in ris_.items():
            try: res_ = RB.area_reinforcement_bars(path, sid_) if RB else None
            except Exception: res_ = None
            for e_ in mem_:
                v_ = (res_ or {}).get(e_)
                if not v_ or not v_.get('bars'): continue
                bars_ = v_['bars']; ln_ = [sum(math.dist(c['p0'], c['p1']) for c in b_ if c.get('type') == 'line') for b_ in bars_]
                p_ = out[e_]['params']
                _setp(p_, 'Bar Length', 'Double', ln_[0]); _setp(p_, 'Quantity', 'Integer', len(bars_)); _setp(p_, 'Total Bar Length', 'Double', float(sum(ln_))); _setp(p_, 'Layout Rule', 'Integer', 2)
                _setp(p_, 'Spacing', 'Double', math.dist(bars_[0][0]['p0'], bars_[1][0]['p0']) if len(bars_) > 1 else 0.0)
                if isinstance(v_.get('diameter'), float): _setp(p_, 'Reinforcement Volume', 'Double', float(sum(ln_)) * math.pi * (v_['diameter'] / 2) ** 2)
    for o_ in out.values():                                          # rebar: volume = total bar length x bar cross-section (Bar Diameter follows from the bar type by the learned rules)
        if o_['class'] != 'Rebar': continue
        p_ = o_['params']; t_ = p_.get('Total Bar Length|Double'); bd_ = next((v_ for k_, v_ in p_.items() if k_.split('|')[0] == 'Bar Diameter' and isinstance(v_, float)), None)
        if isinstance(t_, float) and bd_ is not None:
            for nm_ in ('Reinforcement Volume', 'Estimated Reinforcement Volume'): _setp(p_, nm_, 'Double', t_ * math.pi * (bd_ / 2) ** 2)
    for o_ in out.values():                                          # Family.Host (hosting behaviour): 0 for 91% of families (63 of 69 in rst_basic / Snowdon Structural); the hosted ones are not identified yet
        if o_['class'] == 'Family' and not any(k.split('|')[0] == 'Host' and '|Integer' in k for k in o_['params']): o_['params']['Host|Integer'] = 0
    for o_ in out.values():                                          # MEP fittings: Maximum / Minimum Size = largest / smallest round connector diameter named in the Size string
        if o_['class'] != 'FamilyInstance': continue
        sz_ = o_['params'].get('Size')
        if not isinstance(sz_, str) or 'ø' not in sz_: continue
        parts_ = sz_.split('-')
        m_ = [re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(mm|")ø\s*', t) for t in parts_]
        if not all(m_): continue
        ds_ = [float(m.group(1)) / 304.8 if m.group(2) == 'mm' else float(m.group(1)) / 12 for m in m_]
        _setp(o_['params'], 'Maximum Size', 'Double', max(ds_)); _setp(o_['params'], 'Minimum Size', 'Double', min(ds_))
    for o_ in out.values():                                          # pipes: wall thickness = (outside - inside diameter) / 2
        if o_['class'] != 'RbsPipeCurve': continue
        p_ = o_['params']; od_, id_ = p_.get('Outside Diameter'), p_.get('Inside Diameter')
        if isinstance(od_, float) and isinstance(id_, float): p_['Wall Thickness'] = (od_ - id_) / 2
    # pipes / ducts / conduits: the cell's m_systemId names the MEP system element: System Name = the system's name, System Classification from its system type
    for e_, o_ in out.items():
        if not o_['class'].startswith('Rbs') or not o_['class'].endswith('Curve'): continue
        sid_ = None
        for c_ in ((recs[e_]['fields'].get('m_cellList') or {}).get('obj') or {}).get('m_cells') or []:
            v_ = (c_.get('obj') or {}).get('m_systemId') if isinstance(c_, dict) else None
            if v_ is not None and _sid(v_) in out and out[_sid(v_)]['class'].startswith('Rbs'): sid_ = _sid(v_); break
        if sid_ is None: continue
        sp_ = out[sid_]['params']; p_ = o_['params']
        if isinstance(sp_.get('System Name'), str) and not any(k_.split('|')[0] == 'System Name' for k_ in p_): _setp(p_, 'System Name', 'String', sp_['System Name'])
        t_ = sp_.get('Type Id')
        if isinstance(t_, int) and t_ in out:
            sc_ = out[t_]['params'].get('System Classification')
            if isinstance(sc_, str) and not any(k_.split('|')[0] == 'System Classification' for k_ in p_): _setp(p_, 'System Classification', 'String', sc_)
    # pipes: Invert Elevation = reference level elevation + the inside bottom of the lowest end (outer Bottom Elevation + wall thickness for horizontal / sloped pipes, the lowest end itself for vertical ones); rme_basic 2020: 513756 47.105 = 35.761 + 11.335 + 0.0087
    for e_, o_ in out.items():
        if o_['class'] != 'RbsPipeCurve': continue
        p_ = o_['params']; bot_, top_, od_ = p_.get('Bottom Elevation'), p_.get('Top Elevation'), p_.get('Outside Diameter')
        rl_ = p_.get('Reference Level|ElementId', p_.get('Reference Level'))
        if not all(isinstance(v_, float) for v_ in (bot_, top_, od_)) or not isinstance(rl_, int) or rl_ not in lv: continue
        wt_ = p_.get('Wall Thickness') if isinstance(p_.get('Wall Thickness'), float) else 0.0
        vert_ = abs((top_ - bot_) - od_) > 1e-6 and (top_ - bot_) > 1.5 * od_
        _setp(p_, 'Invert Elevation', 'Double', lv[rl_] + bot_ + (0.0 if vert_ else wt_))
    # pipes: Fixture Units = the demand stored in the pipe's own connector modifiers (m_dDemand; 88 of 88 sanitary pipes exact on rme_basic 2020); other pipes carry 0 and Revit reports none
    for e_, o_ in out.items():
        if o_['class'] != 'RbsPipeCurve': continue
        dem_ = []
        for cn_ in (((recs[e_]['fields'].get('m_pConnectorManager') or {}).get('obj') or {}).get('m_connPtrArray') or []):
            for m_ in ((cn_.get('obj') or {}).get('m_modifiers') or []) if isinstance(cn_, dict) else []:
                mo_ = (m_.get('obj') or {}) if isinstance(m_, dict) else {}
                if isinstance(mo_.get('m_dDemand'), float): dem_.append(mo_['m_dDemand'])
        if dem_ and (max(dem_) > 0 or o_['params'].get('System Classification') == 'Sanitary'): _setp(o_['params'], 'Fixture Units', 'Double', max(dem_))
    # MEP system sections: a system (RbsHvacSystem / RbsPipingSystem) lists its members per section (m_rgSections[].m_rgSection[].m_id); the member's Section is the section it belongs to
    # (an element shared by several sections: the section where it is the second end, else the first end; measured 1020 of 1036 on rme_basic) and its System Name the system's m_strName
    sec_ = collections.defaultdict(list)
    for e_, r_ in recs.items():
        if r_['class'] not in ('RbsHvacSystem', 'RbsPipingSystem') or e_ not in out: continue
        nm_ = r_['fields'].get('m_strName')
        for s_ in r_['fields'].get('m_rgSections') or []:
            o_ = (s_ or {}).get('obj') if isinstance(s_, dict) else None
            if not isinstance(o_, dict): continue
            ce_ = [_sid(c_['m_id']) for c_ in (o_.get('m_connEnds') or [])]
            for m_ in o_.get('m_rgSection') or []:
                sec_[_sid(m_['m_id'])].append((o_.get('m_nSection'), ce_, nm_ if isinstance(nm_, str) and nm_ else out[e_]['params'].get('System Name')))
    for m_, L_ in sec_.items():
        if m_ not in out: continue
        c1 = [l[0] for l in L_ if len(l[1]) > 1 and l[1][1] == m_]; c0 = [l[0] for l in L_ if l[1] and l[1][0] == m_]
        sel_ = max(c1) if c1 else (min(c0) if c0 else min(l[0] for l in L_))
        p_ = out[m_]['params']
        if isinstance(sel_, int): _setp(p_, 'Section', 'Integer', sel_)
        nm_ = next((l[2] for l in L_ if l[0] == sel_ and l[2]), None)
        if isinstance(nm_, str) and not any(k_.split('|')[0] == 'System Name' for k_ in p_): _setp(p_, 'System Name', 'String', nm_)
    # centre-line sub-elements of pipes/ducts (SegmentCenterLine, m_OwnerId) carry their run's end elevations and Area
    for e_, o_ in out.items():
        if not o_['class'].endswith('CenterLine') or o_['class'] == 'CurveElem': continue
        ow = recs[e_]['fields'].get('m_OwnerId'); ow = int(ow) if ow is not None else None
        if ow in out:
            INH = ('Reference Level', 'Material', 'Level', 'System Type', 'Diameter', 'System Classification', 'System Name')      # a centre line reports its owner's values (measured identical on 3k Snowdon Plumbing centre lines)
            for k_ in [k for k in o_['params'] if k.split('|')[0] in INH and any(kk.split('|')[0] == k.split('|')[0] for kk in out[ow]['params'])]: del o_['params'][k_]
            for k_, v_ in out[ow]['params'].items():
                if k_.split('|')[0] in INH: o_['params'][k_] = v_
            for k_, v_ in out[ow]['params'].items():
                if (' End ' in k_ and 'Elevation' in k_) or k_.split('|')[0] in ('Area', 'Wall Thickness', 'Top Elevation', 'Bottom Elevation', 'Middle Elevation', 'Invert Elevation', 'Fixture Units'): o_['params'].setdefault(k_, v_)
    # OmniClass Title follows from the OmniClass Number (standard table; omniclass_titles.json holds the 73 numbers seen in the corpus, one title each)
    try: _OT = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'omniclass_titles.json')))
    except Exception: _OT = {}
    for o_ in out.values():
        p_ = o_['params']; n_ = p_.get('OmniClass Number')
        if isinstance(n_, str) and n_ in _OT and not p_.get('OmniClass Title'): _setp(p_, 'OmniClass Title', 'String', _OT[n_])
    # duct fitting families (formula parameters): OffsetWidth = Width1 / 2, OffsetHeight = Height1 / 2 (rme_basic 2020: 393414 .738 = 1.476 / 2, .779 = 1.558 / 2; 393568 .410 = .820 / 2)
    for o_ in out.values():
        if o_['class'] != 'FamilyInstance' or o_['params'].get('Category|ElementId') != -2008010: continue
        p_ = o_['params']
        for nm_, src_ in (('OffsetWidth', 'Width1'), ('OffsetHeight', 'Height1')):
            v_ = p_.get(src_ + '|Double', p_.get(src_))
            if not isinstance(v_, float): v_ = p_.get('Diameter|Double', p_.get('Diameter'))          # round fittings: half the diameter
            if isinstance(v_, float) and not any(k_.split('|')[0] == nm_ for k_ in p_): _setp(p_, nm_, 'Double', v_ / 2)
    # Type IfcGUID: an instance carries its type's IfcGUID, a type element its own (both = ifcguid.from_unique(UniqueId) unless an IFC GUID is stored)
    for o_ in out.values():
        p_ = o_['params']
        if 'Type IfcGUID' in p_: continue
        t_ = p_.get('Type Id')
        if isinstance(t_, int) and t_ in out and out[t_]['params'].get('IfcGUID'): p_['Type IfcGUID'] = out[t_]['params']['IfcGUID']
        elif t_ is None and p_.get('IfcGUID'): p_['Type IfcGUID'] = p_['IfcGUID']
    # Type (String) = the type's Type Name: OFF by default (measured worse on Commercial + Snowdon Structural 2024, 2026-10-15); RVT_TYPESTR=1 enables
    for o_ in out.values():
        p_ = o_['params']; t_ = p_.get('Type Id')
        if not os.environ.get('RVT_TYPESTR') or 'Type|String' in p_ or not isinstance(t_, int) or t_ not in out: continue
        tn_ = out[t_]['params'].get('Type Name')
        if isinstance(tn_, str) and tn_: _setp(p_, 'Type', 'String', tn_)
    # 'Level' is both a String (level name) and an ElementId parameter (rooms): the id follows from the name when exactly one Level carries it
    lvn = collections.defaultdict(list)
    for e_, o_ in out.items():
        if o_['class'] == 'Level' and o_['params'].get('Name'): lvn[o_['params']['Name']].append(e_)
    for o_ in out.values():
        v_ = o_['params'].get('Level')
        if isinstance(v_, str) and 'Level|ElementId' not in o_['params'] and len(lvn.get(v_, ())) == 1: o_['params']['Level|ElementId'] = lvn[v_][0]
    return out

_INVALID = (None, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
def _setp(d, nm, stg, v):
    """derived value for parameter name+storage: replaces learned per-parameter-id guesses of the same name and storage"""
    d[nm + '|' + stg] = v
    for k in [k for k in d if k.startswith(nm + '|' + stg + '|')]: del d[k]

_THERMAL_ASSET = 'ec0048162207264ba23504ffc53660d5'       # m_sharedAssetIdMap key of a material's thermal asset (PropertySetElement)

def _thermal_params(out, recs):
    """layered types (m_pCompoundStructure): Thermal Resistance (R) = sum width / conductivity, U = 1/R, Thermal Mass = sum width * density * specific heat of each
    layer material's thermal asset (measured exact on wall types, 2023 Construction template: 9.486 / 144361 vs Revit 9.4859 / 144359.5); Roughness/Absorptance from the type cell"""
    for eid, r in recs.items():
        f = r['fields']
        if eid in out:
            cl_ = ((f.get('m_cellList') or {}).get('obj') or {}).get('m_cells') or []
            for c_ in cl_:
                c_ = c_.get('obj', c_) if isinstance(c_, dict) else {}
                if isinstance(c_.get('m_absorptance'), float): _setp(out[eid]['params'], 'Absorptance', 'Double', c_['m_absorptance'])
                if isinstance(c_.get('m_roughness'), int): _setp(out[eid]['params'], 'Roughness', 'Integer', c_['m_roughness'])
        cs = f.get('m_pCompoundStructure')
        if not isinstance(cs, dict):
            if eid in out and out[eid]['class'] == 'CompoundCeilingType':          # basic (single-layer 'Generic') ceiling: no structure, no thermal data in Revit either
                for nm_ in ('Thermal Resistance (R)', 'Thermal Mass', 'Heat Transfer Coefficient (U)'): _setp(out[eid]['params'], nm_, 'Double', 0.0)
            continue
        cs = cs.get('obj', cs); L = cs.get('m_layers') if isinstance(cs, dict) else None
        if not isinstance(L, list) or eid not in out: continue
        d = out[eid]['params']; R = 0.0; M_ = 0.0; tot = 0.0; ok = True
        for l in L:
            w = l.get('m_layerWidth')
            if not isinstance(w, float): ok = False; break
            tot += w
            if w <= 0: continue
            m = recs.get(_sid(l.get('m_materialId'))); mt = (m or {}).get('fields', {}).get('m_pMaterial') if m else None
            mt = mt.get('obj', mt) if isinstance(mt, dict) else None
            ps = None
            for s_ in ((mt or {}).get('m_assetMap') or {}).get('m_sharedAssetIdMap') or []:
                if (((s_.get('first') or {}).get('m_value') or {}).get('m_guid')) == _THERMAL_ASSET: ps = out.get(_sid(s_.get('second')), {}).get('params')
            k_ = ps.get('Thermal Conductivity') if ps else None; dn = ps.get('Density') if ps else None; sh = ps.get('Specific Heat') if ps else None
            if not all(isinstance(v, float) for v in (k_, dn, sh)) or k_ <= 0: continue            # layer material without thermal asset (e.g. 'Default'): contributes nothing; a type with none reports 0 / 0 / 0
            R += w / k_; M_ += w * dn * sh
        if not ok: continue
        _setp(d, 'Thermal Resistance (R)', 'Double', R); _setp(d, 'Thermal Mass', 'Double', M_)
        _setp(d, 'Heat Transfer Coefficient (U)', 'Double', 1.0 / R if R > 0 else 0.0)
        if out[eid]['class'] == 'BasicWallType': _setp(d, 'Width', 'Double', tot)

_MATTYPE = {3: 1, 4: 2, 5: 3, 1: 4, 7: 4, 8: 4, 2: 6}      # PropertySetElement Class of the material's structural asset slot (guid 2df6...) -> Material Type (measured 29/29 materials, 2023 Construction template)

def _material_type(out, recs):
    for eid, r in recs.items():
        if r['class'] != 'MaterialElem' or eid not in out: continue
        mt = r['fields'].get('m_pMaterial'); mt = mt.get('obj', mt) if isinstance(mt, dict) else None
        for s_ in ((mt or {}).get('m_assetMap') or {}).get('m_sharedAssetIdMap') or []:
            if (((s_.get('first') or {}).get('m_value') or {}).get('m_guid')) == '2df6c9ede4489e4aabb922c8664c012c':
                c_ = out.get(_sid(s_.get('second')), {}).get('params', {}).get('Class')
                if isinstance(c_, int) and c_ in _MATTYPE: _setp(out[eid]['params'], 'Material Type', 'Integer', _MATTYPE[c_])

def _view_sheet_params(out, recs):
    """views placed on sheets: Viewport Detail Number (m_detailNumber), Sheet Number / Sheet Name (sheet = the viewport's owner view), View Name, View Scale
    (round(1 / m_scale)); a placed view gets its viewport's values (m_sheetViewportElemIds), a view marker (Viewer/Section/elevation arrow, m_dbViewId) its view's"""
    def pv(x, nm):
        o = out.get(x); return o['params'].get(nm + '|String', o['params'].get(nm)) if o else None
    def scale(f):
        sc = f.get('m_scale'); return int(round(1.0 / sc)) if isinstance(sc, float) and sc > 0 else None
    sheets = {e for e, o in out.items() if o['class'].startswith('DBView') and isinstance(pv(e, 'Sheet Number'), str) and pv(e, 'Sheet Number') not in ('', '---')}   # sheets decode as DBViewDrafting
    info = {}
    for eid, o in out.items():
        if o['class'] != 'Viewport': continue
        f = recs[eid]['fields']; d = o['params']
        sh = f.get('m_ownerDBViewId'); sh = int(sh) if sh is not None else None; vw = f.get('m_dbViewId'); vw = int(vw) if vw is not None else None
        r = {}
        dn = f.get('m_detailNumber')
        if isinstance(dn, str): r['Detail Number'] = dn or '-'
        if sh not in _INVALID:
            for nm in ('Sheet Number', 'Sheet Name'):
                v = pv(sh, nm)
                if isinstance(v, str): r[nm] = v
        if vw not in _INVALID and vw in recs:
            vn = pv(vw, 'View Name') or pv(vw, 'Name')
            if isinstance(vn, str): r['View Name'] = vn
            sc = scale(recs[vw]['fields']) or scale(f)
            if sc: _setp(d, 'View Scale', 'Integer', sc); _setp(d, 'Scale Value    1:', 'Integer', sc)
            info[vw] = r
        for nm, v in r.items(): _setp(d, nm, 'String', v)
    for eid, o in out.items():
        f = recs[eid]['fields']; d = o['params']
        if 'm_sheetViewportElemIds' in f or o['class'].startswith('DBView'):
            sc = scale(f)
            if sc: _setp(d, 'View Scale', 'Integer', sc); _setp(d, 'Scale Value    1:', 'Integer', sc)
            for nm, v in info.get(eid, {}).items():
                if nm in ('Detail Number', 'Sheet Number', 'Sheet Name'): _setp(d, nm, 'String', v)
            if o['class'].startswith('DBView') and eid not in sheets and eid not in info:     # not placed on a sheet
                _setp(d, 'Sheet Number', 'String', '---'); _setp(d, 'Detail Number', 'String', '-')
        vw = f.get('m_dbViewId')
        if o['class'] in ('Viewer', 'Viewer3d', 'Section', 'InteriorElevArrow', 'InteriorElev', 'Callout', 'Elevation') and vw is not None and int(vw) in recs:
            vw = int(vw); r = info.get(vw)
            if vw in sheets: r = {'Sheet Number': pv(vw, 'Sheet Number'), 'Detail Number': '-'}       # the marker of a sheet itself
            _setp(d, 'Sheet Number', 'String', (r or {}).get('Sheet Number', '---')); _setp(d, 'Detail Number', 'String', (r or {}).get('Detail Number', '-'))
            sc = scale(recs[vw]['fields'])
            if sc: _setp(d, 'View Scale', 'Integer', sc); _setp(d, 'Scale Value    1:', 'Integer', sc)
            # referencing view / sheet: a marker drawn in a view that is placed on a sheet references its target view from that sheet and detail number
            hv = f.get('m_ownerDBViewId'); hv = int(hv) if hv is not None and hv not in _INVALID else None
            if hv in info and hv != vw:
                for tgt in (d, out[vw]['params'] if vw in out else None):
                    if tgt is None: continue
                    if isinstance(info[hv].get('Sheet Number'), str): _setp(tgt, 'Referencing Sheet', 'String', info[hv]['Sheet Number'])
                    if isinstance(info[hv].get('Detail Number'), str): _setp(tgt, 'Referencing Detail', 'String', info[hv]['Detail Number'])
def _wsize_key(sz):
    """sort key of a conductor size string, larger conductor = larger key: AWG '#14'..'#1' < '1/0'..'4/0' < kcmil / metric numbers"""
    t = sz.strip().lstrip('#')
    try:
        if sz.strip().startswith('#'): return -float(t)
        if t.endswith('/0'): return float(t[:-2])
        return 10 + float(re.match(r'[0-9.]+', t).group(0))
    except Exception: return 0.0

def _circuit_params(out, recs):
    """electrical circuits (RbsElectricalSystem): Number of Elements = load connectors, Panel = the panel's Panel Name (connector of type 4 to the panel),
    Voltage = the panel distribution system's line-to-ground (1 pole) or line-to-line (2/3 poles) voltage type's Actual Voltage, currents = load / voltage"""
    for e_, o_ in out.items():
        if o_['class'] != 'RbsElectricalSystem': continue
        f = recs[e_]['fields']; p_ = o_['params']
        cm = F.S_(f, 'm_pConnectorMgr', 'm_connPtrArray') or []
        loads, panel = set(), None
        for cn in cm:
            cn = cn.get('obj', cn) if isinstance(cn, dict) else {}
            for rf in cn.get('m_arrRefs') or []:
                t_ = int(rf.get('m_id')) if rf.get('m_id') is not None else None
                if t_ is None or t_ == e_: continue
                if rf.get('m_connType') == 4: panel = t_
                elif rf.get('m_connType') == 1: loads.add(t_)
        if not cm: continue
        _setp(p_, 'Number of Elements', 'Integer', len(loads))
        pp = out.get(panel, {}).get('params', {}) if panel is not None else {}
        pn = pp.get('Panel Name')
        if panel is None:
            p_['Panel'] = ''
            if not p_.get('Circuit Number'): p_['Circuit Number'] = '<unnamed>'          # circuit not connected to a panel
        elif isinstance(pn, str): p_['Panel'] = pn
        ds = pp.get('Distribution System|ElementId') or pp.get('Distribution System')
        np_ = p_.get('Number of Poles')
        if not isinstance(ds, int) or ds not in out or not isinstance(np_, int): continue
        dp = out[ds]['params']
        vt = dp.get('Line to Ground Voltage') if np_ == 1 else dp.get('Line to Line Voltage')
        v_ = out.get(vt, {}).get('params', {}).get('Actual Voltage') if isinstance(vt, int) else None
        if not isinstance(v_, float) or v_ <= 0: continue
        p_['Voltage'] = v_
        k_ = math.sqrt(3) if np_ == 3 else 1.0
        al, tl = p_.get('Apparent Load'), p_.get('True Load')
        if isinstance(al, float): p_['Apparent Current'] = al / (v_ * k_)
        if isinstance(tl, float): p_['True Current'] = tl / (v_ * k_)
        if isinstance(al, float) and isinstance(tl, float) and al > 0: p_['Power Factor'] = tl / al
        vlg = out.get(dp.get('Line to Ground Voltage'), {}).get('params', {}).get('Actual Voltage') if isinstance(dp.get('Line to Ground Voltage'), int) else None
        vg = v_ / 2.0 if np_ == 2 else (vlg if np_ == 3 and isinstance(vlg, float) and vlg > 0 else v_ / (math.sqrt(3) if np_ == 3 else 1.0))      # per-pole voltage: phase load / it = phase current (1 pole: L-G; 2 poles: L-L / 2; 3 poles: the L-G voltage type)
        pl = [p_.get('Apparent Load Phase ' + ph) for ph in 'ABC']; pl = [a for a in pl if isinstance(a, float) and a > 0]
        _setp(p_, 'Balanced Load', 'Integer', 1 if np_ > 1 and len(pl) == np_ and max(pl) - min(pl) <= 1e-6 * max(pl) else 0)      # multi-pole circuit with equal phase loads
        nph = 3 if dp.get('Phase') == 1 else 2                                # distribution system Phase 1 = three-phase (A B C), 0 = single-phase (A B)
        cn_ = p_.get('Circuit Number')
        if isinstance(cn_, str) and cn_ and all(t.strip().isdigit() for t in cn_.split(',')):
            sl = [int(t) for t in cn_.split(',')]
            if len(sl) == 1 and np_ > 1: sl = [sl[0] + 2 * k for k in range(np_)]          # a multi-pole circuit numbered by its first slot occupies every second slot below it
            pl_ = ''.join('ABC'[((t - 1) // 2) % nph] for t in sl)      # panel slots: rows of two, phases cycle per row
            p_['Phase Label'] = ''.join(sorted(pl_)) if len(pl_) == 3 else pl_          # three-pole: always 'ABC'
        if True:
            for ph in 'ABC':
                for lk, ck in (('Apparent Load Phase ', 'Apparent Current Phase '), ('True Load Phase ', 'True Current Phase ')):
                    if isinstance(p_.get(lk + ph), float): p_[ck + ph] = p_[lk + ph] / vg

def _fi_circuit_params(out, recs):
    """family instances with electrical connectors: Circuit Number = numbers of the circuits (RbsElectricalSystem, connector type 4) they sit on, Panel = the first circuit's panel"""
    for e_, o_ in out.items():
        if o_['class'] != 'FamilyInstance': continue
        cm = F.S_(recs[e_]['fields'], 'm_pConnectorManager', 'm_connPtrArray')
        if not isinstance(cm, list): continue
        cs = []
        for cn in cm:
            for rf in (cn.get('obj', cn) if isinstance(cn, dict) else {}).get('m_arrRefs') or []:
                t_ = rf.get('m_id')
                if rf.get('m_connType') == 4 and t_ is not None and int(t_) in out and out[int(t_)]['class'] == 'RbsElectricalSystem' and int(t_) not in cs: cs.append(int(t_))
        if not cs: continue
        cp = [out[c_]['params'] for c_ in cs]; nums = [q.get('Circuit Number') for q in cp]
        if not all(isinstance(v, str) for v in nums): continue
        p_ = o_['params']
        p_['Circuit Number'] = ','.join(sorted(set(nums), key=lambda v: (0, int(v)) if v.isdigit() else (1, v)))
        if isinstance(cp[0].get('Panel'), str): p_['Panel'] = cp[0]['Panel']

_SYSCLASS = {1: 'Supply Air', 2: 'Return Air', 3: 'Exhaust Air', 7: 'Hydronic Supply', 8: 'Hydronic Return', 16: 'Sanitary', 19: 'Domestic Hot Water', 20: 'Domestic Cold Water', 22: 'Other', 23: 'Fire Protection Wet'}      # connector m_eSystemType (measured 2020 rme_basic)

def _fi_system_params(out, recs):
    """family instances on duct / pipe systems: System Name = names of the connected systems (connector type 4 refs, in connector order, distinct);
    System Classification when every system connector has the same type (multi-system fittings list a classification per connector: not reproduced)"""
    for e_, o_ in out.items():
        if o_['class'] != 'FamilyInstance': continue
        cm = F.S_(recs[e_]['fields'], 'm_pConnectorManager', 'm_connPtrArray')
        if not isinstance(cm, list): continue
        names, types = [], set()
        for cn in cm:
            o = cn.get('obj', cn) if isinstance(cn, dict) else {}
            for m in o.get('m_modifiers') or []:
                m = m.get('obj', m) if isinstance(m, dict) else {}
                t_ = m.get('m_idSystem')
                if t_ is not None and int(t_) in out and out[int(t_)]['class'] in ('RbsHvacSystem', 'RbsPipingSystem'):
                    nm = out[int(t_)]['params'].get('System Name') or out[int(t_)]['params'].get('Name')
                    if isinstance(nm, str) and nm and nm not in names: names.append(nm)
                if m.get('m_eSystemType') in _SYSCLASS and m.get('m_idSystem') is not None and int(m['m_idSystem']) in out and out[int(m['m_idSystem'])]['class'] in ('RbsHvacSystem', 'RbsPipingSystem'): types.add(m['m_eSystemType'])
        if names: _setp(o_['params'], 'System Name', 'String', ','.join(names))
        if len(types) == 1 and len(names) == 1: _setp(o_['params'], 'System Classification', 'String', _SYSCLASS[next(iter(types))])

def _hub_params(out, recs, yr=None):
    """analytical nodes (Hub) and their reference points: Connection Status 2 when two or more analytical members meet at the node, else 0"""
    for e_, o_ in out.items():
        if o_['class'] != 'Hub': continue
        f = recs[e_]['fields']
        cm = F.S_(f, 'm_oConnectorManager', 'm_connPtrArray')
        if not isinstance(cm, list): continue
        n = sum(len((cn.get('obj', cn) if isinstance(cn, dict) else {}).get('m_arrRefs') or []) for cn in cm)
        k1 = {recs[int(a['m_id'])]['class'] for cn in cm for a in (cn.get('obj', cn) if isinstance(cn, dict) else {}).get('m_arrRefs') or [] if int(a['m_id']) in recs}
        st = 1 if n >= 2 or (k1 & {'AnalyticalModelBeam', 'AnalyticalModelSlab', 'AnalyticalMember'}) else 0      # one member alone: beams / slabs report connected, columns mostly not (rst_basic: 21 of 28 columns connected: remainder open; 2023 analytical members: 197 of 264 single-member hubs connected)
        if st and not (yr and yr.isdigit() and int(yr) >= 2023): st = 2             # the enum value of 'connected' is 2 in Revit 2020-2022 (gt: 2/0) and 1 in 2023 (gt: 1/0)
        _setp(o_['params'], 'Connection Status', 'Integer', st)
        for c_ in F.S_(f, 'm_cellList', 'm_cells') or []:
            pt = F.S_(c_, 'm_pointId') if isinstance(c_, dict) else None
            if pt is not None and int(pt) in out: _setp(out[int(pt)]['params'], 'Connection Status', 'Integer', st)

def _wire_params(out, recs):
    """electrical wires: Revit's Hot/Neutral/Ground Conductors and Wire Size follow from the circuits the wire carries (m_pDesignPropManager.m_setidCircuits):
    hot = sum of the circuits' hot conductors, grouped by size (largest first); neutral / ground = the largest count and size among the circuits; plus the wire's stored adjustments"""
    for e_, o_ in out.items():
        if o_['class'] != 'RbsWireCurve': continue
        dp = F.S_(recs[e_]['fields'], 'm_pDesignPropManager') or {}
        cs = [int(c_) for c_ in (dp.get('m_setidCircuits') or []) if int(c_) in out]
        p_ = o_['params']
        et = recs[e_]['fields'].get('m_eType')
        if isinstance(et, int): p_['Type|Integer|-1140097'] = et                 # wiring type (arc / chamfer); 'Type' alone is the ElementId type
        if cs:
            cp = [out[c_]['params'] for c_ in cs]
            pn = [q.get('Panel') for q in cp]
            if isinstance(pn[0], str): p_['Panel'] = pn[0]                       # Revit shows the first circuit's panel (circuit numbers of all circuits)
            nums = [q.get('Circuit Number') for q in cp]
            if nums and all(isinstance(v, str) for v in nums):
                u = sorted(set(nums), key=lambda v: (0, int(v)) if v.isdigit() else (1, v))
                p_['Circuits'] = ','.join(u)                                     # distinct circuit numbers, numeric order
            if all(isinstance(q.get('Load Name'), str) for q in cp): p_['Circuit Load Name'] = ','.join(q['Load Name'] for q in cp)      # circuit order (m_setidCircuits)
            ds = []
            for q in cp:
                v_, np_, r_ = q.get('Voltage'), q.get('Number of Poles'), q.get('Rating')
                if not all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in (v_, np_, r_)): ds = None; break
                ds.append('%gV-%dP/%gA' % (round(v_ / 10.763910416709722, 6), int(np_), round(r_, 6)))      # voltage stored in kg ft2 / (s3 A): 1 V = 10.7639 internal
            if ds: p_['Circuit Description'] = ','.join(ds)
        parts = []
        for c_ in cs:
            ws = out[c_]['params'].get('Wire Size')
            if not isinstance(ws, str) or not ws: parts = None; break
            q = [re.match(r'\s*(\d+)-(.+)', t) for t in ws.split(',')]
            if len(q) != 3 or not all(q): parts = None; break
            parts.append([(int(m.group(1)), m.group(2).strip()) for m in q])
        if not parts: continue
        hot = collections.Counter()
        for pp in parts: hot[pp[0][1]] += pp[0][0]
        nh = sum(hot.values()) + _sid(dp.get('m_nHotAdjustment') or 0)
        neu = max((pp[1] for pp in parts), key=lambda a: (_wsize_key(a[1]), a[0])); gnd = max((pp[2] for pp in parts), key=lambda a: (_wsize_key(a[1]), a[0]))
        nn = max(pp[1][0] for pp in parts) + _sid(dp.get('m_nNeutralAdjustment') or 0); ng = max(pp[2][0] for pp in parts) + _sid(dp.get('m_nGroundAdjustment') or 0)
        p_['Hot Conductors'] = nh; p_['Neutral Conductors'] = nn; p_['Ground Conductors'] = ng
        p_['Wire Size'] = ', '.join(['%d-%s' % (n_, z_) for z_, n_ in sorted(hot.items())] + ['%d-%s' % (nn, neu[1]), '%d-%s' % (ng, gnd[1])])

_HOSTID_SELF = {'SWall', 'ArcWall', 'JoistSystem', 'ProfileRoof', 'FootPrintRoof', 'ExtrusionRoof', 'TrussElement', 'Ceiling'}     # Revit's Host Id = the host for these host classes, -1 otherwise (train split counts)
def _host_params(out, recs):
    """FamilyInstance 'Host' (String) and 'Host Id' (ElementId), derived from m_hostId:
    no host -> 'Level : <level name>'; SketchPlane host -> the element whose face the plane references ('<not associated>' for a free plane);
    other hosts -> '<Family Name> : <Type Name>' of the host's type. Host Id = the host for wall/roof/ceiling/joist/truss hosts, else -1."""
    def nm(x): return (out.get(x) or {}).get('params', {}).get('Name') or (recs.get(x) or {}).get('fields', {}).get('m_name')
    def famtype(x):
        o = out.get(x)
        if not o: return None
        t = o['params'].get('Type Id'); tp = (out.get(int(t)) or {}).get('params', {}) if isinstance(t, int) else {}
        fn, tn = tp.get('Family Name'), tp.get('Type Name')
        return '%s : %s' % (fn, tn) if fn and tn else None
    def lvname(f):
        lv = f.get('m_assocLevelId'); return nm(int(lv)) if lv is not None and int(lv) not in _INVALID else None
    def refname(ref):
        rc = out[ref]['class'] if ref in out else None
        if rc == 'Level': return 'Level : ' + (nm(ref) or '')
        if rc in ('Grid', 'GridLine'): return 'Grid : ' + (nm(ref) or '')
        if rc == 'ReferencePlane': return 'Reference Plane : ' + (nm(ref) or '')
        return famtype(ref)
    # Work Plane (String): the sketch plane's datum (level / grid / reference plane) or referenced face's element, else the host's work plane
    # (beams of a beam system), else the element's level, else '<not associated>'
    def spname(sp):
        if sp not in out or out[sp]['class'] != 'SketchPlane': return None
        pr = F.S_(recs[sp]['fields'], 'm_oPlaneRef') or {}
        for k in ('m_datumPlaneId',):
            v = pr.get(k)
            if v is not None and int(v) not in _INVALID and int(v) in out: return refname(int(v))
        ref = F.S_(pr, 'm_geomRef', 'm_elemId'); ref = int(ref) if ref is not None else None
        if ref not in _INVALID and ref in out: return refname(ref)
        return '<not associated>'
    def wplane(eid, depth=0):
        o = out[eid]; w = o['params'].get('Work Plane|String')
        if w: return w
        f = recs[eid]['fields']; sp = f.get('m_assocSketchPlaneId', f.get('m_sketchPlaneId')); sp = int(sp) if sp is not None else None
        if sp in _INVALID and f.get('m_sketchId') is not None and int(f['m_sketchId']) in recs:
            sp = recs[int(f['m_sketchId'])]['fields'].get('m_sketchPlaneId'); sp = int(sp) if sp is not None else None
        w = spname(sp) if sp not in _INVALID else None
        if w is None and depth < 2:
            h = f.get('m_hostId'); h = int(h) if h is not None else None
            if h not in _INVALID and h in out and out[h]['class'] in ('FamilyInstance', 'JoistSystem', 'CurveElem'): w = wplane(h, depth + 1)
        if w is None:
            ln = lvname(f); w = ('Level : ' + ln) if ln else '<not associated>'
        o['params']['Work Plane|String'] = w
        return w
    for eid, o in out.items():
        if o['class'] in ('FamilyInstance', 'JoistSystem', 'CurveElem'): wplane(eid)
    for eid, o in out.items():
        if o['class'] != 'FamilyInstance': continue
        f = recs[eid]['fields']; h = F.S_(f, 'm_hostId'); h = int(h) if h is not None else None
        d = o['params']; hc = out[h]['class'] if h in out else None
        if h in _INVALID or hc is None:
            lv = f.get('m_assocLevelId'); ln = nm(int(lv)) if lv is not None and int(lv) not in _INVALID else None
            d['Host Id|ElementId'] = -1
            d['Host|String'] = ('Level : ' + ln) if ln else (None if os.environ.get('RVT_HOSTNONE_OFF') else 'None')      # no host and no associated level: Revit prints 'None' (392 Snowdon Electrical, 43 Site, 77 rst_advanced values)
            if d['Host|String'] is None: del d['Host|String']
            continue
        d['Host Id|ElementId'] = h if hc in _HOSTID_SELF else -1
        if hc == 'SketchPlane':
            ref = F.S_(recs[h]['fields'], 'm_oPlaneRef', 'm_geomRef', 'm_elemId'); ref = int(ref) if ref is not None else None
            if ref in _INVALID: d['Host|String'] = '<not associated>'
            else:
                v = famtype(ref)
                if v: d['Host|String'] = v
        elif hc == 'Level':
            ln = nm(h)
            if ln: d['Host|String'] = 'Level : ' + ln
        elif hc == 'SiteSurface':                                       # a subregion is a SiteSurface hosted by the toposurface
            sh = recs[h]['fields'].get('m_hostId'); d['Host|String'] = 'Subregion' if sh is not None and int(sh) not in _INVALID else 'Surface'
        elif hc == 'BoundaryConditions': d['Host|String'] = 'Boundary Conditions'
        elif hc == 'BuildingPad':
            t = out[h]['params'].get('Type Id', recs[h]['fields'].get('m_buildingPadTypeId'))
            tn = ((out.get(int(t)) or {}).get('params', {}).get('Type Name') or nm(int(t))) if t is not None and int(t) not in _INVALID else None
            if tn: d['Host|String'] = 'Pad : ' + tn
        else:
            v = famtype(h)
            if v: d['Host|String'] = v

if __name__ == '__main__':
    p = params(sys.argv[1])
    if '--json' in sys.argv: json.dump({str(k): v for k, v in p.items()}, open(sys.argv[sys.argv.index('--json') + 1], 'w'), default=str)
    print(len(p), 'elements;', sum(len(v['params']) for v in p.values()), 'parameter values')
