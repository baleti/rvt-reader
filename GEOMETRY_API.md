# rvt_geometry API (for the viewer, session 187)

`import sys; sys.path.insert(0, '/home/user1/rvt-research'); import rvt_geometry as GG`
(needs the venv `~/rvt-env` for numpy/olefile; OCC checks use `~/occ-env`.  First call on a file decodes it and caches in `xcache/` (minutes for large files); later calls load the pickle.)

    GG.element_geometry(file, element_id) -> dict
    GG.file_geometry_index(file)          -> {element_id: record class}

Units: Revit internal feet, radians. All coordinates are in the Revit internal (project) frame, not shared coordinates.

## Result
```
{ 'element_id': int, 'class': str, 'confidence': 'exact'|'approx'|'exact_geometry_approx_section'|'box'|'none',
  'transform': 4x4 row-major local->world (identity for solids already in world coordinates; instance transform for 'box'),
  'bbox': [[x,y,z],[x,y,z]] or None,
  'flags': [str]   # e.g. 'no_joins','no_openings','no_openings_or_slope','curved','has_arcs','symbol_outline_only','family_solids_not_decoded','class_not_supported'
  'solids': [ solid ] , 'notes': str }
```
Solid kinds
* `extrusion` (floors, ceilings): `profile.loops` = list of closed loops (first = outer; later ones holes if present), each a list of segments
  `{'type':'line','p0','p1'}` or `{'type':'arc','p0','p1','mid'}`; `profile.plane` (origin, xvec, yvec, normal); `direction`, `depth`; `layers` = compound-structure layers `[{width, material_id, function}]` (top to bottom as stored); `voids` = [] (openings not decoded).
* `wall_extrusion`: `location_curve` (line or arc segment, centre line), `thickness` (sum of layers), `height`, `base_z`, `layers`, `location_line`:'centre'. Joins, openings, profile edits NOT applied (see flags).
* `sweep` (ducts, pipes, conduits, cable trays): `path` (line/arc segment), `section` {'shape':'round','diameter'} or {'shape':'rect','width','height'}; fittings/cuts not applied.
* `box` (family instances): `min`,`max` = the family symbol's stored outline in family-local coordinates, with `transform` = the instance transform. Family solids are NOT decoded (flag `family_solids_not_decoded`).

## Status per class
see NOTES.md "GEOMETRY STATUS" for the measured table; everything not listed there returns confidence 'none' (use the element header bbox if you need something).

## Update: triangle meshes from saved graphics
`confidence: 'mesh_approx'` results carry one solid `{'kind':'triangle_mesh','triangles':[[p0,p1,p2],...],'source': 'own_geometry_in_bbox'|'symbol_instance'|'all_geometry'}` in world coordinates (feet).
Source = the geometry Revit last drew for the element (partition channel 103). Planar and cylindrical faces are tessellated from their stored edge loops; ruled/revolved/other surfaces are skipped (flag `unsupported_faces`).
Measured fidelity per class: NOTES.md section 'GEOMETRY STATUS'. For classes with an analytic builder (Floor, Ceiling, SWall, MEP curves) the analytic solid is returned; everything else falls back to the mesh, and finally to the symbol bbox ('box').

## Update 2026-10-11 (later): what the mesh path covers now
Surface types evaluated exactly (formulas fitted against Revit's own edge points, 0.0 error): Plane, CylSurf (P = C + R cos u X + R sin u Y + v Z), ConeSurf (apex at m_center, P = C + v sin a (cos u X + sin u Y) + v cos a Z), RuledSurf ((1-v) C1(t) + v C2(t), t = t0 + (t1-t0) u), SurfRev (profile in local coords rotated about the local z by u; profile parameter = v), HermiteSurf (bicubic Hermite patches: corner/node values verified, interior pending), GPolyMesh (stored triangle meshes: topography, some curtain parts).
Curves (rvt_curves.py): line, arc, ellipse, Hermite spline, NURBS (basis evaluation), cylindrical helix, offset curve. Not yet evaluated: OffsetSurf, SharedSurface, TempImportNurbsSurf (none occur in the 10 indexed corpus files).
Volume of curved shells is computed by refined_volume (coarse closed mesh gives the orientation, curved triangles are subdivided in (u,v)); `closed_shell` flag = the element's own faces were isolated from the solid + reference-face Geometry nodes and form a manifold shell (walls: volume equals Revit's to 1e-4 in the 8/8 test walls).
Every mesh result carries `profile` (end-cap cross-section loops in the cap plane, prismatic elements) when one exists.

