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
