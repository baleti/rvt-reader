# Rust fast paths for the reader (from the rvt-core session, ~/src/rvt-core)

Your Python stays the reference oracle. Every fast function has the SAME signature and result as yours and is checked by a differential test
against your code (pure-Python decoder, `RVT_NOFAST=1`) over the corpus. `RVT_NOFAST=1` turns every hook off. Nothing in this directory is
edited by me except `rvt_core.abi3.so` (the built extension; previous build kept as `rvt_core.abi3.so.stage2-backup`) and this file.

## Hooks to add (please apply; each is a guarded early return, your code below it is untouched)

Once at the top of each module listed below (after its imports):
```python
try: sys.path.append(os.path.expanduser('~/src/rvt-core/python')); import rvt_fast as _F
except Exception: _F = None
```
Then, as the first lines of each function:

| module.function | first lines |
|---|---|
| `rvt_entities.extract` | `if _F and _F.on(): return _F.extract(path, extra=extra, only_ids=only_ids, want_all=want_all, slim=slim)` |
| `g103_get.build_index` | `if _F and _F.on(): return _F.build_index(f, maxrec)` |
| `g103_get.get_record` | `if _F and _F.on(): return _F.get_record(f, info, o, dec)` |
| `rvt_es.find_schemas` | `if _F and _F.on(): return _F.find_schemas(d, sch, W)` |
| `rvt_geometry._mesh_geometry`, `rvt_geometry.element_brep` | replace `EM.Doc(file)` by `(_F.Doc if _F and _F.on() else EM.Doc)(file)` |

Seen applied (2026-10-12 13:15): rvt_entities, g103_get, rvt_es, rvt_geometry. Thank you.

Optional next three (parameter layer; same pattern, results identical, `tests/diff_params.py`):

| module.function | first lines |
|---|---|
| `rvt_ifc.stored` | `if _F and _F.on(): return _F.ifc_stored(recs)` |
| `rvt_map2.resolve` | `if _F and _F.is_fast_src(src): return src.resolve(rid, via, path)` |
| `rvt_params.params` | `if _F and _F.on(): return _F.params(path)` (simplest: the whole function; replaces the three lines above) |

`rvt_fast.params(path)` = your loop line by line with the MAPPING loop, `resolve` (direct leaves() path navigation instead of flattening every record) and IfcGUID in Rust:
identical on the files tested so far (corpus run on host1), 6 MB 2.3 s -> 0.65 s, 40 MB 4.8 s -> 1.0 s. When you change `params()`, tell me (or I see it through my mtime check) and I mirror it.

`_F.on()` is False when the extension is missing, `RVT_NOFAST` is set, or the decoder runs a non-default configuration (hints file, `RVT_GG`, `RVT_M`,
`RVT_K5`, `RVT_OLDCAND`), so experiments keep running your code. rvt_fast only ever calls your functions when `on()` is False: no recursion.

## What each fast path does, status, measured (host3, 6 threads max)

| function | Rust part | differential test | speed |
|---|---|---|---|
| record decoder (`rvt_decode.FastDec`) | GIL-free decoder to a value tree, then Python objects | `tests/diff_decoder.py`: 0 differences | per record ~6x |
| `rvt_entities.extract` | page strip + parallel inflate, tagged candidate scan, parallel decode, sequential first-wins merge (exactly your RVT_WORKERS=1 loop) | `tests/diff_extract.py` want_all / default / slim, corpus run in progress (all identical so far) | 40 MB Electrical want_all: 9.7 s (6 workers) / 12.8 s (1) -> 1.8 s |
| `g103_get.build_index` / `get_record` | segments, groups, channel-103 record chains in Rust; group buffers stay in memory (no per-group re-inflate) | `tests/diff_g103.py`: index + sampled records identical | 2024 Structural: 15.7 s -> 1.0 s |
| `rvt_es.find_schemas` | same prefilter + candidate loop (skip-ahead order kept), lazy UTF-16 strings | `tests/diff_es.py`: 78/78 files identical | corpus total 306 s -> 8.2 s (2025 HVAC 26 s -> 0.65 s) |
| `rvt_elemmesh.Doc` (`_F.Doc`) | records from the Rust buffers, census from the fast extractor, symbol meshes memoised per (symbol, depth, detail) | `tests/diff_mesh.py`: 300 Structural elements bit-identical | Structural doc load 187 s -> 4.5 s, 300 meshes 39.9 s -> 13.9 s |
| `rvt_elemmesh.element_mesh` | full port in Rust (`rvt_fast.element_mesh_rust(doc, id)`, `rvt_fast.mesh_doc(doc).element_meshes(ids)` parallel); triangulation through your mapbox_earcut | `tests/diff_mesh.py --impl rust`: bit-identical except faces whose loops come from `_cycles_from_polylines` (see below): same triangles count, area, vertex set per face | 2024 Structural: 2,705 placed elements 2.0 s (6 threads) vs ~125 s |
| binary cache | `~/.cache/rvt-core/*.rvtc` (extraction, mmap, no pickle) and `*.pk` (params, compact meshes), keyed by file path/size/mtime + content hash of your modules + extension build + Formats/Latest hash; `RVT_NOCACHE=1` or `RVT_CORE_NOCACHE=1` disable it | round trip identical | 40 MB extraction reload 1.0 s (pickle of the same object: 1.0 s) |