## element_brep(file, element_id) -> {'faces': [...], 'instances': [...]}   (for the viewer's occsurf.py)
Each face: `{'geometry': node index, 'handle', 'surface': {...}, 'loops_uv': [[[u,v],...],...], 'orient': m_orientFlag, 'render_style': m_renderStyleId}`.
Surface dict types (all coordinates document feet; the instance transform is NOT applied - see `instances`):
`plane {origin,xdir,ydir}` | `cylinder {origin,xdir,ydir,zdir,radius}` (u angle from xdir, v along zdir) | `cone {origin,xdir,ydir,zdir,ref_radius=0,semi_angle}` (apex at origin; v = slant distance from the apex; OCC Geom_ConicalSurface with ref_radius 0)
| `revolution {profile:<curve>,axis_origin,axis_dir,xdir,ydir}` (u angle about the axis from xdir; v = profile curve parameter; profile given in world coordinates at u = 0) | `ruled {curve1,curve2}` (u along the curves, v 0..1 between them)
| `hermite {uparams,vparams,nodes:[{p,tu,tv,twist}] u-fastest}` (bicubic Hermite). `<curve>` = `line {p0,p1}` | `arc {p0,mid,p1}` | `bspline {degree:1,poles}` (sampled ellipse/spline/NURBS/helix, flagged in `note`).
`instances` lists the GInstance nodes of the record: `{symbol_id, transform: {m_3x3, m_or}}` (world = m_3x3-variant @ local + m_or; element_mesh picks the variant whose bbox fits the element bbox).
Per-shell closed/volume/area: use `element_geometry(...)['solids'][0]` flags (`closed_shell`) or rvt_mesh.mesh_volume on the triangles.

## Update 2026-10-12: what changed in the mesh path (rosetta + stairs/railings/revolutions)
Validated against the Revit oracle gt_geom (rosetta base+var files, 2024): FamilyInstance, Wall, Mullion, Floor, Panel, Railing, TopRail, Room, WallSweep, Stairs, StairsRun, Element: 100% of elements with volume <=2%, area <=3%, centroid <=1% diag (`gtg_table.py gtg_ros/*.jsonl`). Topography: vertex set == Revit TOPO points, same TIN area (`gtg_topo.py`).
* Faces with no edges (full sphere/torus halves; loop envelope = uv rectangle) are tessellated from their uv rectangle (cone/cylinder generators stay single segments so seams weld). Sphere, torus, cone, revolution, sketch-spline profile extrusions now close and measure within 1% of Revit.
* Plane/cylinder/cone/revolution joins: boundary samples are snapped onto the exact intersection curve (the same points are used on both sides of the edge).
* Volume: `mesh_volume`/`refined_volume` trust windings that are already consistent (directed edges cancel), ignore non-manifold edges when propagating orientation, orient per FACE when `fid` is given (element_mesh now returns `fid`, one id per face), detect watertightness across T-junctions, and treat pole triangles (cone apex, sphere pole) flat. Single planar reference faces (wall layer interfaces) are dropped from a node's volume.
* `element_mesh` keeps symbol instances next to an element's own faces (stair railing rods + balusters) and skips instances that are drawn through their own element (instance with a non-zero `m_forbiddenTarget.m_targets`, e.g. a railing's top rail).
* Stairs: a stair run is its own saved-graphics solid (sawtooth of tread/riser faces, supports are separate elements): volume/area/centroid exact.

