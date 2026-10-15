"""Materials / appearance assets / textures read from the file (own analysis).
material_table(file)  -> {material_id: {...}}   (Material elements with their appearance asset resolved)
appearance_table(file)-> {asset_id: {...}}
material_for_face(file, element_id, fid)  -> material id of a face of an element (fid = face handle) or None
embedded_images(file) -> [{'offset','size','width','height','format'}] PNG blobs stored in the partitions (swatch thumbnails, image symbols)
Colours are [r,g,b] 0-255 (Revit stores BGR in an int); transparency 0..1; texture paths are asset-library names (Revit keeps texture files outside the .rvt)."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault('RVT_GEOM', '1')

def _ob(o): return o.get('obj', o) if isinstance(o, dict) else o
def _eid(v):
    try: v = int(v)
    except Exception: return None
    return None if v in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF) else v
def rgb(c):
    try: c = int(c)
    except Exception: return None
    if c in (0xFFFFFFFF,): return None
    return [c & 255, (c >> 8) & 255, (c >> 16) & 255]

def _prop(p):
    """AProperty -> (name, value) with connected assets (textures) resolved"""
    p = _ob(p); nm = p.get('m_sName'); v = p.get('m_value')
    conn = [_asset(c) for c in (p.get('m_aConnected') or [])]
    if conn: return nm, {'value': v, 'connected': conn}
    return nm, v

def _asset(a):
    a = _ob(a); props = {}
    for q in (a.get('m_aAProperties') or []):
        k, v = _prop(q); props[k] = v
    return {'schema': a.get('m_sName'), 'library': a.get('m_sLibrary'), 'type': a.get('m_eAssetType'), 'props': props}

def _texture(conn):
    """summary of a connected UnifiedBitmap asset: path, scale (real-world units), offset, angle"""
    for c in conn:
        p = c['props']
        path = p.get('unifiedbitmap_Bitmap')
        if isinstance(path, dict): path = path.get('value')
        if path is None and not any(k.startswith('texture_') for k in p): continue
        if isinstance(path, str): path = '|'.join(dict.fromkeys(x.replace('\\', '/') for x in path.split('|')))      # the library stores the same path once per channel (backslashes in newer files)
        return {'path': path or None, 'scale': [p.get('texture_RealWorldScaleX'), p.get('texture_RealWorldScaleY')], 'offset': [p.get('texture_RealWorldOffsetX'), p.get('texture_RealWorldOffsetY')],
                'angle': p.get('texture_WAngle'), 'uv_scale': [p.get('texture_UScale'), p.get('texture_VScale')], 'invert': p.get('unifiedbitmap_Invert'), 'blur': p.get('unifiedbitmap_Blur'), 'rgb_multiplier': p.get('unifiedbitmap_RGBAmount')}
    return None

def _ctx(file):
    import rvt_geometry as G
    return G.get_ctx(file)

def appearance_table(file):
    out = {}
    for eid, r in _ctx(file).recs.items():
        if r['class'] != 'AppearanceAssetElem': continue
        f = _ob(r['fields']); a = _ob(f.get('m_pAppearanceAsset') or {})
        asset = _asset(a.get('m_Asset') or {}); props = asset['props']; tex = {}; flat = {}
        for k, v in props.items():
            if isinstance(v, dict) and 'connected' in v:
                t = _texture(v['connected'])
                if t: tex[k] = t
                flat[k] = v['value']
            else: flat[k] = v
        diffuse = flat.get('generic_diffuse') if isinstance(flat.get('generic_diffuse'), list) else None
        out[eid] = {'raw': {k: v for k, v in props.items()}, 'id': eid, 'name': a.get('m_Name'), 'schema': flat.get('BaseSchema') or asset['schema'], 'library': asset['library'], 'color': rgb(a.get('m_color')), 'transparency': a.get('m_transparency'),
                    'diffuse': [round(x * 255) for x in diffuse[:3]] if diffuse else None, 'properties': flat, 'textures': tex,
                    'reflectivity_0deg': flat.get('generic_reflectivity_at_0deg'), 'reflectivity_90deg': flat.get('generic_reflectivity_at_90deg'), 'glossiness': flat.get('generic_glossiness'),
                    'metal': flat.get('generic_is_metal'), 'glazing_transparency': flat.get('generic_transparency'), 'refraction_index': flat.get('generic_refraction_index'),
                    'self_illumination': flat.get('generic_self_illum_luminance'), 'bump_amount': flat.get('generic_bump_amount'), 'tint': flat.get('common_Tint_color') if flat.get('common_Tint_toggle') else None,
                    'cutout_opacity': flat.get('generic_cutout_opacity')}
    return out

def material_table(file):
    app = appearance_table(file); out = {}
    for eid, r in _ctx(file).recs.items():
        if r['class'] != 'MaterialElem': continue
        m = _ob(_ob(r['fields']).get('m_pMaterial') or {}); aid = _eid(m.get('m_appearanceAssetId'))
        out[eid] = {'id': eid, 'name': m.get('m_name'), 'class': m.get('m_sMaterialClass'), 'category': m.get('m_sCategory'), 'color': rgb(m.get('m_color')), 'transparency': m.get('m_transparency'),
                    'smoothness': m.get('m_smoothness'), 'shininess': m.get('m_shininess'), 'glow': m.get('m_glow'), 'use_render_appearance': m.get('m_bUseRenderAppearance'),
                    'cut_pattern': {'id': _eid(m.get('m_cutPatternId')), 'color': rgb(m.get('m_cutPatternColor')), 'background_id': _eid(m.get('m_cutBackgroundPatternId')), 'background_color': rgb(m.get('m_cutBackgroundPatternColor'))},
                    'surface_pattern': {'id': _eid(m.get('m_surfacePatternId')), 'color': rgb(m.get('m_surfacePatternColor')), 'background_id': _eid(m.get('m_surfaceBackgroundPatternId')), 'background_color': rgb(m.get('m_surfaceBackgroundPatternColor'))},
                    'appearance_asset_id': aid, 'appearance': app.get(aid), 'structural_asset_id': _eid(m.get('m_structuralPropertySetId')), 'keywords': m.get('m_keywords') or None}
        out[eid]['texture'] = next(iter((app.get(aid) or {}).get('textures', {}).values()), None) if aid else None
    return out

def gstyle_material(file, style_id):
    """material attached to a graphics style (the Geometry node's GInfo.m_categoryId points at a GStyleElem)"""
    r = _ctx(file).rec(style_id)
    if r is None or r['class'] != 'GStyleElem': return None
    return _eid(_ob(_ob(r['fields']).get('m_pGStyle') or {}).get('m_materialElemId'))

def material_for_face(file, element_id, fid):
    """material id of a face (fid = face handle as in element_brep): the face's render style when it is a Material, else the material of the Geometry node's graphics style; None when unassigned"""
    import rvt_elemmesh as E
    d = E.Doc(file); rec = d.rec(int(element_id))
    if rec is None: return None
    geos, inst = E._geos_f(rec['fields'], 3)
    if not geos: geos, inst = E._geos(rec['fields'])
    ctx = _ctx(file)
    for g in geos:
        for fc in g['m_pFaces']:
            if fc.get('handle') != fid: continue
            f = _ob(fc); rs = _eid(f.get('m_renderStyleId'))
            if rs is not None:
                rr = ctx.rec(rs)
                if rr is not None and rr['class'] == 'MaterialElem': return rs
                m = gstyle_material(file, rs)
                if m is not None: return m
            cat = _eid((g.get('m_GInfo') or {}).get('m_categoryId'))
            if cat is not None: return gstyle_material(file, cat)
    return None

def embedded_images(file):
    import olefile, rvt2text as T
    o = olefile.OleFileIO(file); out = []
    for pn in ['/'.join(e) for e in o.listdir(streams=True) if e[0] == 'Partitions']:
        ch = T.joined(o.openstream(pn).read()); p = 0
        while True:
            i = ch.find(b'\x89PNG\r\n\x1a\n', p)
            if i < 0: break
            j = ch.find(b'IEND', i)
            if j < 0: break
            end = j + 8; w, h = struct.unpack('>II', ch[i + 16:i + 24]); out.append({'partition': pn, 'offset': i, 'size': end - i, 'width': w, 'height': h, 'format': 'png'}); p = end
    return out

def embedded_image_bytes(file, entry):
    import olefile, rvt2text as T
    o = olefile.OleFileIO(file); ch = T.joined(o.openstream(entry['partition']).read()); return ch[entry['offset']:entry['offset'] + entry['size']]

if __name__ == '__main__':
    import json
    mt = material_table(sys.argv[1]); print(len(mt), 'materials')
    for m in list(mt.values())[:3]: print(json.dumps(m, default=str)[:900])