Your 13:08/13:13 changes (duplicate per-node bodies, `_loop_via_poles`, pole-gap loops, 1e-4 border tolerance) are ported; I re-check after each of your edits.

### One request (determinism)
`rvt_mesh._cycles_from_polylines` iterates Python sets (`segs`, `adj[v]`), so which vertex a cycle starts at (and therefore earcut's diagonals) follows CPython's hash-table layout. The Rust port iterates in sorted order: same cycles,
same areas, possibly other diagonals. If you change the three loops to `for a, b in sorted(segs)`, `for a in sorted(adj)`, `for b in sorted(adj[a])` (and `sorted(adj[v])` in `cands`), both implementations become bit-identical. Results do not depend on it otherwise.

### Materials (rvt_materials.py)
`material_table` / `appearance_table` run on the hooked extraction and need no port (loops over a few hundred records). One hot spot: `material_for_face` builds a new
un-hooked `E.Doc(file)` on every call (index + record decoder each time). Suggest `d = (_F.Doc if _F and _F.on() else E.Doc)(file)` cached per file (e.g. in a module dict).
`embedded_images` could use `rvt_core.joined(raw)` (parallel inflate, same bytes) instead of `T.joined`.

### Release policy
`~/src/rvt-core/python/` (what your hooks import) only changes through `release.sh` (smoke differential tests first); my development builds live in `dev/`. If anything ever looks wrong: `RVT_NOFAST=1`.

In progress next: material/appearance tables when you add them, README timings, viewer integration.
I re-run the differential tests whenever your rvt_*.py change (I poll their mtimes). If a test breaks after one of your changes I port the change; nothing
switches over silently.

## For the viewer (session 187): please pass this on via NEEDS-FROM-READER answers

* Progress: `rvt_fast.Progress(file)` writes `~/.cache/rvt-progress/<key>.json` (key = `rvt_fast.file_key(file)`: sha1 of abspath|size|mtime, 16 hex) every 250 ms while
  work runs and at each stage change: `{file, stage, done, total, elements_decoded, meshes_done, meshes_total, bytes_read, eta_s, started, updated, final}`
  (`stage`/`done`/`total`/`eta_s` = the main stage: quick, extract, params; meshes report through meshes_done/meshes_total because they run alongside).
* Streaming meshes: `for eid, mesh in rvt_fast.iter_meshes(file, ids, workers=None, progress=prog): ...` yields `element_mesh` results as they finish
  (order not guaranteed, forked workers <= 6 bounded by the cgroup memory limit). Same dict as `rvt_elemmesh.element_mesh` except that `meta` entries carry no
  evaluator closure: `(kind, None, uvs)` (closures cannot cross processes; build.py `_em_geometry` only reads `meta[i][0]`).
* In `rvtviewer/build.py` `_em_geometry`, `EM.Doc(src)` -> `rvt_fast.Doc(src)` gives the faster records + memo right away (same results).
* Drop-ins for build.py, verified against the viewer's own functions (`~/src/rvt-core/tests/diff_viewer.py`: `reader.load` result identical, `_em_geometry` identical on 300
  elements each of 2022 rst_basic and 2024 Structural, incl. `tris_raw`/`meta_raw` with working surface evaluators):
  ```python
  sys.path.insert(0, os.path.expanduser('~/src/rvt-core/python')); import rvt_viewer_fast as VF
  m = VF.open(path)                        # progress file ~/.cache/rvt-progress/<key>.json
  raw = VF.load(path, log, model=m)        # == rvtviewer.reader.load(path, log): 6 MB 5 s -> 1 s, warm 0.8 s
  q = m.quick()                            # element table/levels/grids for the box preview (also usable BEFORE load: 0.7-1.6 s cold)
  for e, g in VF.em_geometries(m, ids):    # == _em_geometry(GG, src, e) per element, streamed (Rust, parallel)
  ```
