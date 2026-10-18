"""Per-view graphic display options decoded from DBView*.m_pViewDisplayMgr (model display, shadows, lights).
view_display(file) -> {view_eid: {'class', 'name', 'surfaces' (raw m_model.m_surfaces), 'style', 'edges', 'silhouettes', 'silhouette_style_id', 'transparency', 'smooth_edges', 'hidden_lines', 'cast_shadows', 'ambient_shadows',
 'shadow_intensity', 'sun_settings_id'}}.
'surfaces' values verified against the Revit API camera dump (review-compare cameras.tsv, 2024 Snowdon Structural, 26 HLR / 12 FlatColors views): 2 = Hidden Line, 7 = Consistent Colors (FlatColors) separate every view exactly;
1 = Wireframe (single sample, name from the Revit enum order, not verified); 3..6 = shaded family (2020 Commercial: the three 3D views / five sections that are not HLR all hold 4) (Shaded / Shaded with edges / Realistic / Raytrace, not separated yet: no oracle views)."""
import rvt_materials as RM

STYLE = {1: 'Wireframe', 2: 'HLR', 7: 'FlatColors'}

def _cref(v):
    try: v = int(v); return (v & 255, (v >> 8) & 255, (v >> 16) & 255)         # Windows COLORREF 0x00BBGGRR
    except Exception: return None

def view_display(file):
    out = {}
    for e, r in RM._ctx(file).recs.items():
        if not r['class'].startswith('DBView'): continue
        mgr = RM._ob((r['fields'] or {}).get('m_pViewDisplayMgr') or {})
        if not isinstance(mgr, dict) or 'm_model' not in mgr: continue
        m = mgr['m_model']; sh = mgr.get('m_shadows') or {}; li = mgr.get('m_lights') or {}; s = m.get('m_surfaces')
        bg = mgr.get('m_background') or {}
        out[e] = {'class': r['class'], 'name': RM._ob((r['fields'].get('m_name') if isinstance(r['fields'].get('m_name'), dict) else {'obj': r['fields'].get('m_name')})) if False else None,
                  'surfaces': s, 'style': STYLE.get(s, 'Shaded?' if s in (3, 4, 5, 6) else None), 'edges': m.get('m_edges'), 'silhouettes': m.get('m_enableSilhouettes'), 'silhouette_style_id': RM._eid(m.get('m_silhouetteEdgesGStyleId')),
                  'transparency': m.get('m_transparency'), 'smooth_edges': m.get('m_smoothEdges'), 'hidden_lines': m.get('m_showHiddenLinesVal'), 'cast_shadows': sh.get('m_castShadows'), 'ambient_shadows': sh.get('m_ambientShadows'),
                  'shadow_intensity': li.get('m_shadowIntensity'), 'sun_settings_id': RM._eid(li.get('m_sunAndShadowSettingsId')), 'lighting': mgr.get('m_lighting'), 'ambient_light': li.get('m_ambientLightIntensity'), 'sunlight': li.get('m_sunlightIntensity'),
                  'background_type': bg.get('m_type'), 'sky_color': _cref(bg.get('m_skyColor')), 'ground_color': _cref(bg.get('m_groundColor'))}
    return out

# background: m_background.m_type 256 / 257 / 512 (257 = sky + ground gradient with the colours below on 2020 Commercial 206158, 512 = image background (m_oStaticRRTRenderSettings.m_BkIamgeSettings)); meaning of 256 vs 257 not separated (no oracle).

def view_clip(file):
    """Section / elevation / callout depth and crop state, from the Viewer (marker) record's m_boundedSpace and the DBViewSection's m_backClipping.
    view_clip(file) -> {view eid: {'viewer', 'far_clip_offset' (ft, m_boundOffset[2][0]), 'far_clip_active' (m_boundActive[2][0]), 'far_clipping' (0 no clip, 1 clip without line, 2 clip with line),
    'crop_active' (any x / y bound active), 'bound_offset' ([[x lo, x hi], [y lo, y hi], [z near, z far]] in the view frame), 'bound_active', 'origin', 'basis', 'annotation_crop_active'}}
    far_clipping = DBViewSection.m_backClipping when valid; the 0xFFFFFFFF 'inherit' value means 2 if the far clip is active or the view has no marker, else 0.
    Verified against Revit's parameter dump (Snowdon Structural 2024, 15 section / elevation views): Far Clip Offset 10 of 10 exact, Far Clipping all, Crop View all."""
    import rvt_params as RP
    try: year = int(RP._file_year(file))
    except Exception: year = 2024
    ctx = RM._ctx(file); viewers = {}
    for e, r in ctx.recs.items():
        f = r['fields'] or {}
        bs = f.get('m_boundedSpace')
        if isinstance(bs, dict) and f.get('m_dbViewId') not in (None, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF) and 'm_boundOffset' in bs:
            viewers[int(f['m_dbViewId'])] = (e, f, bs)
    out = {}
    for e, r in ctx.recs.items():
        if not r['class'].startswith('DBView'): continue
        vw = viewers.get(e); bc = (r['fields'] or {}).get('m_backClipping')
        d = {'viewer': None, 'far_clip_offset': None, 'far_clip_active': None, 'crop_active': None, 'bound_offset': None, 'bound_active': None, 'origin': None, 'basis': None, 'annotation_crop_active': None}
        if vw:
            ve, vf, bs = vw; ba = bs.get('m_boundActive') or []; bo = bs.get('m_boundOffset') or []
            d.update(viewer=ve, bound_offset=bo, bound_active=ba, origin=bs.get('m_orig'), basis=bs.get('m_basis'), annotation_crop_active=vf.get('m_bAnnotationCropActive'))
            try:
                d['far_clip_offset'] = bo[2][0]; d['far_clip_active'] = ba[2][0]; d['crop_active'] = int(any(ba[i][j] for i in (0, 1) for j in (0, 1)))
            except Exception: pass
        if isinstance(bc, int) and bc in (0, 1, 2): d['far_clipping'] = bc
        elif bc is not None: d['far_clipping'] = (2 if d['far_clip_active'] else 0) if vw else (2 if year >= 2024 else 0)          # no marker = a view TYPE record: Revit's default changed from 'no clip' (<= 2023) to 'clip with line' (2024+)
        else: d['far_clipping'] = None
        if d['far_clipping'] is not None or vw: out[e] = d
    return out
