# Full objectives (user, 2026-10-11). Geometry is the top priority, but EVERYTHING below is required; nothing is dropped. Geometry criteria: ACCEPTANCE.md.

## Reader (session 176)
1. Geometry: ACCEPTANCE.md (surfaces/curves, family generative geometry, stairs/railings/ramps/curtain walls/rooms/topography/masses, exact walls/floors/roofs, profiles).
2. Parameters: close the gap between ~68-71% and as close to 100% as possible: buckets (a) derivable by lookup/join, (b) geometry-derived (Area/Volume/Length/elevation, computed from the decoded geometry), (c) MEP engine values, (d) unknown; per-year 2020-2026 before/after table; every derivable parameter reproduced exactly.
3. Elements: the 186/119/119 bare Element objects, remaining not-exact elements, all classes complete per year.
4. Speed: 40 MB file < ~10 s cold and < 1 s from cache: profile, parallel/lazy decode (done partly), then the Rust core in ~/src/rvt-core (PyO3, Python oracle, bit-identical on all corpus files) for record decoding.
7. Safety: memory caps on all jobs (systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0), monero VM on host1 must be running when you are not using the headroom.

## Writer / oracle (session 181)
1. Revit geometry oracle (gt_geom/, rosetta/ differential files incl. profiles, stairs, railings, topography, surfaces, family forms) for session 176.
2. Scene generator: populated realistic models with doors, windows, floors, roofs, rooms, families, MEP, parameters of every storage type, views/sheets, groups/worksets/phases; ladder of scenes in write-lab/scenes/ all passing the full protocol (offline invariants, fresh-process Revit open audit off/on, API+UI, SaveAs/reopen equal dump).
3. Campaign loop persistent; clean files in generated/clean/; regenerate and retest every earlier deliverable; wall/line visibility; 2026 walls.
4. VM safety: one overlay VM at a time, host2 MemAvailable > 6 GB, never touch revit-win/ci-20261010-222858, VMs stay offline.

## Viewer (session 187)
1. Render every class from the reader API with true geometry, profiles, surfaces (occsurf.py), stairs/railings/rooms/topography/curtain walls; walls/roofs/floors accuracy (joins, mitres, openings from real cut bodies, slopes); honest fidelity buckets (true geometry / parametric-unproven / box-only); compare-with-Revit mode.
2. Features: Revit-style navigation + ViewCube, section planes/box, measuring with snapping, parameter search, view/sheet browser, isolation by level/category/phase, shareable state, inspector with type parameters and profile dimensions, model picker, progress UI, caching/versioning, tests + smoke test.
3. Performance and hygiene: first-open speed, memory caps, no leaked processes (chromium), test windows only on workspace 178, no sample files committed/published.