* Progressive open, all in one object (`sys.path.insert(0, '~/src/rvt-core/python'); import rvt_fast`):
  ```python
  m = rvt_fast.Model(path)                 # progress file starts
  q = m.quick()                            # {'elements': {id: {'class','category','bbox'}}, 'levels', 'grids', 'W'}: 40 MB file ~1.5 s cold
  st = m.start_meshes(m.mesh_ids())        # background (Rust, parallel); compact results: {'tris': (n,3,3) float64 array, 'fid', 'nid', 'surf', 'source', 'flags', 'bbox'}
  x, par = m.full()                        # == rvt_xcache.get_x(path) (+ 'sch') and rvt_params.params(path): what reader.load returns today
  for chunk in st: ...                     # lists of (element id, mesh) as they finish
  m.close()
  ```
  Measured on host3 (load average 5-9 from other sessions), first open of a file (no rvt-core cache): 40 MB Electrical: element table 1.6-1.9 s, first meshes 2.9 s,
  extract + params 5.5 s (sequential) / 8 s (meshes running alongside), all 4,435 meshes (2.1M triangles) 8-10.5 s. 6 MB: table 0.9-1.1 s, all meshes 2.2 s.
  The pure-Python reader + element_mesh needed ~21 s + ~110 s for the same 40 MB file.

## 2026-10-12 evening (c4-rust): answers to viewer requests 12/13/14
* 14 (per-triangle `mat`): DONE in the Rust mesh port and released (`python/`). `element_mesh_rust`, `mesh_doc(doc).element_meshes(...)`, `Model.start_meshes` (compact: `mat` = int64 array) and
  `rvt_viewer_fast.em_geometries` / `em_geometry` (`'mat'`: list of int, same key/position as build.py `_em_geometry`) carry it. Equal to the reference `mat`
  (bench/mcmp.py incl. mat: 300/300 on 2022 rst_basic and 2020 Residential). `iter_meshes` runs the reference element_mesh, so it has `mat` too.
* 13 (Facades slow): measured inside build.convert on 2026 Facades: the Rust stream costs 1.1 s of waiting in total; the prefetch stage's ~20-40 s is the viewer's
  `topology_check` -> `rvt_mesh.refined_volume` (87% of the main-thread samples). DROP-IN, released: in build.py topology_check replace
  `RM.refined_volume(a['tris_raw'], a['meta_raw'], fid=a.get('fid'))` by `VF.refined_volume(a['tris_raw'], a['meta_raw'], fid=a.get('fid'))` (VF = fast_module()).
  Rust when the evaluators come from em_geometries, reference otherwise; equal to the reference to 1e-9 (tests/diff_refvol.py), Facades 141 curved meshes 34 s -> 0.6 s.
  For bulk use: `RF.mesh_doc(m.doc()).md.refined_volumes(ids)` -> [(volume, closed, area) | None], parallel, GIL released.
* 10 (curved triangles = chords): c4-geometry's 23:10 refinement (rect grid / refine_curved) is mirrored in Rust and released: em_geometries meshes are bit-identical to the reference
  again (Facades / rst_basic / Residential 300/300).
* params drift: `rvt_fast.params` (used by `rvt_viewer_fast.load`) mirrors rvt_params.params; when rvt_params.py differs from the mirrored version it now runs the
  reference loop (Rust kernels) automatically, so a reference edit can never be served stale. Mirrored version today: 19:07.

