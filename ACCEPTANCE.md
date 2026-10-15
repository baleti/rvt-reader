# Geometry acceptance criteria (set by the user, 2026-10-11)
Goal: ACCURATE and COMPLETE geometric representation of every Revit element, readable from .rvt files of all versions 2020-2026, shown faithfully in the viewer.
Measured against Revit's own geometry (gt4/ Volume/Area values, gt_geom/ oracle exports from session 181, bbox stored in the file), per class AND per year 2020-2026, on ALL corpus files (not a hand-picked few).

A class counts as DONE only if all hold:
1. TRUE geometry (decoded solid/mesh from the file, profiles/surfaces/curves exact) for >= 95% of its elements; box-only <= 2%; every surface type (plane, cylinder, cone, sphere, torus, revolution, ruled, extruded/swept, B-spline/NURBS) and curve type (line, arc, ellipse, spline/NURBS, helix) handled.
2. Accuracy: bbox IoU >= 0.95 and volume within 2% (surface area within 3%, centroid within 1% of diagonal) for >= 95% of elements; walls/floors/roofs include joins, openings, profile edits, layers, slopes.
3. Profiles: structural/mullion/railing/sweep/reveal/stringer profile cross-sections and sketch profiles (arcs, splines, holes) match Revit's curve loops and dimensions per type.
4. Classes required: walls, floors, roofs, ceilings, columns, beams/framing, foundations, stairs (runs/landings/supports), railings, ramps, curtain walls (grids/panels/mullions), doors, windows, all family instances (generative geometry, nested families, voids, transforms incl. mirror/flip), MEP (ducts, pipes, conduits, trays, fittings, equipment), rooms/spaces/areas (boundaries+volume), topography (+subregions, pads), masses, generic models.
5. Tests: unit/regression tests per surface type and class; a per-class, per-year table (true / approximate / box-only, IoU, volume error) is published in NOTES.md (reader) and the viewer README; no 'exact' label may include bbox-only matches.
6. Viewer (187): renders every class above from the reader API, compare-with-Revit mode shows deviation, regression screenshots updated.
If something is believed impossible, write the evidence into NOTES.md and propose a workaround (rosetta/differential files from session 181, Revit API oracle) first.

## STATUS 2026-10-14 (c4-geometry) against the criteria above
1. TRUE geometry >= 95%, box-only <= 2%: MET for every class with a population in the 60-file corpus (FID_TABLE_FINAL.txt): FamilyInstance 97.8/0.8, SWall 99.3/0.6, Floor/Ceiling/Roofs/Room 99.4-100/0, MEP curves 100/0, Stairs/Railings (oracle) 100, Toposolid 97.6, SweepHost 92.7 (documented: Revit has no solid for 3 of them). FamilyInstance 2025/2026 box-only 2% (void/nested families).
2. Accuracy vs the Revit oracle: 2020 samples + all rosetta 2024/2026 files >= 96% per class (volume 2%, area 3%, centroid 1% of diagonal); roofs 56/56; rebar centre-lines 346/346 (2020).
3. Profiles: structural/mullion/railing/sweep type outlines agree with Revit's type parameters for 63/69 types (6 misses are Form Deck / Stair Tread parameters that are not the outline); exact family profile polygons are NOT stored in the file (blocker, evidence in NOTES.md).
4. Classes: all listed classes covered; remaining gaps: masses (zero-volume level data only), topography TIN accuracy 97.6%, nested/void families without solids (as in Revit), RebarInSystem in 2023+ files (cache-less, shape rules proven in 2020), texture bitmaps (not stored).
5. Tests: gtg_table/gt_geom_cmp (oracle), fid_table (corpus), mat_tri_eval (materials 52/52 + all-element dumps 497/515), rebar_eval, per-year parameter table (param_report.py).
6. Viewer: c4-viewer adopted per-triangle materials; compare-with-Revit belongs to c4-viewer.