## Update 2026-10-12 (evening): validated against the Revit oracle on 1,373 elements
2020 sample projects (3 files) every class >= 96% (volume/area/centroid per ACCEPTANCE: 2% / 3% / 1% diag): FamilyInstance 98.9%, Wall 100%, Mullion/Panel 100%, Floor/Ceiling 100%, Stairs/StairsRun/Railing 100%, WallSweep 100%, Room 96%, analytical surfaces/filled regions/mass level data (zero-volume sheets) 100%. Rosetta (2024 single features) 100% for all classes; topography exact. Details + remaining deviations: NOTES.md "GEOMETRY vs Revit's own geometry".
API notes for the viewer: `element_mesh` result now carries `fid` (face id per triangle) and `nid` (body id per triangle); bodies are measured independently, `source` in {own_geometry_in_bbox, symbol_instance, all_geometry}, flags `closed_shell`, `per_node`, `plus_instances`. `element_curves(doc, id)` returns profile-family outlines (bounding lines only, see NOTES). Instance transform: world = m_3x3 @ local + m_or.


## Per-class/per-year table (partial, 2026-10-12): see NOTES.md "Per-class / per-year geometry table". Headline for the viewer: FamilyInstance 86% accurate / 11% approximate / 3% box-only over 17.8k placed instances (2020: 74/11/1 before the final fixes), SWall 82%, Ceiling 99.7%, Floor 98.7%, ProfileRoof 100%, MEP curves (duct/pipe/conduit/flex) 100%, mullions 99.7%, panels 96.7%, Stairs 100%, Toposolid/SiteSurface 86-95%. Open: curve elements (reference/model lines), BaseRailing 35%/48% approx (old-run rows), analytical wall/slab/panel surfaces.

## Materials / appearance / textures (rvt_materials.py, 2026-10-12; own analysis)
* `material_table(file) -> {material_id: {id, name, class, category, color:[r,g,b], transparency 0..1, smoothness, shininess, glow, use_render_appearance, cut_pattern{id,color,background_id,background_color}, surface_pattern{...}, appearance_asset_id, appearance{...}, structural_asset_id, keywords, texture{path,scale,offset,angle,uv_scale,invert,blur,rgb_multiplier}|None}}`
* `appearance_table(file) -> {asset_id: {id, name, schema (GenericSchema/WallPaintSchema/PlasticVinylSchema/MetalSchema/HardwoodSchema/ConcreteSchema/MasonryCMUSchema/Glazing..., library, color, transparency, diffuse [r,g,b], reflectivity_0deg/90deg, glossiness, metal, glazing_transparency, refraction_index, self_illumination, bump_amount, tint, cutout_opacity, properties{all AssetProperty name->value}, textures{property name -> {path (asset-library relative, e.g. '1/Mats/Sitework.Planting.Grass.Thick.bump.png'), scale, offset, angle, ...}}}}`
* `material_for_face(file, element_id, face_handle)`: face render style (a MaterialElem id) else the material of the Geometry node's graphics style (GStyleElem.m_materialElemId); `None` when unassigned. Face handles are those of `element_brep(...)['faces']` (symbol faces: pass the symbol id).
* `embedded_images(file)` / `embedded_image_bytes(file, entry)`: PNG blobs stored in the partitions (material swatch thumbnails 128x128/64x64 and image symbols, ~170 per sample project). Texture bitmaps themselves are NOT stored in the .rvt: only their asset-library relative paths (Revit keeps them in the Autodesk material library); the viewer should resolve `path` against its own library copy and fall back to the diffuse colour.
* Measured in 2020 Residential: 139 materials, 139 appearance assets, 55 with textures; schemas as listed above. Validation against Revit's API is requested in NEEDS-FROM-ORACLE.md (not yet answered).