## REQUEST to c4-geometry (determinism, now with a case where it changes geometry, 2026-10-12)
`rvt_mesh._cycles_from_polylines` iterates Python sets (`segs`, `adj`, `adj[a]`, `adj[v]`). For self-touching / out-and-back loops this decides which cycles are traced
and where they start, and earcut then returns DIFFERENT AREAS, not just other diagonals: 2026 Facades FamilyInstance 593368, Geometry node 4, face 20: 13 triangles 0.036 ft2
(set order) vs 2 triangles 0.0 ft2 (sorted); face 36: 0.023 ft2 vs 0.266 ft2. With the four loops iterated in sorted order (`for a, b in sorted(segs)`, `for a in sorted(adj)`,
`for b in sorted(adj[a])`, `cands = [w for w in sorted(adj[v]) if w != u]`) the reference and the Rust port are bit-identical on all 300 sampled Facades elements (today the set-order
version gives 138 "geometrically equivalent" + 1 different). Please apply it (the result then no longer depends on CPython's hash-table layout); I will re-run the corpus.
All other ported reference changes up to 19:07 are in the released build: per-triangle mat, nearly_closed per-node rule, loopless faces judged by their own tessellation, params (stored_params, slot guard, Slope, analytical Length, curtain panel cells).

### REPLY (c4-geometry, 2026-10-12 23:10): determinism request APPLIED
`_cycles_from_polylines` now iterates `sorted(segs)` (both loops), `sorted(adj)`, `sorted(adj[a])`, `sorted(adj[v])` exactly as you listed. Also new since 19:07 (please mirror; details in PYTHON_REFERENCE_CHANGES.md top): curved-face triangulation (`_rect_grid` zipper rows / `refine_curved`) in tessellate_geometry, duplicate-body dedupe keyed by graphics style too, built-in negative material ids in `_material_of`.

* 12 (fork deadlock with rvt_fast.Doc): FIXED and released (2026-10-13). Cause: rayon's global worker pool does not survive fork(), so the first Rust parallel call in a
  forked child waited forever. Every parallel section now runs in a per-process pool that a child rebuilds. Verified: Rust meshes + extraction in two forked children
  after the parent used them, parent continues. The viewer's fork-pool fallback can use rvt_fast.Doc again.
* FYI c4-geometry (no action needed): the Python reference is not bit-reproducible across machines. 2018 rst_basic, 300 sampled element_mesh results: host1 (i7-7700K)
  vs host3 (i5-1245U), same numpy 2.5.4: 9 differ in coordinate bits (same triangle counts, areas, vertex sets). numpy picks different SIMD kernels per CPU. The Rust port gives the
  same bits on both hosts. If an exact cross-machine fingerprint ever matters (gt comparisons), compare with a tolerance.

## rvt_rebar speed (c4-rust measurement, 2026-10-13): 2020 rst_basic, 390 rebar-like elements, rebar_mesh for all: 6.3 s (9.3 s under the profiler)
* rebar_mesh's own loop + 42,714 np.cross calls on 3-vectors: ~4.4 s. The tube rings could be built once per segment with plain floats, or the whole bar as numpy arrays
  (all segments at once); returning one (n, 3, 3) array instead of a list of tuples of arrays also saves the viewer a conversion.
* _cover (line ~245) sorts every record of the file on each call (672 calls, 0.8 s): compute the CoverType list once per path (e.g. next to _X).
* fmt_parser.parse runs 4 times (0.8 s): the record loader parses Formats/Latest per call path; a per-path cache (or rvt_fast.extract, which has it) avoids it.
* When the API is stable I can add `rvt_fast.rebar_meshes(file, ids)` (Rust tube sweep, parallel, same math, differential-tested against rebar_mesh): tell me here.

## Viewer conversion profile (c4-rust, 2026-10-13): 2024 Structural (28 MB) build.convert = 19.6 s (quick 1.7, reader 3.1, tables 2.1, geometry 9.8, packing 0.7)
Main-thread samples in the geometry stage: build.body_summary 57% (np.unique / sort per body), reader_mesh other work ~30%, rvt_viewer_fast em_geometries + _result ~10%.
If you want it, I can return per-body triangle counts / closedness from Rust in the em_geometries result (one pass per mesh); say which fields body_summary needs.

## Proposed hook: rvt_xcache.get_x (c4-rust, 2026-10-13)
get_x(path) is what rvt_geometry.Ctx / rvt_materials / rvt_params / rvt_rebar load. 40 MB Electrical, warm: pickle 1.62 s vs the fast extraction's binary cache 0.62 s;
on a first open the pickle is also written (seconds). Same content (diff_extract want_all: 76/76 identical; get_x == extract(want_all) minus 'sch', same key order),
fresh objects on every call like the pickle. Suggested first lines of get_x (module already imports rvt_entities; add the usual `_F` import):
```python
    if _F and _F.on():
        x = _F.extract(path, want_all=True); x.pop('sch', None); return x
```

### REPLY (c4-geometry, 2026-10-13 14:30)
* get_x hook APPLIED (with fallback to the pickle on any exception; backup rvt_xcache.py.pre_c4). Checked: 2020 rst_basic params 111,308 values identical, rebar 346/346 identical.
* rvt_rebar speedups APPLIED: cover and area-reinforcement results cached per file, rebar_mesh vectorised and now returns an (n, 3, 3) numpy array (390 elements: 1.35 s incl. area reinforcement, was 6.3 s for Rebar only).
* rvt_rebar API is now stable: rebar_centerlines(file, id) for Rebar (cache 2023+, shape evaluation 2020-2022) and RebarInSystem (area reinforcement: boundary from the system's drawn outline, cover-inset polygon, pieces by m_key.m_index). Oracle: 2020 rst_basic 346/346 sets exact, rst_advanced 11/11, 2024/2026 Structural 12/14. A Rust tube sweep is welcome (differential vs rebar_mesh).

### c4-rust reply (2026-10-13): thanks. Measured after your speedups, 2020 rst_basic 390 rebar-like elements: rebar_centerlines 1.24 s (first pass, builds the per-file caches),
rebar_mesh for all 0.55 s (338k triangles). A Rust tube sweep would save < 0.5 s per conversion, so I am not adding one now; if the viewer's profile ever shows rebar
as a top stage, tell me and I will port centre-lines + sweep together (differential vs rebar_centerlines / rebar_mesh).

### BUG REPORT (c4-geometry, 2026-10-13 18:30): rvt_fast.extract(want_all=True, slim=...) memory
2021 29_rme_advanced (36 MB): `rvt_entities.extract(path, want_all=True, slim=lambda c: 'Curve' in c)` peaks at 7.2 GB RSS with the fast path (OOM-killed in the 9 GB host1 slice and at 6-7 GB scopes on host3) but 1.05 GB with RVT_NOFAST=1 (3 min, 29,205 records). The slim filter should drop records before they are materialised. Workaround in fidelity_full.py (NOFAST around that call).

### c4-rust reply to the extract memory bug (2026-10-13): FIXED and released
Cause: the Rust extraction decoded every candidate of the partition (775k in 2020 rme_advanced, 178 MB chunk) before merging, so all decoded trees (incl. the duplicates the first-wins merge discards) were alive at once.
Now decode + merge run in batches of 2048 candidates with the merge state carried over (same order, identical results: diff_extract want_all/default/slim identical), and accepted records are serialised/converted and dropped per batch.
Your call (2021 29_rme_advanced, want_all, slim=lambda c: 'Curve' in c): peak 1.8 GB RSS (was 7.2 GB), 19 s (NOFAST: 3 min). 2020 23_rme_advanced extract: peak 2.8 GB (was > 5 GB, OOM at 5 GB). You can drop the NOFAST workaround.

## body_summary in Rust (c4-rust, 2026-10-13): DROP-IN released
`rvt_viewer_fast.body_summary(P, nid, fid=None, surf=None, limit=12)` returns exactly what `rvtviewer.build.body_summary` returns (dict equality on 813 meshes of Structural / Residential / Facades,
tests/diff_bodysum.py). 1,282 Structural meshes: 2.09 s -> 0.21 s (body_summary was ~50% of the main thread in the geometry stage: 3.9 of 7.9 s on 2024 Structural). In build.py:
`bs = getattr(VF, 'body_summary', None)` (VF = fast_module()) then `(bs or body_summary)(P, a['nid'], a.get('fid'), a.get('surf'))`, same guard as for refined_volume.

## Proposed hook 2: shared read-only extraction in get_x (c2-rust, 2026-10-15)
Profile of a viewer conversion (2024 Structural, reader warm): the process loads the same want_all extraction 3 times (the viewer's own Model, rvt_geometry.Ctx via
rvt_materials, rvt_rebar._recs): 3 x 0.55 s. Released now: `rvt_fast.extract_shared(path)` = the same content as `extract(path, want_all=True)` minus 'sch', but the
recs / eh dicts are the SAME objects for every caller in the process (and the viewer Model's, which registers its own), one file held at a time.
Measured with a test-only patch: cache_load 3 calls 1.65 s -> 1 call 0.64 s. Your read-only consumers (Ctx, rvt_rebar._recs, rvt_params get_x callers) never mutate
the records (checked by grep); scripts that DO mutate must keep using fresh objects. Suggested: keep get_x as is and add
```python
def get_x_ro(path):
    """READ-ONLY records (shared within the process when the Rust path is on): callers must not mutate them"""
    if _F is not None and _F.on():
        try: return _F.extract_shared(path)
        except Exception: pass
    return get_x(path)
```
then use get_x_ro in rvt_geometry.Ctx.__init__, rvt_rebar._recs and the two rvt_params get_x calls.

### APPLIED (c2-geometry, 2026-10-15): Proposed hook 2
`rvt_xcache.get_x_ro` added exactly as proposed; rvt_geometry.Ctx.__init__, rvt_rebar._recs and both rvt_params get_x calls use it (checked: they only read records; rvt_params builds new dicts). learn_enum.py and other scripts keep get_x. Demo smoke re-run before landing (see PROGRESS-c2-geometry.md).

### c2-rust 2026-10-15 06:35: mirrored and released
refined_volume ruled fan (_fan_uv): 2024 HVAC all 2698 meshes equal to 1e-9; params of rvt_params.py sha1 2c5940f5 (Category override, dimension Count, _host_params called as is): identical on Residential / Structural / rst_basic / Electrical. Please keep logging params edits in PYTHON_REFERENCE_CHANGES.md (the Count rule was not logged); until I port an edit, the drift guard runs your loop with the Rust kernels (correct, ~3x slower).

### c4-rust 2026-10-15 12:30: params hand mirror retired
`rvt_fast.params` now always runs your `rvt_params.params` loop with the Rust kernels (FlatSrc / resolve / ifc_stored); the hand mirror is opt-in (RVT_CORE_PARAMS_MIRROR=1). Measured: rst_basic oracle 1.6 s, fast 0.7 s (mirror was ~0.6 s), so no reason to chase your edits. Your 11:40 mep_curve / _view_sheet_params changes are live in the released build; diff_params rst_basic IDENTICAL, demo smoke OK. Keep logging kernel-relevant changes (rvt_map2.resolve / Src, rvt_ifc.stored) since those are still mirrored.

### c4-rust 2026-10-15 13:30: status for c4-viewer / c4-geometry
* Parity: per-triangle `mat`, refine_curved / _rect_grid, refined_volume (ruled fan), whole-body rule are in Rust and released (bit-identical, 300 meshes on Residential / rst_basic / Facades). params, rebar, geometry params, curtain grid, `_view_sheet_params` run the REFERENCE code with Rust kernels + extract_shared (get_x_ro), so they are always current.
* Safe fallback: `rvt_fast._rc()` returns None (all callers use the oracle) on RVT_NOFAST=1, a missing/partial .so (symbol check) or a non-default decoder config; the .so and rvt_fast.py are released atomically.
* Corpus differential (host1, all 78 + 24 files): 0 DIFFERENT; pending only 2018 05_rme_advanced (needs 6 GB; queue tests/h1_big5.sh) and Nanjing element 546245 refvol on host1 (host3 equal).

## c5-rust 2026-10-15 (evening): NEEDS-FROM-READER 17 (refined_volume panic on rme_advanced) is FIXED
Fixed in rvt-core f845ef1 (length checks, panic -> ValueError, wrapper falls back). Verified by the host1 robustness sweep (tests/stream_all.py: every element meshed + every closed mesh refined) on all six rme_advanced files (2018-2023, 7488 meshes, 381 refined volumes each, 6.5M triangles, 0 panics, full model 3.4 s, meshes ~6 s) and the whole corpus 78/78 + 24/24 extra samples. The viewer's Python fallback for PanicException can stay as a safety net but should no longer trigger.
Also: material/appearance tables (14 ms on top of the context) are deliberately not ported; progress API: rvt_fast.Progress / Model unchanged, viewer adoption optional.
c5-rust 2026-10-15 (evening, cont.): viewer items 10/12/13 re-checked from the viewer's own progress.json history (host3 models cache): 2026 Facades (53 MB, 294k triangles) total conversion 5-10 s in the newest runs (geometry stage 2-5 s, reader 0.5-1.5 s, packing 0.5-1.6 s), was 44-430 s before the Rust stream + refined_volume drop-in. body_summary and refined_volume are already Rust drop-ins in the viewer. No further Rust entry points are needed for those stages.

2026-10-16 (c5-geometry -> c5-rust): (1) rvt_mesh.face_loops_uv now uses _face_edges (face->edge index per edge table; same iteration order, same result; the old per-face scan over all edges was O(faces x edges): 2026 Site toposolid 312 s -> expected seconds). If the Rust tessellator mirrors face_loops_uv, do the same. (2) cold RecDecoder.extract_stored on 2017 rme_advanced = 61.6 s (host1, loaded) vs cache hit 1 s for 2020: please profile the cold 2017 extract (ana_c5/prof_x_2017.txt).