## Update 2026-10-12 14:20 (geometry + materials validated)
Geometry vs Revit (gt_geom oracle): 2020 samples FamilyInstance 100% volume / 99.2% all (628 instances), Wall/Mullion/Panel/Floor/Ceiling/Railing/Stairs/WallSweep 100%, Room 96%; all 2024+2026 rosetta files 100% (638 FamilyInstances, 342 walls, 82 floors). Materials vs Revit (gt_mat oracle): Material elements 530/530 exact on all fields, appearance-asset properties 38,417/38,417, face material sets 49/52 identical + 3 supersets + 0 wrong. API additions: element_mesh `fid`/`nid`; element_brep(doc, id, depth, detail) resolves instances; element_curves; curtain_grid(file, id) -> {u, v, panels, mullions} ids (6/6 exact vs Revit); rvt_materials.{material_table, appearance_table, material_for_face, embedded_images}. Important for consumers: Revit's Volume follows FINE detail for loadable families, so request detail=3 meshes.

## Update 2026-10-12 (c4-geometry): per-triangle materials + parameters
* `rvt_elemmesh.element_mesh(doc, id)` returns `mat`: one material id per triangle (same length as `tris`, -1 unassigned, negative built-in ids such as -4000011 for rooms kept as Revit reports them). Resolution: face m_renderStyleId (MaterialElem, or a GStyleElem's material) -> the Geometry node's graphics-style material; symbol-instance triangles carry the symbol's face materials. Validated against Revit's Face.MaterialElementId (gt_mat): 52/52 sampled elements and 2020 Residential all-element dump 172/189 before the room fix (rooms were the 17 misses; fixed). Paint is stored as the face's own render style (painted faces resolve to the paint material).
* `rvt_params.params(file, geom=False)`: stored parameter sets are read by id (fixes shifted Name/Number on rooms); `stored_params(fields)`, `symbol_params(file, symbol_id)` (type values incl. Type Mark, follows m_masterId of derived symbols); geom=True adds Volume/Area of family instances from the solids (Revit computes them at MEDIUM detail in files of Revit 2020-2025 and FINE in 2026; family Area = half the solid's surface area; curtain panel Width/Height/Area from the panel's derived symbol, wall-type panels Volume 0).

## Final per-class/per-year table (2026-10-15): see NOTES.md "FINAL per-class / per-year geometry table, refreshed 2026-10-15" (FID_TABLE_FINAL.txt). Headline for the viewer: FamilyInstance 99.5% accurate / 0.3% true-off / 0.1% box-only over 14435 placed instances, SWall 99.3%, Ceiling 100.0%, Floor 100.0%, RoomElem 99.4%, ProfileRoof 100.0%, SiteSurface 100.0%, Toposolid 97.6%.

## Parameters (rvt_params.params / symbol_params), state 2026-10-16 (c5-geometry)
Overall 94.5% of 8.98M corpus parameter values reproduced exactly (86.5% before the 2026-10-15/16 work; per year 2020 95.2, 2021 95.7, 2022 95.7, 2023 95.5, 2024 93.2, 2025 93.2, 2026 92.1; final table in NOTES.md). Derived (exact unless noted): layered-type thermal values (R, U, thermal mass), absorptance/roughness, wall Width = layer sum; Material Type; OmniClass Title; construction-type names; FamilySymbol built-ins (thermal/optical, Rough Width/Height, Width/Height by id and name in symbol_params); beam/brace Length and Start/End Level Offset; window/door Head Height; Elevation from Level (also via the schedule-only level); MEP: Section and System Name from the system's section lists, pipe System Name/Classification, centre-line inheritance; Room Area (exact) and Perimeter (outer boundary); Rebar Bar Length/Quantity/Layout Rule/Spacing; RebarInSystem via rvt_rebar (Total Bar Length approximate); FamilyInstance Volume/Area from the decoded solids with the Revit node rules (electrical/lighting categories: nodes with controlCommand bit 26 and no bit 15 ignored).
Deliberately ABSENT (better missing than wrong): duct fitting Area, room Volume (Revit gives 0 when volume computation is off, setting not decoded), curtain-panel Area when the cell size is not stored (Revit = cell minus mullion offsets), Fixture Units, duct Pressure Drop / Loss Coefficient, Flow of centre lines (MEP engine values).
Known approximate: Rebar Total Bar Length / Reinforcement Volume (about 0.03% off), pipe fitting Volume on 'Standard' small fittings (119 of 535 low).
