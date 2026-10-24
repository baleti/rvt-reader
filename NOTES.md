# RVT format notes (Revit 2025 sample: F106-LAC724-MOD-AR-00061.rvt, 21 MB, workshared)

Container: OLE2 compound file (olefile reads it). Streams:
- BasicFileInfo (UTF-16LE): original save path, Revit version (2025), build 20250815_1515(x64), file GUIDs. Readable.
- ProjectInformation: a ZIP containing an Atom xml (title, product version, save date, parameter-group names). Readable.
- TransmissionData: UTF-16 XML, external file refs (keynote file paths, linked models). Readable.
- Global/DocumentIncrementTable: chunked-deflate; contains usernames of every editor (workshared). Readable.
- Global/PartitionTable: chunked-deflate; view names ("Floor Plan: LEVEL 39"), family/type names ("Family : Curtain Panels : ..."), worksets. Readable via UTF-16 strings.
- Global/History, ContentDocuments, ElemTable, Latest; Formats/Latest (class schema, ~17k identifiers); Partitions/N (bulk element data, 20 MB -> 107 MB raw).

Compression: NOT plain gzip. Stream = small header (8 or 44 bytes) + one or more members with a 10-byte gzip header
(1f 8b 08 00 ...) followed by RAW deflate (wbits=-15), no CRC trailer -> zlib "incorrect data check" errors with wbits=31.
Partitions/N is ~1169 such members back to back (each ~130 KB raw, 40-byte framing between). A naive search for 1f8b0800
gives false hits inside compressed data; they fail to inflate and are skipped (rvt_extract.inflate_chunks).

Phase 1 result: rvt_extract.py gives metadata, editors, view/family/type names and UTF-16 strings from element data
(families, materials, keynote codes, URLs, text) with no SDK.
Limits: strings are fragmentary (length-prefix bytes, truncated tails). Geometry, parameters-per-element, room/door/wall
values, sheets need real object decoding: Formats/Latest schema + ElemTable (id->offset) + per-class field walk.

## KEY FINDING (2026-10-08): streams are PAGED - the root cause of all earlier "corruption"
Large streams (Formats/Latest, Global/*, Partitions/*) are stored in pages of 65,249 bytes: the first 64,896 bytes are payload,
the last 353 bytes are a checksum/ECC trailer that must be REMOVED before inflating (rvtfmt.strip_pages). Page boundaries count from the start of
the OLE stream (including any 8-byte custom prefix). Streams < 64,896 bytes are unaffected, which is why small streams always worked.
Then: [optional 8-byte prefix] + 10-byte gzip header + raw deflate (-15) + 8-byte (CRC32, ISIZE) trailer. After stripping, 97/97 Formats+Global
streams in 14 files (Revit 2011-2025) match CRC and size exactly. Partitions/NN: 44-byte header + ~1270 gzip members, 0 false hits after stripping
(was 103 false hits and ~10.8 MB lost). Page layout numbers are also published by DrunkOnJava/rvt-rs (Apache-2.0, prior art), confirmed independently here
(the 0x00 byte at stream offset 64,896 in 3 streams, break position 64,89x in 3 streams, CRC/size match after stripping).
Superseded earlier wrong conclusions: "CRC mismatch = corruption" (true cause: paging), "~50% class-name overlap between versions" (tokenizer noise),
"PartitionTable lists views" (it is the worksharing partition list; see below).

## Formats/Latest grammar (fmt_parser.py) - parses 14/14 files, Revit 2011-2025, consuming the whole stream
stream  := u16 0 , record* , zero terminator
record  := u16 len + name , parent:u16 , X:u16 , [if parent&0x8000: record (inline parent definition)] , Y:u16 , count:u32 , field*count , tail
tail    := [u32 N + N*16-byte GUIDs]  (absent in Revit <= 2012 layout; auto-detected) , [u16 M unless record is an inline field-type definition]
field   := u32 len + name , type
type    := T:u32 (kind = low byte, flags = 2nd byte) ; if flags&0x10 and not flags&0x40: u32 n (fixed array) ;
           kind 0x0e and flags&0x0f==0: u16 ref (bit15 => inline class definition follows: u16 pad + record) ;
           kind 0x0d (array of): u32 k, 1 byte marker (0x20), nested type; if nested kind is 0x0e an extra u16 ref follows.
kinds: 01 bool, 02 u16, 04/05 u32, 06 f32, 07 f64, 08 string(flags 0x60), 09 guid, 0b u64, 0d array-of, 0e reference/class.
flags: 00 plain, 10 fixed array(n), 50 vector, 51 set/pointer-ish, 01/02/03 pointer variants (no ref follows).
Results (classes incl. inline-defined / fields): 2011:2853/7754, 2012:3154/8480, 2015:3725/10074, 2018:4024/10989, 2017:3879/10566, 2020:4164/11481, 2025:4600/12296.
~95% of class names are shared between consecutive versions in the set. Exports: schema/formats-*.json (export_schemas.py).
Not yet verified: meaning of X (small ints 1..8, ADocument 0xa66), parent u16 semantics (parent tag vs own tag; tag assignment), ancestor info.

## Global/ElemTable (reference: rvt-rs src/elem_table.rs, @phi-ag/rvt docs): 6-byte header then 40-byte records (verified: size 592,390 for 2025 file, ids ascend, later records reference earlier ones).
Not yet decoded: field layout inside the 40 bytes beyond element id (u32 at +6 in aligned view).

## Global/PartitionTable is the WORKSHARING partition list, not a view list. The 85 "View ..."/"Family ..." names in the 2025 file exist only because
it is a workshared central model; non-workshared files have 1 entry. View/sheet names must come from element data in Partitions/N.

## Cross-version samples (13) in samples/; still missing Revit 2021, 2023, 2024, 2026 files.

## Working tools (2026-10-08, end of day 1)
- rvtfmt.py            page stripping + truncated-gzip inflate (the core fix)
- fmt_parser.py        strict Formats/Latest schema parser (14/14 projects + 11/11 Autodesk sample families, Revit 2011-2026)
- export_schemas.py    schema -> schema/formats-*.json + cross-version class diff
- rvt_elements.py      anchored sheet extraction (DBViewDrafting chain: sheetNumber,date,drawnBy,checkedBy,designedBy,approvedBy,issueDate;
                       sheet name = DBView.m_viewName at a per-file constant byte gap; gap learned from the file, schema estimate as prior)
- rvt2text.py          full text extractor for indexing (metadata, editors, external refs, sheets, clean length-prefixed UTF-16 names). Bounded memory.
                       120 MB model: ~2 min, 336 MB RSS. Small files ~1 s.
Validated: sheet lists look right on real files (Lynda house tutorial: Cover/Site/Foundation/First Floor/...; Paul Aubin Office Building A1..A13,C1,P1,S0,S1;
Nanjing MEP: E001..P800). Files with no sheets correctly yield none.

## Findings about wire format (verified)
- class tag = index in record list + 12 (1061/1061 checks); first u16 after a class name is the PARENT tag; X = unknown small int.
- ElementId: 4 bytes up to Revit 2023, 8 bytes from 2024 (observed: Level element m_id as i64; 2020 sheet record gap arithmetic).
- Element instance = base-class fields first (Element: 8 polymorphic pointers/sets, docAccess, 8 ElementIds, 3 bools), then derived classes' fields in schema order.
- Pointer fields (ref*, ref**) are polymorphic: [u16 class tag] + body; null/-1 forms vary (6 bytes seen in 2011 and 2020). Strings: u32 nchars + UTF-16LE.
- ElemTable record (40 bytes at offset 6): +0 u32 id, +16 u32 id again, +28 u64 owner id (all-ff = none), +36 u32 varies by element type (e.g. 182 levels, 355 other).
  No offset into partitions is stored there.
- Sheets are DBViewDrafting instances (Revit has no ViewSheet class); DatumPlane-derived elements (Level/Grid/RefPlane) found by anchor
  [8 ElementIds][3 bools][u32 len + name] validated against ElemTable ids.

  mimemap:   .rvt = application/x-revit      .rfa = application/x-revit      .rte = application/x-revit      .rft = application/x-revit

## Ground truth from real Revit (2026-10-10)
`groundtruth/*.json` = per-file output (BFI format, sheets, levels, element count); `compare_gt.py` diffs rvt2text against it.
Result: 24/24 files exact on Revit version + sheet list (68 sheets), 83/83 level names present. Found and fixed one bug this way:
sheets whose drawn/checked/designed-by are short initials had no 'Designer' anchor (rvt_elements._chains_dated).
Driver: guest `C:\ci\driver.py PORT OUTDIR @listfile` + `job.cs` (dialog/failure handlers; upgraded files are saved once to C:\Users\User\upgraded\<year>\ and reused).
Gotchas: matching-year Revit avoids upgrades; a Revit that is "busy" at ~0 CPU is blocked on a dialog (see /v1/info ui.modalDialog); never leave an old batch loop posting to a restarted instance.

## Element decoder (rvt_decode.py / rvt_inventory.py), 2026-10-10
Record := [u32 A][id (4 or 8 bytes, from Identifier in schema)][u64 stamp][u16 class tag] + fixed part + pointer bodies.
Fixed part = class chain fields base-first. `ref->Class` = embedded struct; `ref<vector>` = u32 count + structs; `ref<set>` = u32 count + pointer slots;
pointer slot = u32 0 (null) | u32 handle + u16 class tag (body deferred, slot order; ref*** = u32 handle only).
Kinds: 1 bool(1B) 2 byte(1B) 3 short(2B) 4/5 u32 6 f32 7 f64 8 string 9 guid 0a u16 0b u64; array kind 0d = fixed n (ns[]) of next level or u32-count.
Element.m_id inside the record must equal the header id (validator). Records are accepted partial (decoded-up-to-failure).
Results: identity+class 98-99% of ElemTable ids on every file 2011-2026 tested; ~99% of Revit's API elements found.
Open: Cell-derived bodies (PatternHelper etc.) have an optional 16-byte prefix (07,-1,-1,-1) whose rule is unknown; geometry bodies (GeomStepList/GeomTable) not decoded;
Revit 2024+ differs only in id width. Param tables (ParamValue*) match Revit when present; most API parameters are derived from fields, not stored.

## Checkpoint 2026-10-10 (evening): element decoder vs Revit ground truth
Corpus: 78 native Autodesk sample files 2017-2026 (corpus/<year>/, from the offline VM, git-excluded) + 24 older samples; Revit dumps (gt4/*.tsv: E/P rows, all elements incl. types, all parameters)
for 2020-2026 via guest C:\ci\driver.py + job3.cs. Tools: rvt_decode.py (decoder), rvt_inventory.py, rvt_cache.py, eval_gt.py, rvt_map.py (learn internal field -> API parameter by agreement),
rvt_map_eval.py, rvt_cov_params.py, rvt_fail.py/agg_fail.py/one_fail.py/trace_fail.py (failure analysis), geom_tail.py/geom_hyp.py (geometry experiments), run_cov.py.
Numbers: identity+class for 98-99% of ElemTable ids on all files 2017-2026; 99% of Revit's API elements found; complete (no failure, no geometry stop) ~40% on projects, 92% on small families
(geometry incl.). Mapper on held-out files: 97.2% precision, 20% of Revit parameters explained by learned field links (+paramsets); the rest is derived (Category, Design Option, Length/Area/Volume,
system names...). Known good: sheets/views/levels/grids/phases/walls link fields exactly (see map_train.json).
Blocker: GeomStepList/GeomTable bodies (GeomGenerator: unexplained 9-byte prefix; hist-table vector encoding unclear; schema field M on classes unexplained). Everything stored AFTER geometry in a
record (TextNote text etc.) is unreachable until geometry decodes. Level elevation lives in the geometry body at a fixed offset (+203 from the start of the geometry bodies, 7/7 non-zero levels).
Plan: differential saves in the VM (create/modify known elements via the Revit API, save, diff decoded bytes) as the oracle for geometry/hidden fields.

## BREAKTHROUGH 2026-10-10 night: pointer bodies are BREADTH-FIRST
Record := header + fixed part (class chain base-first) + pointer bodies in FIFO order: bodies referenced by the object's own slots (slot order), then bodies referenced by those bodies, etc.
My earlier depth-first order produced all the "mystery prefixes" (9-byte GeomStep prefix, derived-first Face, M field): they were other bodies seen out of order. No hints are needed.
Pointer slot := u32 0 (null) | u32 handle(>maxh or 0xffffffff)+u16 tag (new object, body queued) | u32 handle<=maxh (back-reference, no tag; 1=document, 2=the element itself).
Flags: 0x50 vector of embedded structs; 0x51/0x54/.. set/vector of pointer slots (count + slots); array kind 0d: fixed (n per level) or u32 count.
Kinds: 1 bool, 2 int8, 3 int16, 4/5 u32, 6 f32, 7 f64, 8 string, 9 guid, 0a u16, 0b u64.
Result: 2020 rst_basic 13751/13765 records complete (99.9%), exact-fit 99.2%; geometry bodies included (Level: GeomStepList, GeomTable, Face, Plane decode exactly = elevation as Plane origin).
Tools: vm.sh (offline VM: put/get/ps/job), runjob.py (answers dialogs via /v1/dialog), exp/*.cs differential-save experiments (exp_out/*.rvt), rvt_solve.py (layout DFS with memo; used to find BFS), cov_year.py, cov_gt.py, cov_report.py.

## Extensible storage (ESEntity) - solved 2026-10-10
Pointer field ESEntity.m_blob is special: [u32 0 | u32 handle][16-byte SCHEMA GUID] (20 bytes, no u16 tag); the body (queued breadth-first) is the entity's values in
ESSchema.m_fields order sorted by m_entryIndex. Types by m_fieldTypeName: TCHAR string, int i32, short i16, char u8, bool u8, double f64 (canonical MILLIMETRES), float f32, GUIDvalue 16B,
ElementId (idsize), XYZ 3xf64, UV 2xf64, ESEntity (nested: slot inline, body queued). container 1 = [u32 count] values; container 2 = map [u32 count] (key,value) with type 'std::pair< K, V >'.
Schemas live in Global/Latest (ADocument root, not fully decoded yet) as vector<pair<GUID,ESSchema>>; rvt_es.find_schemas() locates and decodes them by signature (key GUID == m_guid).
Autodesk's own schemas are vendor-restricted in the API (no API ground truth), my own test schemas (exp/es2.cs) validated the encoding exactly.
Global/Latest = ADocument: [u32 tag 28][u32 0][u16 0?] then fields; root fixed part not yet fully aligned (m_pSteelModelInfo/PartitionTable nulls are 4-byte -1).
Other facts: Level elevation = DatumPlane.m_pSurface.obj.m_origin[2] (verified 9/9 2020, 19/19 2024).

## STATE at usage-limit stop (2026-10-10 night)
Per-year (cov_gt.py, % of Revit's elements fully decoded / exact): 2020 98.85/97.74, 2021 98.82/97.74, 2022 98.81/97.72, 2023 98.81/97.73, 2024 98.13/96.88 (2025/2026 only partly measured).
Open: (1) ~1-1.9% of Revit elements have no recognisable record header (appear only in id lists; their records may be in the 220-byte gaps between gzip members / raw data - was investigating Partitions gaps: 32-byte gaps and 220-byte gaps with plain text 'Data generated by Autodesk Revit'); (2) ~1% complete but not exact-end; (3) Global/Latest (ADocument root) fixed part not fully aligned (schemas found by signature in rvt_es.py);
(4) derived parameters: rvt_map2.py learner (own fields + 1-2 hops) written, only tested on one file; (5) indexing integration into rvt2text not done; (6) 2025/2026 ground truth now in gt4/, idstat for them needs a rerun.

## STATE 2026-10-11 (end of this work block)
Structural coverage vs Revit's element list (cov_gt.py, host1 runs): 2020-2023 100.00% complete / 99.99% exact; 2024-2026 ~99.8% (remaining: ~10 sketch ModelLines per file stored inside Sketch bodies, a few ProjectInfo/FamilySymbol).
Fixes since the BFS breakthrough: members joined per partition (records straddle gzip members), defined-handle set for back-references (not max handle), short header [A][id][u32 stamp][u16 tag], ESEntity schemas incl. 2025 layouts, byte-blob vectors >1MB, ElementHeader records (category/family/ownerView/designOption/bbox) captured separately.
Semantic layer (rvt_map2.py learn2/evaluate2, train on 7 files, test on 3 unseen across 2022/2024/2026): 68.4% of Revit's non-shared parameters reproduced, 98.7% precision (ElementId 78%, Integer 84%, Double 53%, String 42%).
Left (all computed by Revit, not stored): Area/Volume/Length (need B-rep/curve evaluation), Pressure Drop/Flow/System names (MEP engine), IfcGUID (derivable from UniqueId), Elevation/Offsets from geometry, Work Plane, etc.

## UniqueId / IfcGUID from the file alone (2026-10-11)
- Episode GUID table = tail of Global/History: entry i (i = 0 newest-first from the end) GUID (little-endian Data1-3) at offset len-21-17*i; table size = max episode index + 1.
- Element -> episode index: Global/ElemTable column 2 (u32 at +8 of the 28-byte record, 4-byte-id files) / u32 at +8 of the 40-byte record (8-byte-id files).
- UniqueId = "<episode guid>-<id as 8 hex digits>": verified 100% of Revit's elements 2020-2023, 99.7-99.9% 2024-2026 (rest are elements absent from ElemTable, the sketch lines).
- IfcGUID = IFC compressed GUID of (UniqueId guid with last 4 bytes XOR element id) (ifcguid.py); stored string param -1019000 in ParamValueSetAString wins when present (rvt_ifc.py); *CenterLine sub-elements (pipe/duct segments & fittings) inherit the IfcGUID of their owner. Result vs Revit: 2023 100%, 2024-2026 99.97% (HostObject x4, Material x2 per file residual).
## Geometry-derived (in progress)
- Line: length = |dirVec|*(t1-t0); Arc: radius*|t1-t0| (rvt_geom.py), exact vs Revit for ducts/pipes/conduits/cable trays/walls/columns.
- Family parameters stored per instance/symbol: m_pInstParams/m_pParams entries {m_paramId, m_value|m_int|m_str|m_elemId}; name = ParamElem*.m_pParamDef.m_caption (rvt_famparams.py), exact where present.
- Family-instance Area/Volume need the symbol's generative geometry (GLine/GGroup/GFilling histories + parameter expressions): not feasible to reproduce; out of scope.

## FINAL STATE 2026-10-11 (this block)
Per-year structural coverage vs Revit element lists (cov_gt.py, host1 re-run after all decoder/header changes):
  2020 75974 el. 100.00% complete / 99.99% exact | 2021 107975 100.00/99.99 | 2022 108673 100.00/99.99 | 2023 109129 100.00/99.99
  2024 79522 99.74/99.72 (205 not found) | 2025 72565 99.81/99.75 (138) | 2026 73191 99.81/99.79 (138)   [not found = sketch ModelLines stored inside Sketch bodies, absent from ElemTable]
rvt2text over all 100 corpus/sample files: all exit 0, no tracebacks, max 93 s (7 parallel), every output has the Entities block; adds UniqueId/IfcGUID for levels/rooms/sheets and a Quantities line (wall/duct/pipe/conduit/cable-tray modelled length).
UniqueId 100% (2020-2023) / 99.7-99.9% (2024-2026); IfcGUID 100% (2023), 99.97% (2024-2026).
Geometry-derived: curve Length exact (lines, arcs); MEP pipe/duct/conduit/tray Middle/Start/End/Top/Bottom Elevation, Slope, Area, Diameter, Width/Height ~97-100%; FamilyInstance Elevation from Level 99.8% where derivable.
rvt_params.py (+ eval_params.py): per-element parameter dump combining map3 mapping + caption-named family params + derived values + UniqueId/IfcGUID: on held-out 2022 rme_advanced 71% of Revit's parameter values reproduced at 98.1% precision (Double 59.5%).
NOT feasible/out of scope: Area/Volume of family instances and walls/floors needing the parametric solid (GLine/GGroup histories), MEP engine results beyond what is stored.

## Decoder gap closed (2026-10-11, later)
- Elements without their own ElemTable row (sketch ModelLines/Sketch/Floor in parents, 2024+): their ids are referenced at ElemTable row offset +20 (40-byte rows); rvt_scan.load() adds those ids -> all recovered.
- ProjectInfo: 100,547-char string tripped a 100k cap; rvt_decode.STRCAP=4e6 for records, ES schema scanner keeps 100k (rvt_es.find_schemas) to stay fast.
- cov_year exactness: a record followed by a header with id = all ones (non-element trailer / unlisted record) counts as exact.
- Final table: 2020-2023 100.00/100.00 (2023: 2 complete-not-listed-exact); 2024 99.77/99.77 (186 not found), 2025 99.84/99.80 (119), 2026 99.84/99.84 (119).
- Remaining not found = "Element" with no category/name/params whose ids occur NOWHERE in the file (not in ElemTable, partitions, Global/*): created by Revit at load. 2025: 10 more are decoded completely but are followed by an unlisted record (4457-byte AppearanceAssetElem + 125-byte tail etc.).
- Exactness: the record after the 'complete, not exact' ones is a FamSymSurrogate/other non-Element class (id not in ElemTable): cov_year now accepts any next header with a valid class tag. Result: 2023 100.00/100.00, 2025 99.84/99.83 (1 AppearanceAssetElement left unexplained), 2024/2026 unchanged.
- cov_year exactness: next header A field bound relaxed to 1<<24 -> 2025 table 99.84/99.84.

## PROVENANCE of every data source used by the parser (2026-10-11)
Sources actually used:
1. Own analysis of the .rvt/.rfa files (OLE container, paging, gzip members, Formats/Latest class schema, Global/ElemTable, Global/History, Global/Latest, Partitions/*): all structure, record grammar, ESEntity layout, UniqueId/episode tables.
2. Revit VM dumps (Revit 2020-2026 API run in the offline VM): gt4/*.tsv, groundtruth*/, exp_out/ - used as ground truth and to derive category_names.json (328 entries, re-verified 328/328 against the 'Name|id' category field of gt4) and param_names.json (parameter id -> name from gt4 P lines). If complete BuiltInCategory/BuiltInParameter tables are needed, regenerate them from the Revit API (enum names/values) in a VM and record the run here.
3. Public prior art: phi-ag/rvt (open-source Revit file parser) - consulted for the container idea only; no code or data copied.
4. rvt_hints.json is an empty ({}) file; fmt tokens (schema/formats_tokens.json, schema/formats-*.json) are produced by our own fmt_parser from sample files.

## PERFORMANCE profile (2026-10-11; host1 under heavy load ~15, cProfile inflates ~2x) - rvt2text.run on corpus/2022/30_rst_basic_sample_project.rvt (6.4 MB)
total 37 s profiled: schema-driven record decoding (rvt_decode.record/body/struct/value/elem) 16 s (16.5k records, 11.4M struct.unpack_from calls = 3.6 s alone);
rvt_entities.extract own loop (header candidate checks, dict building) 3.5 s tottime; ES (extensible storage) schema search rvt_es.find_schemas 7.7 s; header_candidates (numpy isin over 4 alignments) 3.2 s;
fmt_parser.parse (Formats/Latest schema) 2.7 s x5 calls (re-parsed per Schema build: cacheable by schema hash); zlib inflate 0.6 s; bytes.hex 1.4 s (debug strings in value()).
=> inflate/paging is NOT the bottleneck; Python per-field decoding and the ES schema scan are. Rust target: rvt_decode core + header scan; cheap wins: cache parsed schema + ES schemas by hash, skip bytes.hex, numpy-free candidate scan via bytes.find on id patterns, decode only wanted classes (already), parallel partitions.

## BREAKTHROUGH (2026-10-11): saved graphics = partition channel 103 (family/element geometry source)
Partition streams are sequences of segments: each gzip member is preceded by a 40- or 44-byte segment header whose last u64 is the CHANNEL: 101 (320 segs, definitions?), 102 (element records, 75 MB in 2024 Structural), 103 (33.7 MB: the graphics Revit last drew, one scene-graph record per element id).
Our joined() merged all channels; channel-103 records decode with the existing schema-driven decoder as ordinary records: header [A u32][id u64][stamp u64][tag u16], root class GElement (parent GRep) = {m_GInfo, m_subNodes (GGroup/GFilter/GInstance/...), m_bBox, m_tightbBox, m_elementId, m_gElemType}. For a segment, prepend 4 zero bytes (first record has no A) and chain records back-to-back (next record starts at the previous end).
In 2024 Structural: 93,376 records decoded (93,330 complete); the real GElements (7,666) carry Geometry (B-rep: Face/Edge/EdgeLoop + Plane/CylSurf/RuledSurf/SurfRev surfaces), GLine/GArc/GEllipse/GPolyLine/GPoint (curves), GFilling, GBitmap, GInstance+InstanceInfo (instance of a symbol graph with transform), GConditionDir/Int/Cut/Selected (view/detail filters). 688 of 883 FamilySymbols have Geometry => FAMILY SYMBOL SOLIDS ARE STORED here (the earlier 'family geometry is not stored' conclusion was wrong: it lives in channel 103, not in the element records).
Prior-art idea source only (rvt-rs README/RE-78 'saved graphics', channels 102/103); no code taken.

## GEOMETRY STATUS (2026-10-11, interim - usage limit hit)
Done: rvt_geometry.py v0 + GEOMETRY_API.md (floors/ceilings extrusions from sketches, walls straight/arc approx, MEP sweeps, family instances = box-only from symbol outline); OCC (cadquery-ocp) installed in host1 ~/occ-env.
Measured: Floor Area 194/289 exact, Perimeter 262/289; Ceiling Area 659/677, Perimeter 677/677 (all years); walls 3 exact/5 approx/1 off of 9 (joins/openings missing).
Key discovery: saved graphics (channel 103) hold per-element evaluated B-rep (GElement -> Geometry/Face/Edge/EdgeLoop, Plane+CylSurf exact: P=center+R cos(u) xVec+R sin(u) yVec+v zVec; edge firstAndLast = [start,end] each with uv on both adjacent faces). Tools: g103_all.py (index), g103_get.py, rvt_brep.py, rvt_mesh.py (planar+cylinder tessellation, volume), symvol_test.py. Box symbol volume matched exactly (130.896 ft3).
Open: instance own record has Geometry with many edges (open meshes = unsupported surfaces RuledSurf/SurfRev/cone, missing loops); need instance transform handling, view-condition node selection, then score per class/year. Class status still BOX-ONLY: all FamilyInstance, rooms, stairs, railings, topography, fittings.

## GEOMETRY STATUS - per-class fidelity (2026-10-11, 7 files: one per year 2020-2026, up to 300 elements per class, saved-graphics meshes via rvt_elemmesh.element_mesh)
exact = closed mesh whose volume equals Revit's Volume within 1e-4; approx = mesh bbox IoU >= 0.95 with the element's stored Revit bbox (m_bBox); partial = IoU 0.5-0.95; box-only = no mesh / IoU < 0.5.
FamilyInstance n=2100: exact 20.2%, approx 33.6%, partial 36.6%, box-only 9.7%   (2020-2022 rst files: ~1/3 exact; 2024-2026 Snowdon files far lower: curved/ruled/revolved surfaces + cut/joined shells not handled)
SWall n=204: approx 100% (bbox), exact-volume 0% (joins/openings/cuts)        Floor n=113: exact 73.5%, approx 26.5%       DPart n=180: exact 100%
FamilySymbol n=1324: approx 14.0%, partial 11.6%, box-only 74.3% (many symbols have no solid graphics: 2D/annotation, or unsupported surfaces)
ContFooting n=43: approx 69.8%, box-only 30.2%   AnalyticalModelWall: approx 33% / box-only 56%   ArcWall n=6: partial 100%   FormElem, ShaftOpening, StairsTriserSymbol: approx 100% (n<=8)
BOX-ONLY (no usable solid): SketchGrid 96%, FilledRegion 100%, AnalyticalModelSlab 100%, ImportInstance/MasterImportSymbol 100%, MassLevelData, StairsSupport, StairsElement, StairsRun (n=4 each), GuideGrid.
Not yet attempted: stairs/railings solids, MEP fittings (graphics exist but need ruled/revolved surfaces), rooms, topography; surfaces still unsupported: RuledSurf (two profile curves + points), SurfRev (revolved profile), cones/tori; curved edges use stored interior points only.
Pipeline: g103_get.cached_index(file) (channel-103 index; segments joined by the continuation flag, 100% of 93,359 records complete in 2024 Structural) -> rvt_elemmesh.element_mesh (own faces inside the element bbox, else the symbol's graphics transformed by the GInstance transform) -> rvt_geometry.element_geometry (analytic builders first, mesh fallback 'mesh_approx').

## PERFORMANCE results (2026-10-11, host3 idle, 12 cores, systemd-run MemoryMax=6G)  [before = original code, RVT_NOCACHE=1 RVT_WORKERS=1]
Profile (40 MB file, cProfile): record decode in Python (rvt_decode struct/value/elem) 66%, partition inflate + join 26% (the real cost was `d.decompress(data[i+10:])` slicing = O(n^2) memcpy, not zlib: 0.4 s of actual inflate), ES schema scan 3 x 17 s, header scan 3%.
Fixes (all output bit-identical to before, verified): (1) memoryview instead of slicing in segments(); thread-pool inflate using the compressed size in each 24-byte segment header (joined: 6.3 s -> 0.27 s for a 214 MB partition);
(2) record decoding spread over forked workers (RVT_WORKERS, default min(6,cpu); results merged in candidate order, identical); (3) Formats/Latest parse cached by content hash (~/.cache/rvt-schema);
(4) ES schema scan: numpy prefilter (3-6x faster, 17 files identical to the reference scan, es_ref.py/es_cmp.py) + result cache keyed by Global/Latest hash; (5) whole rvt2text output cached in ~/.cache/rvt2text keyed by file path/size/mtime + code mtimes (0.05 s).
Timings rvt2text (s): 6.5 MB: before 4.2 -> cold 2.2 / warm 1.8 / cached 0.05;  28 MB (2024 Structural): ~? -> cold 10.5 / warm 10.2;  41.6 MB (2024 Plumbing): before 51.3 -> cold (new Global/Latest: ES scan 17 s) 24.8 / warm schema cache 6.4 / output cache 0.05.
Remaining cost: record decoding (Python) and the per-file ES scan; these are the Rust targets (rvt_decode core), plus candidate scan.
Rust: ~/src/rvt-core (own git repo, excluded from the dotfiles repo via .git/info/exclude). Stage 1 = strip_pages + joined + header_candidates; differential test tests/diff_core.py: 183 partitions (all corpus 2017-2026 + samples), 0 differences, 3 partitions where the Rust reader declines (layout) and Python is used. Stage 1 gain is small (Python joined already threaded: 8.7 s vs 6.8 s total over all files); the real target is stage 2 (record decoder, 66% of time).

## Rust stage 2 (2026-10-11): record decoder in ~/src/rvt-core (src/decoder.rs), used through rvt_decode.make_dec()/FastDec (falls back to Python Dec when rvt_core is missing, RVT_NOFAST=1, hints/experiment env set, or the buffer is not bytes)
Differential tests (tests/diff_decoder.py, 7 files 2017-2026, 9,714 cases incl. both header forms): 0 differences, 0 exception mismatches (NaN compared equal); end-to-end rvt_entities.extract(want_all) on two files: 0 of 14,036 / 25,738 records differ, 0 header records differ.
Speed (extract only, 1 worker, warm schema caches): 6.4 MB file 22.5 s -> 6.8 s; 41.6 MB file 35.0 s -> 12.1 s (Python oracle -> Rust), with 6 workers lower still.
The built extension is copied to ~/rvt-research/rvt_core.abi3.so (abi3, python >= 3.9); rebuild: cd ~/src/rvt-core && . .venv/bin/activate && maturin build --release.

## GEOMETRY progress 2026-10-11/12 (reader session 176) - details behind the acceptance table (fid_table.py over fidfull3/*.jsonl, rows per element: fidelity_full.py)
- Walls now exact: element's own shell isolated from the solid + single-face reference Geometry nodes (select_closed_shell), loops from edge-pointer topology (fallback: planar-graph cycles), edges collected from the whole Geometry subtree: 8/8 walls in 2020 rst and 16/16 in 2020 Commercial (incl. openings) have volume = Revit's to 1e-4.
- Curved shells: lateral surfaces refined in (u,v) with winding preserved, plane caps densified through the neighbouring curved face so circles are true circles: cylinder pier 14.9772 vs Revit 14.9817 (0.03%).
- Remaining known failure classes: assemblies of overlapping bodies (nested components; Revit volume != sum of bodies), curtain panels/mullion types in templates (no geometry), stacked-wall parents (Revit volume 0 -> excluded), hosts/cuts (m_complexCutGeoms not decoded), stored m_bBox is larger than the solid for many walls (IoU vs stored bbox is not a valid accuracy test for them; the Revit oracle bbox from session 181 is needed).


## GEOMETRY vs Revit's own geometry (gt_geom oracle) - 2026-10-12 (reader session 176)
Oracle: ~/rvt-research/gt_geom/*.tsv (Revit API dumps by session 181). Criteria per element: volume <=2%, surface area <=3%, centroid <=1% of bbox diagonal (sum over all solids of the element, instances composed to world). Reproduce: `gt_geom_cmp.py FILE OUT.jsonl` then `gtg_table.py OUT*.jsonl`.

### 2020 sample projects (rst_basic 531 el., Commercial 645, Residential 197; all three files, every element with a solid in the oracle)
```
class                          n     vol    area    cent     all   (volume<=2%, area<=3%, centroid<=1% diag, all three; of elements with a solid in the Revit oracle)
FamilyInstance               628   99.7%   98.9%   99.7%   98.9%  no-graphics 0 empty 0
Mullion                      285  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Wall                         125  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Panel                        106  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Part                          45  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
WallSweep                     40  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Room                          25   96.0%   96.0%   96.0%   96.0%  no-graphics 0 empty 0
AnalyticalModelSurface        20  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Element                       20  100.0%   80.0%  100.0%   80.0%  no-graphics 0 empty 0
Floor                         14  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
WallFoundation                13  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Ceiling                       11  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Railing                        9  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Stairs                         6  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
StairsRun                      6  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
FilledRegion                   5  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
FootPrintRoof                  4  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Fascia                         4  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
BuildingPad                    3  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
ModelText                      2  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
MassLevelData                  1  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
SlabEdge                       1  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
```
### Rosetta single-feature files 2024 (stairs, railings, spheres/cones/tori/revolutions, extrusions with arcs, void cuts, spline sketch profiles, curved/profile walls, wall types, doors/windows, rooms, house, mullions)
```
class                          n     vol    area    cent     all   (volume<=2%, area<=3%, centroid<=1% diag, all three; of elements with a solid in the Revit oracle)
FamilyInstance               149  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Wall                          61  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Mullion                       39  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Floor                         35  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Panel                         16  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Railing                        6  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
TopRail                        6  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Room                           5  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Element                        4  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
WallSweep                      2  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Stairs                         2  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
StairsRun                      2  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
```
Topography (5 points -> TIN): `gtg_topo.py`
```
topography_base vertices equal: True tris 4 vs 4 area 1621.8076 vs 1621.8076
topography_var vertices equal: True tris 4 vs 4 area 1698.7361 vs 1698.7361
```
Profile families (structural/mullion/railing/sweep/reveal/stringer, `gtg_prof2.py`): per-type outline extents agree with Revit's type parameters for 63/69 profile types (the 6 misses are Form Deck / Stair Tread whose parameters are not the outline extents); the exact polygons of complex profiles are NOT in the symbol's saved graphics (bounding rectangle + reference planes only) - they must be read from consumers (sweep/beam/mullion end-caps via `end_cap_profile`), which match through the exact volumes above.

### What fixed the 2020 misses (all own analysis, validated against the oracle)
* instance transform: world = m_3x3 @ local + m_or (columns are the basis vectors; never transpose); stairs/railings/balusters/rods compose through nested instances; instances of other ELEMENTS (nested hosted FamilyInstances, a railing's top rail via m_forbiddenTarget) are not part of an element's solid, but a wall's WallSweep instances are (reveals, WallSweepInfo.m_wallSweepType==1, cut instead).
* Geometry node selection: detail-level conditions (3,3,v); (0,3,v) nodes show at the other detail levels; bodies are the nodes that close on their own; auxiliary single faces/bounding boxes are dropped; ModelText keeps only the categorised node.
* surfaces: edgeless faces (sphere/torus halves), pole triangles, boundary samples snapped onto exact plane/curved intersection curves, grid lines through edge samples so neighbouring faces weld; faces with holes touching the outline; zero-width slits cancelled.
* volume: face-level orientation propagation (element_mesh returns `fid`), non-manifold chords ignored, relative-to-centre accumulation (far-origin centroids), T-junction aware watertightness, zero-volume sheets (analytical surfaces, filled regions, mass level data) compared by area + bbox.

### Known remaining deviations (documented, not hidden)
* Room floor/ceiling faces with zero-width slits (1 room in Residential): Revit's own face area is a signed-loop sum, not a region area.
* `Element` class (legend component holders): the oracle counts a zero-volume planar sheet solid in the element area (4 of 20 elements 'area' only).
* ~1% of FamilyInstances: tiny parts with curved fillets (area +3%, volume exact).
* Profile families: exact polygons only through consumers (above).


## Per-class / per-year geometry table, all corpus files 2020-2026 (partial, published 2026-10-12 ~10:05; fid_table.py over fidfull4/ = 44 of 61 gt4 files re-run with the final code, remaining files from the earlier run fidfull3)
Per element (<=400 per class per file): ACCURATE = decoded solid with Revit's Volume within 2% (gt4 `Volume`, medium detail) or, where Revit gives no volume, bbox IoU >= 0.95 vs the stored bbox; TRUE-OFF = a mesh exists (IoU >= 0.5) but volume/IoU criteria fail; BOX-ONLY = no usable mesh. Type definitions and elements Revit reports as volume 0 (stacked-wall parents, annotation) are excluded. Annotation/2D/container classes (legends, sketch grids, groups, import instances) have no solid and are not listed. Per year columns: ACCURATE/true-off/box-only % (n).
Authoritative accuracy numbers for volume AND area AND centroid vs Revit's geometry (1,373 elements, 2020 samples + rosetta) are in the previous section (every class >= 96%).
```
class                      n   ACCURATE   true-off   box-only   (median IoU, median |vol err| where Revit gives Volume)
CurveElem                 23889      0.2%      0.0%     99.8%   iou 1.000  vol nan%
FamilyInstance            17758     86.3%     10.9%      2.8%   iou 1.000  vol 0.00%
RbsDuctCurve               2945     99.9%      0.0%      0.1%   iou 1.000  vol nan%
RbsPipeCurve               2400    100.0%      0.0%      0.0%   iou 1.000  vol nan%
SysMullionFamSym           2085     99.7%      0.0%      0.3%   iou 1.000  vol nan%
RoomElem                    919     85.5%      0.4%     14.0%   iou 1.000  vol 0.00%
SWall                      1842     81.7%      5.8%     12.5%   iou 0.977  vol 0.00%
RbsConduitCurve            1259    100.0%      0.0%      0.0%   iou 1.000  vol nan%
SysPanelFamSym             1252     96.7%      0.0%      3.3%   iou 1.000  vol nan%
WallSweep                   433     96.8%      0.0%      3.2%   iou 1.000  vol nan%
RbsFlexDuctCurve            432    100.0%      0.0%      0.0%   iou 1.000  vol nan%
FilledRegion                375      0.0%      0.0%    100.0%   iou 0.000  vol nan%
Ceiling                     366     99.7%      0.0%      0.3%   iou 1.000  vol 0.00%
Floor                       299     98.7%      1.3%      0.0%   iou 1.000  vol 0.00%
DPart                       185     98.9%      0.0%      1.1%   iou 1.000  vol 0.00%
BaseRailing                 145     34.5%     47.6%     17.9%   iou 0.675  vol nan%
RbsPipingSystem             126      0.0%      0.0%    100.0%   iou nan  vol nan%
ContFooting                  52    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
AnalyticalModelWall          49     18.4%     18.4%     63.3%   iou 0.000  vol nan%
Stairs                       44    100.0%      0.0%      0.0%   iou 1.000  vol nan%
ProfileRoof                  43    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
Toposolid                    42     85.7%      2.4%     11.9%   iou 1.000  vol 0.00%
SweepHost                    38     84.2%      0.0%     15.8%   iou 0.023  vol 0.00%
AnalyticalModelSlab          28      0.0%      0.0%    100.0%   iou 0.000  vol nan%
ShaftOpening                 27    100.0%      0.0%      0.0%   iou 1.000  vol nan%
FormElem                     26    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalPanel              26     11.5%     11.5%     76.9%   iou 0.000  vol nan%
MassLevelData                24      0.0%      0.0%    100.0%   iou 0.000  vol nan%
SiteSurface                  22     95.5%      0.0%      4.5%   iou 1.000  vol nan%
CableTray                    20     85.0%      0.0%     15.0%   iou 1.000  vol nan%
ExtrusionElem                18    100.0%      0.0%      0.0%   iou 1.000  vol nan%
GuideGrid                    18      0.0%      0.0%    100.0%   iou 0.000  vol nan%
StairsSupport                16     50.0%      0.0%     50.0%   iou 0.609  vol nan%
ArcWall                      14    100.0%      0.0%      0.0%   iou 0.959  vol 0.18%
StairsElement                 9     44.4%     11.1%     44.4%   iou 0.667  vol nan%
StairsRun                     9     33.3%     22.2%     44.4%   iou 0.667  vol nan%
SWallRectOpening              8    100.0%      0.0%      0.0%   iou 1.000  vol nan%
Text3dElem                    8     62.5%     37.5%      0.0%   iou 0.957  vol nan%
BuildingPad                   7    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
SweepElem                     6     66.7%      0.0%     33.3%   iou 1.000  vol nan%
TopRail                       6    100.0%      0.0%      0.0%   iou 1.000  vol nan%

per year (all classes with >=5 elements with graphics):
CurveElem              2020:0/0/100(n5897) 2021:0/0/100(n7110) 2022:0/0/100(n3000) 2023:0/0/100(n2400) 2024:1/0/99(n1456) 2025:1/0/99(n1456) 2026:1/0/99(n2570)
FamilyInstance         2020:85/2/1(n2629) 2021:86/7/2(n7426) 2022:88/3/0(n497) 2023:90/4/1(n2400) 2024:68/28/1(n1966) 2025:76/13/7(n1966) 2026:66/23/7(n1967)
RbsDuctCurve           2020:100/0/0(n400) 2022:0/0/100(n2) 2023:100/0/0(n800) 2024:100/0/0(n581) 2025:100/0/0(n581) 2026:100/0/0(n581)
RbsPipeCurve           2020:100/0/0(n400) 2023:100/0/0(n800) 2024:100/0/0(n400) 2025:100/0/0(n400) 2026:100/0/0(n400)
SysMullionFamSym       2020:100/0/0(n309) 2021:100/0/0(n634) 2023:100/0/0(n1142)
RoomElem               2020:80/1/1(n223) 2021:0/0/19(n271) 2022:0/0/3(n31) 2023:54/0/9(n603) 2024:20/0/3(n247) 2025:47/0/3(n247) 2026:47/0/3(n247)
SWall                  2020:80/4/10(n325) 2021:67/16/17(n381) 2022:100/0/0(n9) 2023:81/0/19(n713) 2024:92/6/0(n146) 2025:92/6/0(n146) 2026:92/6/0(n146)
RbsConduitCurve        2020:100/0/0(n20) 2023:100/0/0(n39) 2024:100/0/0(n400) 2025:100/0/0(n400) 2026:100/0/0(n400)
SysPanelFamSym         2020:90/0/10(n242) 2021:99/0/1(n298) 2022:0/0/100(n2) 2023:99/0/1(n708) 2025:0/0/100(n1) 2026:0/0/100(n1)
WallSweep              2020:100/0/0(n44) 2021:100/0/0(n33) 2023:94/0/6(n35) 2024:96/0/4(n107) 2025:96/0/4(n107) 2026:96/0/4(n107)
RbsFlexDuctCurve       2020:100/0/0(n113) 2023:100/0/0(n226) 2024:100/0/0(n31) 2025:100/0/0(n31) 2026:100/0/0(n31)
FilledRegion           2020:0/0/100(n78) 2021:0/0/100(n81) 2022:0/0/100(n56) 2023:0/0/100(n94) 2024:0/0/100(n22) 2025:0/0/100(n22) 2026:0/0/100(n22)
Ceiling                2020:100/0/0(n53) 2021:100/0/0(n113) 2022:0/0/100(n1) 2023:100/0/0(n199)
Floor                  2020:100/0/0(n40) 2021:91/9/0(n43) 2022:100/0/0(n5) 2023:100/0/0(n85) 2024:100/0/0(n42) 2025:100/0/0(n42) 2026:100/0/0(n42)
DPart                  2020:100/0/0(n45) 2021:100/0/0(n45) 2022:96/0/4(n47) 2023:100/0/0(n45) 2024:100/0/0(n1) 2025:100/0/0(n1) 2026:100/0/0(n1)
BaseRailing            2020:48/52/0(n23) 2021:0/41/59(n44) 2023:50/50/0(n72) 2024:50/50/0(n2) 2025:50/50/0(n2) 2026:50/50/0(n2)
RbsPipingSystem        2020:0/0/83(n6) 2023:0/0/83(n12) 2024:0/0/92(n40) 2025:0/0/92(n40) 2026:0/0/92(n40)
ContFooting            2020:100/0/0(n13) 2021:100/0/0(n4) 2022:100/0/0(n4) 2023:100/0/0(n4) 2024:100/0/0(n9) 2025:100/0/0(n9) 2026:100/0/0(n9)
AnalyticalModelWall    2020:12/20/68(n25) 2021:20/20/60(n15) 2022:33/11/56(n9)
Stairs                 2020:100/0/0(n8) 2021:100/0/0(n10) 2023:100/0/0(n26)
ProfileRoof            2020:100/0/0(n4) 2021:100/0/0(n12) 2023:100/0/0(n12) 2024:100/0/0(n5) 2025:100/0/0(n5) 2026:100/0/0(n5)
Toposolid              2024:86/0/14(n14) 2025:86/0/14(n14) 2026:86/7/7(n14)
SweepHost              2020:40/0/60(n5) 2021:0/0/100(n3) 2023:100/0/0(n3) 2024:100/0/0(n9) 2025:100/0/0(n9) 2026:100/0/0(n9)
AnalyticalModelSlab    2020:0/0/100(n13) 2021:0/0/100(n10) 2022:0/0/100(n5)
ShaftOpening           2020:100/0/0(n4) 2021:100/0/0(n10) 2023:100/0/0(n10) 2024:100/0/0(n1) 2025:100/0/0(n1) 2026:100/0/0(n1)
FormElem               2020:100/0/0(n2) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2) 2024:100/0/0(n6) 2025:100/0/0(n6) 2026:100/0/0(n6)
AnalyticalPanel        2023:13/13/74(n23) 2025:0/0/100(n3)
MassLevelData          2020:0/0/100(n2) 2021:0/0/100(n10) 2022:0/0/100(n2) 2023:0/0/100(n10)
SiteSurface            2020:90/0/10(n10) 2021:100/0/0(n6) 2023:100/0/0(n6)
CableTray              2021:0/0/100(n1) 2022:0/0/100(n2) 2023:100/0/0(n17)
ExtrusionElem          2020:100/0/0(n4) 2021:100/0/0(n5) 2023:100/0/0(n9)
GuideGrid              2024:0/0/100(n6) 2025:0/0/100(n6) 2026:0/0/100(n6)
StairsSupport          2020:80/0/20(n10) 2021:0/0/100(n2) 2022:0/0/100(n2) 2023:0/0/100(n2)
ArcWall                2020:100/0/0(n2) 2024:100/0/0(n4) 2025:100/0/0(n4) 2026:100/0/0(n4)
StairsElement          2020:67/17/17(n6) 2021:0/0/100(n1) 2022:0/0/100(n1) 2023:0/0/100(n1)
StairsRun              2020:50/33/17(n6) 2021:0/0/100(n1) 2022:0/0/100(n1) 2023:0/0/100(n1)
SWallRectOpening       2021:100/0/0(n4) 2023:100/0/0(n4)
Text3dElem             2020:100/0/0(n3) 2023:100/0/0(n2) 2024:0/100/0(n1) 2025:0/100/0(n1) 2026:0/100/0(n1)
BuildingPad            2020:100/0/0(n3) 2021:100/0/0(n2) 2023:100/0/0(n2)
SweepElem              2021:100/0/0(n2) 2023:50/0/50(n4)
TopRail                2024:100/0/0(n2) 2025:100/0/0(n2) 2026:100/0/0(n2)

(34942 type/symbol definition rows excluded)
```
Reading guide: CurveElem (reference/model lines) shows box-only because the curve decoder only covers the primary-curve classes (open item, see below); FilledRegion / Analytical* / MassLevelData are zero-volume sheets (checked by area+bbox against the oracle: 100% in the 2020 files; the fidfull rows count them box-only because Revit gives no Volume); BaseRailing / StairsSupport / StairsElement / StairsRun rows in this table are from files not yet re-run with the stair/railing fixes (the oracle shows 100%).

## MATERIALS / APPEARANCE / TEXTURES (2026-10-12, reader) - rvt_materials.py
Decoded from the records (own analysis): MaterialElem.m_pMaterial (name, class, category, colour int BGR, transparency, smoothness, shininess, glow, cut/surface pattern ids + colours, appearance asset id, structural asset id) and AppearanceAssetElem.m_pAppearanceAsset (schema name, library, tree of AProperty name/value with connected assets: generic_diffuse (+ connected UnifiedBitmapSchema texture: unifiedbitmap_Bitmap path, texture_RealWorldScaleX/Y, offsets, WAngle), reflectivity, glossiness, metal, transparency, refraction, bump, self illumination, tint). Per face: face m_renderStyleId (MaterialElem id) else the Geometry node's graphics style -> GStyleElem.m_materialElemId (the oracle's per-solid `material=` equals the node's GStyle id). Embedded images: 100-170 PNG blobs per project (material swatch thumbnails 128/64 px, image symbols); texture bitmaps themselves are not in the .rvt (asset-library relative paths only). Verified on 2020 Residential (139 materials, 55 textured), 2021, 2024, 2026 samples; schemas Generic/Wall Paint/Plastic-Vinyl/Metal/Hardwood/Concrete/Masonry CMU/Glazing. Validation requests for Revit's own values are in NEEDS-FROM-ORACLE.md (pending).

## Status after the 2026-10-12 host3 reboot
fidfull5 (final-code corpus evaluation, <=400 elements per class per file) resumed from 11 finished files; host3 MemAvailable is ~2-5 GB because of many viewer processes (session 187), so the evaluator runs when >=5 GB is free. Oracle-based accuracy (authoritative) is unaffected: 2020 samples + all rosetta files (2024 and 2026) every class >= 96%.
Rooms: in the corpus tables most 2021-2024 RoomElem rows are 'excluded' because Revit reports Volume 0 for unplaced/unenclosed rooms; classes with box-only rows are listed in the table footers.


## UPDATE 2026-10-12 14:20 - geometry vs Revit (final code) and materials vs Revit
2020 samples (all three files; every element with a solid in the oracle; criteria volume<=2% / area<=3% / centroid<=1% diag):
```
class                          n     vol    area    cent     all   (volume<=2%, area<=3%, centroid<=1% diag, all three; of elements with a solid in the Revit oracle)
FamilyInstance               628  100.0%   99.2%  100.0%   99.2%  no-graphics 0 empty 0
Mullion                      285  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Wall                         125  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Panel                        106  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Part                          45  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
WallSweep                     40  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Room                          25   96.0%   96.0%   96.0%   96.0%  no-graphics 0 empty 0
AnalyticalModelSurface        20  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Element                       20  100.0%   80.0%  100.0%   80.0%  no-graphics 0 empty 0
Floor                         14  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
WallFoundation                13  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Ceiling                       11  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Railing                        9  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Stairs                         6  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
StairsRun                      6  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
FilledRegion                   5  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
FootPrintRoof                  4  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Fascia                         4  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
BuildingPad                    3  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
ModelText                      2  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
MassLevelData                  1  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
SlabEdge                       1  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
```
All rosetta files, 2024 and 2026 (gt_geom; stairs, railings, revolutions, void cuts, wall openings k/k2/geom, rooms, floors, columns, hosted doors/windows, all_types, house, topography):
```
class                          n     vol    area    cent     all   (volume<=2%, area<=3%, centroid<=1% diag, all three; of elements with a solid in the Revit oracle)
FamilyInstance               638  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Wall                         342  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Floor                         82  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Mullion                       39  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Room                          26  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Panel                         18  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Railing                       12  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
TopRail                       12  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Element                        8  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
Stairs                         4  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
StairsRun                      4  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
WallSweep                      2  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
FootPrintRoof                  2  100.0%  100.0%  100.0%  100.0%  no-graphics 0 empty 0
```
Fixes since the previous table (own analysis, each validated here): Revit's Volume parameter follows FINE detail for loadable families (60/60 earlier Snowdon misses match at Fine, 0/60 at Medium; the evaluator now tries Fine then Medium and records `detail` per row); duplicate bodies; nested hosted FamilyInstances are not part of the host solid; instances of other symbols with `m_oEmbeddedSymbolGRep`; GInfo flag bits 0xE0 nodes are not displayed solids; (0,3,v) conditions; trimmed revolution faces whose pole edge is missing (`_loop_via_poles`); curve<->point ruled surfaces (fan from m_Point1); nearly-closed bodies (sampling mismatch on trimmed curved faces) counted as bodies; large terrain Toposolid (10.6M ft3, -0.85%).
MATERIALS validated against the oracle (gtg_mat.py, 2020 x3 + 2024 + 2026 samples): Material elements 530/530 on name, class, category, colour, transparency, shininess, smoothness, appearance asset id, cut and surface pattern ids (100%); appearance assets 465/465 found, schema 463/465; asset properties 38,417/38,417 values equal (incl. connected texture assets: bitmap path, scale, offset, angle); compound-structure layers 398 listed. Face materials (gtg_fmat.py, 52 sampled elements): 49 identical material sets, 3 supersets, 0 wrong.
Corpus evaluation (all 61 gt4 files) is running on host1 (`fidfull6/`, final code, Fine-then-Medium); the per-class/per-year table will replace the interim one when it finishes. Stale rows in the interim table (before these fixes) explain most of its SWall/RoomElem/BaseRailing/Stairs gaps: RoomElem is 99.5% once unplaced rooms (no geometry in Revit either) are excluded; BaseRailing/Stairs classes are judged by the oracle only (the stored bbox includes child elements).

## UPDATE 2026-10-12 23:45 (c4-geometry, continues session 176)
Materials: `element_mesh` returns `mat` per triangle (face render style -> style material -> node graphics-style material; built-in negative ids kept). Oracle (Face.MaterialElementId): 52/52 sampled elements; 2020 Residential ALL elements (fmatall) 172/189, the 17 misses were rooms (built-in -4000011), fixed. Paint = the face's own render style.
Curved faces: earcut on uv loops produced chords through doubly curved solids (viewer request 10). Fixed with `_rect_grid` (zipper rows through the loop's border samples) / `refine_curved` (conforming interior-edge bisection): torus emitted-triangle area 39.31 vs exact 39.48 (was 64.6); Facades 593321 19.26 vs 19.27 (was 65.2). The earlier analytic areas of such faces were also wrong (torus 40.1); refined_volume now follows the corrected uv triangles.
Revit's Volume PARAMETER semantics (own analysis vs gt4): (1) family instances: MEDIUM detail in files of Revit 2020-2025, FINE in 2026 (Snowdon Structural 608201: 13.6098 / 13.6098 / 13.7427 in the 2024 / 2025 / 2026 dumps = our Medium / Medium / Fine); (2) walls: the wall's own body, integrated sweeps / banding excluded (Facades 593337 102.51 vs 102.498; with sweeps 112.28) while Revit's geometry includes them; (3) duct fittings: body + coincident insulation + lining bodies all summed (2020 rme: Revit = 3x the body), so duplicate bodies are merged only within one graphics style; (4) curtain panels of a wall type (`m_isHostPanelSym` = 1): Volume 0; (5) family Area = half the solid's surface area, curtain panel Area = Width x Height (derived symbol `m_refs[0].m_width/m_height`).
Not geometry: RbsPipingSystem Volume = fluid volume; GM_OpeningWall_Type instances (31 in Snowdon Structural) have no solid in Revit either (void cutters).
Known residual: rooms with zero-width slits (2020_22 576007, 2020_20 159906: coincident internal faces), volume 2.5x low; rebar has no saved graphics (oracle centre-lines requested).
Parameters (rvt_params): stored sets by id (rooms' Name/Number were shifted), symbol_params (type values, follows m_masterId of derived symbols), material Transparency/Smoothness/Shininess, CurveElem Length (full circle = 2 pi r) and Slope = tan(m_angle), vertical column Length from m_refs, geometry-derived values (geom=True), learn_enum.py lookup rules. 2020_20 65.1% -> 83.2%, 2020_18 71.9% -> 85.2% (exact). Full corpus run queued on host1 (params_h1.sh: pout_c4n / pout_c4e, enum rules learned on the train split).

## REBAR (2026-10-13, c4-geometry): rvt_rebar.py
Rebar records (Revit 2023+) cache the centre-lines of the first bar (m_oInstance.m_oCacheData: m_selfIntersectingCenterlineCurves = plain curves as GetCenterlineCurves(adjustForSelfIntersection=false); m_noSelfIntersectingCenterlineCurves = Revit's tilted variant that avoids hook overlap), the other bars are m_barPositionsRelativeToFirstBarArr[i] (composed with m_individualBarsTrf[i]). Oracle gt_rebar (GetCenterlineCurves): 2024/2026 Structural 12/14 rebar sets exact (1e-4 ft, all bars, all curves). Residual: 2 sets hosted in nested pile components (cache in the host's saved frame m_savedHostTrf; needs the host's current placement). 2020-2022 records have no cache: shape evaluation (RebarShape.m_oDefinition edges/vertices + instance m_params + bend diameters + hooks) needed; RebarInSystem (area reinforcement) is a key into the RebarSystem layers.
Shape evaluation for files without the cache (2020-2022), validated on bar 0 (the 2020 API overload returns the first bar for every index): 2020 rst_basic 122/122 rebar sets exact, rst_advanced 11/11 (one hook tip 0.0007 ft). Rules (own analysis): segment lengths are out-to-out from (0,0) along each edge's fixed m_dir with the instance value m_oInstance.m_params[paramId] -> m_values.m_doubles[m_index]; centre-line inset d/2 toward the turning side (straight bars: no inset); bends filleted with r = bend diameter / 2 + d / 2 (stirrup/tie bend diameter for style 1 shapes, else standard); hooks (RebarShape.m_hook degrees) at the end corners, side from RebarShape.m_hookOri (start 1 = left of the bar direction, 3 = right; end 3 = left, 1 = right), arc starts r + d/2 from the out-to-out end, extension = bar type m_HLSettingsMap[hook type].m_offsetLength when > 0, for 90-degree hooks m_hookLength - r - d/2, else RebarHookType.m_straightLineMultiplier x d; bar i at shape-local z = i * m_endPar / (n - 1), world = m_shapeInstTrf; m_includeFirstBar/LastBar = 0 hides the end bars. Not decoded: RebarInSystem / AreaReinforcement bars (boundary sketch + host faces + cover), 2 nested-host sets in 2024/2026.

## FINAL per-class / per-year geometry table, all corpus files 2020-2026 (published 2026-10-14, c4-geometry; replaces the interim tables above)
fid_table.py over fidfull8/ (60 of the 61 gt4 files: 2025_74/2026_74 have no corpus file; final code of 2026-10-13 18:45, Fine-then-Medium evaluation, <=400 elements per class per file). Per element: ACCURATE = decoded solid with Revit's Volume within 2% (Revit gives no Volume: bbox IoU >= 0.95 vs the stored bbox; zero-volume sheets/analytical surfaces validated by area+bbox in the oracle section); TRUE-OFF = mesh exists, criteria fail; BOX-ONLY = no usable mesh. Excluded and listed in the footers: type/symbol definitions, curtain/stacked wall hosts (zero-volume containers, geometry is in their panels/mullions), elements with an empty stored bbox (no geometry in Revit), void families (openings, reference columns: no solid in Revit), placeholder ids, unplaced rooms. 738 rows without a dump entry in their own year are judged against the same element id in another year's Revit dump (Snowdon 2024/25/26 are one project).
Reading: all classes with a meaningful population are >= 96% ACCURATE in total; per-year FamilyInstance 96-99% (2025/2026: 2% box-only = nested pile/void families, see residuals). Weakest rows: Text3dElem 77% (n13), SweepHost 93% (n41: fascia holders whose solid Revit's export lacks), SiteSurface 96%, Toposolid 98%, FamilyInstance 2025/26 96%.
```
class                      n   ACCURATE   true-off   box-only   (median IoU, median |vol err| where Revit gives Volume)
FamilyInstance            14495     97.8%      1.4%      0.8%   iou 0.998  vol 0.00%
CurveElem                 13743     99.9%      0.0%      0.1%   iou 1.000  vol nan%
RbsDuctCurve               4943    100.0%      0.0%      0.0%   iou 1.000  vol nan%
RbsPipeCurve               4400    100.0%      0.0%      0.0%   iou 1.000  vol nan%
SWall                      2592     99.3%      0.1%      0.6%   iou 0.977  vol 0.00%
RoomElem                   1605     99.4%      0.6%      0.0%   iou 1.000  vol 0.00%
RbsConduitCurve            1356    100.0%      0.0%      0.0%   iou 1.000  vol nan%
RbsFlexDuctCurve            997    100.0%      0.0%      0.0%   iou 1.000  vol nan%
Ceiling                     693    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
WallSweep                   452    100.0%      0.0%      0.0%   iou 1.000  vol nan%
Floor                       442    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
FilledRegion                422    100.0%      0.0%      0.0%   iou 0.000  vol nan%
BaseRailing                 259    100.0%      0.0%      0.0%   iou 0.937  vol nan%
DPart                       184     99.5%      0.0%      0.5%   iou 1.000  vol 0.00%
Stairs                       94    100.0%      0.0%      0.0%   iou 1.000  vol nan%
CableTray                    68    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalModelWall          55    100.0%      0.0%      0.0%   iou 0.000  vol nan%
ProfileRoof                  55    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
ContFooting                  52    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
Toposolid                    42     97.6%      2.4%      0.0%   iou 1.000  vol 0.00%
SweepHost                    41     92.7%      0.0%      7.3%   iou 0.039  vol 0.00%
ShaftOpening                 37    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalModelSlab          24    100.0%      0.0%      0.0%   iou 0.000  vol nan%
ExtrusionElem                33    100.0%      0.0%      0.0%   iou 1.000  vol nan%
MassLevelData                32    100.0%      0.0%      0.0%   iou 0.000  vol nan%
SiteSurface                  28     96.4%      0.0%      3.6%   iou 1.000  vol nan%
FormElem                     26    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalPanel              23    100.0%      0.0%      0.0%   iou 0.000  vol nan%
StairsSupport                16    100.0%      0.0%      0.0%   iou 0.609  vol nan%
ArcWall                      14    100.0%      0.0%      0.0%   iou 0.959  vol 0.01%
Text3dElem                   13     76.9%     23.1%      0.0%   iou 0.957  vol nan%
SWallRectOpening             12    100.0%      0.0%      0.0%   iou 1.000  vol nan%
StairsElement                 9    100.0%      0.0%      0.0%   iou 0.667  vol nan%
StairsRun                     9    100.0%      0.0%      0.0%   iou 0.667  vol nan%
BuildingPad                   9    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
BlendElem                     8    100.0%      0.0%      0.0%   iou 1.000  vol nan%
FamilyGeomCombination         8    100.0%      0.0%      0.0%   iou 1.000  vol nan%
SweepElem                     6    100.0%      0.0%      0.0%   iou 1.000  vol nan%
FaceRoof                      6    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
TopRail                       6    100.0%      0.0%      0.0%   iou 1.000  vol nan%

per year (all classes with >=5 elements with graphics):
FamilyInstance         2020:98/2/0(n1980) 2021:99/1/0(n2279) 2022:98/2/0(n2254) 2023:99/1/0(n2284) 2024:99/0/1(n1908) 2025:96/1/2(n1895) 2026:96/1/2(n1895)
CurveElem              2020:100/0/0(n2156) 2021:100/0/0(n2411) 2022:100/0/0(n2408) 2023:100/0/0(n2400) 2024:100/0/0(n1456) 2025:100/0/0(n1456) 2026:100/0/0(n1456)
RbsDuctCurve           2020:100/0/0(n800) 2021:100/0/0(n800) 2022:100/0/0(n800) 2023:100/0/0(n800) 2024:100/0/0(n581) 2025:100/0/0(n581) 2026:100/0/0(n581)
RbsPipeCurve           2020:100/0/0(n800) 2021:100/0/0(n800) 2022:100/0/0(n800) 2023:100/0/0(n800) 2024:100/0/0(n400) 2025:100/0/0(n400) 2026:100/0/0(n400)
SWall                  2020:99/0/1(n411) 2021:99/0/1(n583) 2022:99/0/1(n583) 2023:99/0/1(n583) 2024:100/0/0(n144) 2025:100/0/0(n144) 2026:100/0/0(n144)
RoomElem               2020:99/1/0(n343) 2021:99/1/0(n326) 2022:99/1/0(n326) 2023:99/1/0(n326) 2024:100/0/0(n50) 2025:100/0/0(n117) 2026:100/0/0(n117)
RbsConduitCurve        2020:100/0/0(n39) 2021:100/0/0(n39) 2022:100/0/0(n39) 2023:100/0/0(n39) 2024:100/0/0(n400) 2025:100/0/0(n400) 2026:100/0/0(n400)
RbsFlexDuctCurve       2020:100/0/0(n226) 2021:100/0/0(n226) 2022:100/0/0(n226) 2023:100/0/0(n226) 2024:100/0/0(n31) 2025:100/0/0(n31) 2026:100/0/0(n31)
Ceiling                2020:100/0/0(n96) 2021:100/0/0(n199) 2022:100/0/0(n199) 2023:100/0/0(n199)
WallSweep              2020:100/0/0(n44) 2021:100/0/0(n33) 2022:100/0/0(n33) 2023:100/0/0(n33) 2024:100/0/0(n103) 2025:100/0/0(n103) 2026:100/0/0(n103)
Floor                  2020:100/0/0(n61) 2021:100/0/0(n85) 2022:100/0/0(n85) 2023:100/0/0(n85) 2024:100/0/0(n42) 2025:100/0/0(n42) 2026:100/0/0(n42)
FilledRegion           2020:100/0/0(n83) 2021:100/0/0(n91) 2022:100/0/0(n91) 2023:100/0/0(n91) 2024:100/0/0(n22) 2025:100/0/0(n22) 2026:100/0/0(n22)
BaseRailing            2020:100/0/0(n37) 2021:100/0/0(n72) 2022:100/0/0(n72) 2023:100/0/0(n72) 2024:100/0/0(n2) 2025:100/0/0(n2) 2026:100/0/0(n2)
DPart                  2020:100/0/0(n45) 2021:100/0/0(n45) 2022:98/0/2(n46) 2023:100/0/0(n45) 2024:100/0/0(n1) 2025:100/0/0(n1) 2026:100/0/0(n1)
Stairs                 2020:100/0/0(n16) 2021:100/0/0(n26) 2022:100/0/0(n26) 2023:100/0/0(n26)
CableTray              2020:100/0/0(n17) 2021:100/0/0(n17) 2022:100/0/0(n17) 2023:100/0/0(n17)
AnalyticalModelWall    2020:100/0/0(n25) 2021:100/0/0(n15) 2022:100/0/0(n15)
ProfileRoof            2020:100/0/0(n4) 2021:100/0/0(n12) 2022:100/0/0(n12) 2023:100/0/0(n12) 2024:100/0/0(n5) 2025:100/0/0(n5) 2026:100/0/0(n5)
ContFooting            2020:100/0/0(n13) 2021:100/0/0(n4) 2022:100/0/0(n4) 2023:100/0/0(n4) 2024:100/0/0(n9) 2025:100/0/0(n9) 2026:100/0/0(n9)
Toposolid              2024:100/0/0(n14) 2025:100/0/0(n14) 2026:93/7/0(n14)
SweepHost              2020:40/0/60(n5) 2021:100/0/0(n3) 2022:100/0/0(n3) 2023:100/0/0(n3) 2024:100/0/0(n9) 2025:100/0/0(n9) 2026:100/0/0(n9)
ShaftOpening           2020:100/0/0(n4) 2021:100/0/0(n10) 2022:100/0/0(n10) 2023:100/0/0(n10) 2024:100/0/0(n1) 2025:100/0/0(n1) 2026:100/0/0(n1)
AnalyticalModelSlab    2020:100/0/0(n8) 2021:100/0/0(n8) 2022:100/0/0(n8)
ExtrusionElem          2020:100/0/0(n6) 2021:100/0/0(n9) 2022:100/0/0(n9) 2023:100/0/0(n9)
MassLevelData          2020:100/0/0(n2) 2021:100/0/0(n10) 2022:100/0/0(n10) 2023:100/0/0(n10)
SiteSurface            2020:90/0/10(n10) 2021:100/0/0(n6) 2022:100/0/0(n6) 2023:100/0/0(n6)
FormElem               2020:100/0/0(n2) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2) 2024:100/0/0(n6) 2025:100/0/0(n6) 2026:100/0/0(n6)
AnalyticalPanel        2023:100/0/0(n23)
StairsSupport          2020:100/0/0(n10) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
ArcWall                2020:100/0/0(n2) 2024:100/0/0(n4) 2025:100/0/0(n4) 2026:100/0/0(n4)
Text3dElem             2020:100/0/0(n4) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2) 2024:0/100/0(n1) 2025:0/100/0(n1) 2026:0/100/0(n1)
SWallRectOpening       2021:100/0/0(n4) 2022:100/0/0(n4) 2023:100/0/0(n4)
StairsElement          2020:100/0/0(n6) 2021:100/0/0(n1) 2022:100/0/0(n1) 2023:100/0/0(n1)
StairsRun              2020:100/0/0(n6) 2021:100/0/0(n1) 2022:100/0/0(n1) 2023:100/0/0(n1)
BuildingPad            2020:100/0/0(n3) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
BlendElem              2020:100/0/0(n2) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
FamilyGeomCombination  2020:100/0/0(n2) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
SweepElem              2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
FaceRoof               2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
TopRail                2024:100/0/0(n2) 2025:100/0/0(n2) 2026:100/0/0(n2)

(40176 type/symbol definition rows excluded; 738 rows judged against the same element in another year's Revit dump of the same model, because their own year's dump lacks them)

not solids (2D / annotation / system / container classes, excluded from the solid criterion): Dimension (3), ElementGroup (843), FamilySymbol (4645), GuideGrid (18), ImportInstance (18), LegendComponent (7536), LegendComponentGRepHolder (103), RbsPipingSystem (168), SketchGrid (2292), TextNote (4992)
sheet-like classes (zero-volume faces; counted ACCURATE when a mesh exists - validated vs the oracle): AnalyticalModelBeam (2383), AnalyticalModelColumn (2218), AnalyticalModelSlab (34), AnalyticalModelSurface (5), AnalyticalModelWall (55), AnalyticalPanel (26), FilledRegion (425), MassLevelData (32)
classes judged by the oracle comparison only (mesh exists; stored bbox includes child elements, Revit gives no Volume): BaseRailing (259), StairsElement (9), StairsRun (9), StairsSupport (16)
```
Rebar (not in the table: classes Rebar/RebarInSystem have no Volume-bearing saved graphics): rvt_rebar.py centre-lines vs Revit's GetCenterlineCurves: 2020 rst_basic 346/346 sets exact, 2020 rst_advanced 11/11, 2024/2026 Structural 12/14 (2 nested-host sets), Revit 2021-2022 shapes by shape evaluation (same rules as 2020).
Residuals / fundamental blockers (evidence in the sections above): rooms with zero-width slits (2 of 1,605); Facades 'Flex' columns 3% low (joined bodies cut at the bbox); 3 Residential fascias carry a solid Revit's export lacks; family profile polygons are not stored (bbox lines only, read from consumers' end caps); texture bitmaps are not in the .rvt (library paths only).

## PARAMETERS UPDATE 2026-10-15 07:00 (c2-geometry) - held-out numbers, rules learned on the TRAIN split (split.json: 40 train / 20 test files)
Exact reproduction of Revit's parameter values over all 20 TEST files (2,986,654 values, geometry-derived values OFF):
* c4n (rules of 2026-10-13, no learned enums): 79.71%
* c2t (learned enum rules train2 + Category override + Host/Host Id + dimension Count): 85.90%
* c2t4 (train4 rules, 120 samples/class, parameter-id keys for same-name parameters, identity rules, Work Plane, Type IfcGUID, Level ElementId): 86.45%
* geometry-derived values (RVT_PARAMS_GEOM=1: FamilyInstance/host Volume, Area, Length...) add more: 2020 Commercial 90.1% -> 93.0% (Volume exact 90 -> 639 of 767). Full per-year run with geometry: host1 job par2 (params_c2_h1.sh -> pout_c2g/), pending.
New derivations (exact on every checked file): FamilyInstance Host (String: 'Level : <name>', '<Family Name> : <Type Name>' of the host or of the face the sketch plane references, '<not associated>', 'Surface'/'Subregion', 'Pad : <type>', 'Boundary Conditions') and Host Id (host for wall/roof/ceiling/joist/truss hosts, else -1); Work Plane (sketch plane datum level/grid/reference plane, face element, the beam system's plane for its beams, else '<not associated>'); dimension Count = number of witness references; Type IfcGUID (type's IfcGUID); Category from learned per-class rules over the header category (centre lines, views, styles, materials).
CAVEAT (honest generalisation): train and test contain other-year copies of the same sample models, so a learned table keyed by element ids (e.g. a room's placement ref -> its name) can look right on the test split without generalising to a new model. Identity rules (value = source id) generalise; id-keyed name tables do not. A model-held-out split (train on some models, test on others) is the stricter measure: TODO.
Still not reproduced (test split, % of values): a_lookup ~2-6% (electrical wire Type/Hot Conductors/Wire Size, Connection Status, view Family/Type strings, sheet numbers / detail numbers / view scale on viewports), b_geom ~5-7% (Volume/Area/Length/MEP elevations: geometry pass), c_mep ~0.1-4.7% (system names, flows, pressure drops: Revit's MEP engine), d_other 1-6%.

## FINAL per-class / per-year geometry table, refreshed 2026-10-15 (c5-geometry; replaces the 2026-10-14 table; fidfull9 final code 2026-10-15, 60 of 61 gt4 files)
fid_table.py over the newest row per file (fidfull9 = final code of 2026-10-15 where present). SiteSurface is classed as a flat sheet (topography surface: mesh area equals Revit Surface Area exactly, 2020 Commercial 16201.727).
```
class                      n   ACCURATE   true-off   box-only   (median IoU, median |vol err| where Revit gives Volume)
FamilyInstance            14435     99.5%      0.3%      0.1%   iou 0.998  vol 0.00%
CurveElem                 13743     99.9%      0.0%      0.1%   iou 1.000  vol nan%
RbsDuctCurve               4943    100.0%      0.0%      0.0%   iou 1.000  vol nan%
RbsPipeCurve               4400    100.0%      0.0%      0.0%   iou 1.000  vol nan%
SWall                      2592     99.3%      0.1%      0.6%   iou 0.977  vol 0.00%
RoomElem                   1605     99.4%      0.6%      0.0%   iou 1.000  vol 0.00%
RbsConduitCurve            1356    100.0%      0.0%      0.0%   iou 1.000  vol nan%
RbsFlexDuctCurve            997    100.0%      0.0%      0.0%   iou 1.000  vol nan%
Ceiling                     693    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
WallSweep                   452    100.0%      0.0%      0.0%   iou 1.000  vol nan%
Floor                       442    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
FilledRegion                422    100.0%      0.0%      0.0%   iou 0.000  vol nan%
BaseRailing                 259    100.0%      0.0%      0.0%   iou 0.937  vol nan%
DPart                       184     99.5%      0.0%      0.5%   iou 1.000  vol 0.00%
Stairs                       94    100.0%      0.0%      0.0%   iou 1.000  vol nan%
CableTray                    68    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalModelWall          55    100.0%      0.0%      0.0%   iou 0.000  vol nan%
ProfileRoof                  55    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
ContFooting                  52    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
Toposolid                    42     97.6%      2.4%      0.0%   iou 1.000  vol 0.00%
SweepHost                    41    100.0%      0.0%      0.0%   iou 0.039  vol 0.00%
ShaftOpening                 37    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalModelSlab          24    100.0%      0.0%      0.0%   iou 0.000  vol nan%
ExtrusionElem                33    100.0%      0.0%      0.0%   iou 1.000  vol nan%
MassLevelData                32    100.0%      0.0%      0.0%   iou 0.000  vol nan%
SiteSurface                  28    100.0%      0.0%      0.0%   iou 1.000  vol nan%
FormElem                     26    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalPanel              23    100.0%      0.0%      0.0%   iou 0.000  vol nan%
StairsSupport                16    100.0%      0.0%      0.0%   iou 0.609  vol nan%
ArcWall                      14    100.0%      0.0%      0.0%   iou 0.959  vol 0.01%
Text3dElem                   13     76.9%     23.1%      0.0%   iou 0.957  vol nan%
SWallRectOpening             12    100.0%      0.0%      0.0%   iou 1.000  vol nan%
StairsElement                 9    100.0%      0.0%      0.0%   iou 0.667  vol nan%
StairsRun                     9    100.0%      0.0%      0.0%   iou 0.667  vol nan%
BuildingPad                   9    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
BlendElem                     8    100.0%      0.0%      0.0%   iou 1.000  vol nan%
FamilyGeomCombination         8    100.0%      0.0%      0.0%   iou 1.000  vol nan%
SweepElem                     6    100.0%      0.0%      0.0%   iou 1.000  vol nan%
FaceRoof                      6    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
TopRail                       6    100.0%      0.0%      0.0%   iou 1.000  vol nan%

per year (all classes with >=5 elements with graphics):
FamilyInstance         2020:100/0/0(n1980) 2021:100/0/0(n2279) 2022:99/1/0(n2254) 2023:100/0/0(n2284) 2024:99/0/0(n1908) 2025:99/0/0(n1865) 2026:99/0/0(n1865)
CurveElem              2020:100/0/0(n2156) 2021:100/0/0(n2411) 2022:100/0/0(n2408) 2023:100/0/0(n2400) 2024:100/0/0(n1456) 2025:100/0/0(n1456) 2026:100/0/0(n1456)
RbsDuctCurve           2020:100/0/0(n800) 2021:100/0/0(n800) 2022:100/0/0(n800) 2023:100/0/0(n800) 2024:100/0/0(n581) 2025:100/0/0(n581) 2026:100/0/0(n581)
RbsPipeCurve           2020:100/0/0(n800) 2021:100/0/0(n800) 2022:100/0/0(n800) 2023:100/0/0(n800) 2024:100/0/0(n400) 2025:100/0/0(n400) 2026:100/0/0(n400)
SWall                  2020:99/0/1(n411) 2021:99/0/1(n583) 2022:99/0/1(n583) 2023:99/0/1(n583) 2024:100/0/0(n144) 2025:100/0/0(n144) 2026:100/0/0(n144)
RoomElem               2020:99/1/0(n343) 2021:99/1/0(n326) 2022:99/1/0(n326) 2023:99/1/0(n326) 2024:100/0/0(n50) 2025:100/0/0(n117) 2026:100/0/0(n117)
RbsConduitCurve        2020:100/0/0(n39) 2021:100/0/0(n39) 2022:100/0/0(n39) 2023:100/0/0(n39) 2024:100/0/0(n400) 2025:100/0/0(n400) 2026:100/0/0(n400)
RbsFlexDuctCurve       2020:100/0/0(n226) 2021:100/0/0(n226) 2022:100/0/0(n226) 2023:100/0/0(n226) 2024:100/0/0(n31) 2025:100/0/0(n31) 2026:100/0/0(n31)
Ceiling                2020:100/0/0(n96) 2021:100/0/0(n199) 2022:100/0/0(n199) 2023:100/0/0(n199)
WallSweep              2020:100/0/0(n44) 2021:100/0/0(n33) 2022:100/0/0(n33) 2023:100/0/0(n33) 2024:100/0/0(n103) 2025:100/0/0(n103) 2026:100/0/0(n103)
Floor                  2020:100/0/0(n61) 2021:100/0/0(n85) 2022:100/0/0(n85) 2023:100/0/0(n85) 2024:100/0/0(n42) 2025:100/0/0(n42) 2026:100/0/0(n42)
FilledRegion           2020:100/0/0(n83) 2021:100/0/0(n91) 2022:100/0/0(n91) 2023:100/0/0(n91) 2024:100/0/0(n22) 2025:100/0/0(n22) 2026:100/0/0(n22)
BaseRailing            2020:100/0/0(n37) 2021:100/0/0(n72) 2022:100/0/0(n72) 2023:100/0/0(n72) 2024:100/0/0(n2) 2025:100/0/0(n2) 2026:100/0/0(n2)
DPart                  2020:100/0/0(n45) 2021:100/0/0(n45) 2022:98/0/2(n46) 2023:100/0/0(n45) 2024:100/0/0(n1) 2025:100/0/0(n1) 2026:100/0/0(n1)
Stairs                 2020:100/0/0(n16) 2021:100/0/0(n26) 2022:100/0/0(n26) 2023:100/0/0(n26)
CableTray              2020:100/0/0(n17) 2021:100/0/0(n17) 2022:100/0/0(n17) 2023:100/0/0(n17)
AnalyticalModelWall    2020:100/0/0(n25) 2021:100/0/0(n15) 2022:100/0/0(n15)
ProfileRoof            2020:100/0/0(n4) 2021:100/0/0(n12) 2022:100/0/0(n12) 2023:100/0/0(n12) 2024:100/0/0(n5) 2025:100/0/0(n5) 2026:100/0/0(n5)
ContFooting            2020:100/0/0(n13) 2021:100/0/0(n4) 2022:100/0/0(n4) 2023:100/0/0(n4) 2024:100/0/0(n9) 2025:100/0/0(n9) 2026:100/0/0(n9)
Toposolid              2024:100/0/0(n14) 2025:100/0/0(n14) 2026:93/7/0(n14)
SweepHost              2020:100/0/0(n5) 2021:100/0/0(n3) 2022:100/0/0(n3) 2023:100/0/0(n3) 2024:100/0/0(n9) 2025:100/0/0(n9) 2026:100/0/0(n9)
ShaftOpening           2020:100/0/0(n4) 2021:100/0/0(n10) 2022:100/0/0(n10) 2023:100/0/0(n10) 2024:100/0/0(n1) 2025:100/0/0(n1) 2026:100/0/0(n1)
AnalyticalModelSlab    2020:100/0/0(n8) 2021:100/0/0(n8) 2022:100/0/0(n8)
ExtrusionElem          2020:100/0/0(n6) 2021:100/0/0(n9) 2022:100/0/0(n9) 2023:100/0/0(n9)
MassLevelData          2020:100/0/0(n2) 2021:100/0/0(n10) 2022:100/0/0(n10) 2023:100/0/0(n10)
SiteSurface            2020:100/0/0(n10) 2021:100/0/0(n6) 2022:100/0/0(n6) 2023:100/0/0(n6)
FormElem               2020:100/0/0(n2) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2) 2024:100/0/0(n6) 2025:100/0/0(n6) 2026:100/0/0(n6)
AnalyticalPanel        2023:100/0/0(n23)
StairsSupport          2020:100/0/0(n10) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
ArcWall                2020:100/0/0(n2) 2024:100/0/0(n4) 2025:100/0/0(n4) 2026:100/0/0(n4)
Text3dElem             2020:100/0/0(n4) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2) 2024:0/100/0(n1) 2025:0/100/0(n1) 2026:0/100/0(n1)
SWallRectOpening       2021:100/0/0(n4) 2022:100/0/0(n4) 2023:100/0/0(n4)
StairsElement          2020:100/0/0(n6) 2021:100/0/0(n1) 2022:100/0/0(n1) 2023:100/0/0(n1)
StairsRun              2020:100/0/0(n6) 2021:100/0/0(n1) 2022:100/0/0(n1) 2023:100/0/0(n1)
BuildingPad            2020:100/0/0(n3) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
BlendElem              2020:100/0/0(n2) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
FamilyGeomCombination  2020:100/0/0(n2) 2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
SweepElem              2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
FaceRoof               2021:100/0/0(n2) 2022:100/0/0(n2) 2023:100/0/0(n2)
TopRail                2024:100/0/0(n2) 2025:100/0/0(n2) 2026:100/0/0(n2)

(40176 type/symbol definition rows excluded; 798 rows judged against the same element in another year's Revit dump of the same model, because their own year's dump lacks them)

not solids (2D / annotation / system / container classes, excluded from the solid criterion): Dimension (3), ElementGroup (843), FamilySymbol (4645), GuideGrid (18), ImportInstance (18), LegendComponent (7536), LegendComponentGRepHolder (103), RbsPipingSystem (168), SketchGrid (2292), TextNote (4992)
sheet-like classes (zero-volume faces; counted ACCURATE when a mesh exists - validated vs the oracle): AnalyticalModelBeam (2383), AnalyticalModelColumn (2218), AnalyticalModelSlab (34), AnalyticalModelSurface (5), AnalyticalModelWall (55), AnalyticalPanel (26), FilledRegion (425), MassLevelData (32), SiteSurface (28)
classes judged by the oracle comparison only (mesh exists; stored bbox includes child elements, Revit gives no Volume): BaseRailing (259), StairsElement (9), StairsRun (9), StairsSupport (16)

```

## Parameter reproduction, all 60 gt4 files, final code (c5-geometry, 2026-10-16; pout_c5 on host1 = rules from the TRAIN split, geometry-derived values on; before = pout_c2g)
ALL 93.7% exact (86.5% before): 2020 93.9, 2021 94.7, 2022 94.7, 2023 94.1, 2024 93.0, 2025 92.9, 2026 91.8. New derivations since: layered-type thermal values (exact), Material Type, OmniClass Title, construction-type names, window/door thermal+optical built-ins, beam/brace Length+level offsets, rebar Bar Length/Quantity/Layout Rule/Spacing, MEP system Section + System Name, Room Area/Perimeter.
```
year files    values  before%  exact%  exact+approx%   Double / Integer / String / ElementId exact%   not reproduced: a_lookup b_geom c_mep d_other (% of values)
2020    6   1068534     89.7    93.9     94.0        82.0 / 96.1 / 93.2 / 99.7     1.1 3.0 1.2 0.7
2021    9   1426259     90.6    94.7     94.8        84.5 / 96.2 / 93.1 / 99.7     1.0 2.6 0.9 0.6
2022    9   1438591     90.7    94.7     94.8        84.8 / 96.3 / 92.7 / 99.7     1.1 2.6 0.9 0.7
2023    9   1529686     88.2    94.1     94.2        86.8 / 91.0 / 93.6 / 99.3     2.1 2.1 0.9 0.7
2024    9   1294307     80.1    93.0     93.1        83.4 / 96.9 / 97.2 / 98.4     0.9 2.4 2.3 1.2
2025    9   1105074     79.4    92.9     93.0        83.8 / 95.7 / 96.5 / 98.5     1.3 2.2 1.9 1.6
2026    9   1113559     84.7    91.8     92.0        81.7 / 95.2 / 96.1 / 98.0     1.5 2.3 2.0 2.2
ALL    60   8976010              93.7     93.8
== a_lookup_candidate 116379
     3880 Leader Line [Integer]
     3610 Family and Type [String]
     3434 Connection Status [Integer]
     3278 Column Location Mark [String]
     2914 Sheet Number [String]
     2731 Has Association [Integer]
     2492 Referencing Sheet [String]
     2476 Occupancy Unit [Integer]
     2472 Ways [Integer]
     2374 Export to IFC [Integer]
     2319 Referencing Detail [String]
     1946 Family [String]
     1834 Host [String]
     1699 Moves With Grids [Integer]
     1699 Location Mark [String]
     1699 Associated Level [ElementId]
     1574 Quantity [Integer]
     1517 Far Clipping [Integer]
     1470 Rebar Number [String]
     1438 Sheet Name [String]
     1419 Type [ElementId]
     1403 Associated Level [String]
     1368 Structural Material [ElementId]
     1291 Detail Number [String]
     1248 y Justification [Integer]
== b_geom 221063
    47616 Area [Double]
    39070 Volume [Double]
    18596 Elevation from Level [Double]
    16011 Invert Elevation [Double]
     7149 Elevation at Bottom [Double]
     6951 Length [Double]
     6425 Elevation at Top [Double]
     6116 Cut Length [Double]
     6052 OffsetHeight [Double]
     6052 OffsetWidth [Double]
     4928 Slope [Double]
     4088 End Join Cutback [Double]
     3570 Perimeter [Double]
     3180 Top Elevation [Double]
     3174 Bottom Elevation [Double]
     2875 Unconnected Height [Double]
     2669 Start Join Cutback [Double]
     2476 Area per Person [Double]
     2381 Total Bar Length [Double]
     2336 Takeoff Length Projection [Double]
     2316 Cross-Section Rotation [Double]
     1904 Width [Double]
     1748 Head Height [Double]
     1703 Elevation at Top Survey [Double]
     1703 Elevation at Bottom Survey [Double]
== c_mep 124439
    30169 Pressure Drop [Double]
    13361 Velocity Pressure [Double]
    12686 System Type [ElementId]
    11121 Flow [Double]
    10180 Friction [Double]
    10180 Velocity [Double]
     9270 System Classification [String]
     5880 Loss Coefficient [Double]
     4107 Section [Integer]
     3246 Relative Roughness [Double]
     2348 Circuit Description [String]
     2204 Additional Flow [Double]
     1930 Electrical Data [String]
     1627 Friction Factor [Double]
     1016 System Length [Double]
      744 Static Pressure [Double]
      462 Reynolds number [Double]
      456 Voltage [Double]
      382 Branch Circuit Apparent Power Phase C [Double]
      382 Branch Circuit Apparent Power Phase B [Double]
      382 Branch Circuit Apparent Power Phase A [Double]
      316 Circuits [String]
      262 Branch Circuit Current Phase A [Double]
      254 Branch Circuit Current Phase B [Double]
      245 Branch Circuit Current Phase C [Double]
== d_other 94557
    19724 Fixture Units [Double]
     3786 Maximum Size [Double]
     3786 Minimum Size [Double]
     3419 Coefficient of Utilization [Double]
     2479 Calculated Cooling Load per area [Double]
     2479 Calculated Heating Load per area [Double]
     2479 Calculated Supply Airflow per area [Double]
     2244 Work Plane Grid Spacing [Double]
     1827 Spacing [Double]
     1812 Latent Heat Gain per person [Double]
     1812 Sensible Heat Gain per person [Double]
     1812 Total Heat Gain per person [Double]
     1684 Text Size [Double]
     1312 Actual Lighting Load per area [Double]
     1278 Apparent Power Phase C [Double]
     1278 Apparent Power Phase B [Double]
     1278 Apparent Power Phase A [Double]
     1264 Actual Power Load per area [Double]
     1188 Average Estimated Illumination [Double]
     1188 Room Cavity Ratio [Double]
     1133 Tension perpendicular to grain [Double]
     1128 Apparent Power [Double]
     1111 Bend Radius [Double]
     1019 Lining Thickness [Double]
      992 True Power [Double]

```

## 2017 geometry fidelity (c5-geometry, 2026-10-16; fid_table_old.py over fidold/, FID_TABLE_2017.txt)
Revit 2017 has no oracle dump, so each 2017 file is compared with the Revit 2020/2021 dump of the SAME model (element ids survive the upgrade): 2017 rst_basic, rst_advanced, Arch_Link, rme_basic (4 files, about 6.5k placed elements judged with the same criteria as the 2020-2026 table). Not yet done: 2017 rme_advanced (cold extract is slow and the host1 job was OOM-killed at 4.9 GB peak), rac_advanced (no matching dump), and all of 2018/2019. Result: FamilyInstance 100% accurate (n=1511), SWall 99.3%, RoomElem 99.4%, Ceiling/Floor/DPart/MEP curves/Stairs/ProfileRoof 100%.
```
class                      n   ACCURATE   true-off   box-only   (median IoU, median |vol err| where Revit gives Volume)
CurveElem                  1608    100.0%      0.0%      0.0%   iou nan  vol nan%
FamilyInstance             1511    100.0%      0.0%      0.0%   iou 0.969  vol 0.00%
RbsDuctCurve                400    100.0%      0.0%      0.0%   iou 1.000  vol nan%
RbsPipeCurve                400    100.0%      0.0%      0.0%   iou 1.000  vol nan%
SWall                       302     99.3%      0.0%      0.7%   iou 0.977  vol 0.00%
RoomElem                    163     99.4%      0.6%      0.0%   iou 1.000  vol 0.00%
RbsFlexDuctCurve            113    100.0%      0.0%      0.0%   iou 1.000  vol nan%
Ceiling                      91    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
FilledRegion                 78    100.0%      0.0%      0.0%   iou 0.000  vol nan%
Floor                        48    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
DPart                        45    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
BaseRailing                  36    100.0%      0.0%      0.0%   iou 0.833  vol nan%
RbsConduitCurve              20    100.0%      0.0%      0.0%   iou 1.000  vol nan%
WallSweep                    17    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalModelWall          15    100.0%      0.0%      0.0%   iou 0.000  vol nan%
Stairs                       13    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalModelSlab           8    100.0%      0.0%      0.0%   iou 0.000  vol nan%
ShaftOpening                  8    100.0%      0.0%      0.0%   iou 1.000  vol nan%
MassLevelData                 6    100.0%      0.0%      0.0%   iou 0.000  vol nan%
ProfileRoof                   6    100.0%      0.0%      0.0%   iou 1.000  vol 0.04%
ExtrusionElem                 5    100.0%      0.0%      0.0%   iou 1.000  vol nan%

per year (all classes with >=5 elements with graphics):
CurveElem              2017:100/0/0(n1608)
FamilyInstance         2017:100/0/0(n1511)
RbsDuctCurve           2017:100/0/0(n400)
RbsPipeCurve           2017:100/0/0(n400)
SWall                  2017:99/0/1(n302)
RoomElem               2017:99/1/0(n163)
RbsFlexDuctCurve       2017:100/0/0(n113)
Ceiling                2017:100/0/0(n91)
FilledRegion           2017:100/0/0(n78)
Floor                  2017:100/0/0(n48)
DPart                  2017:100/0/0(n45)
BaseRailing            2017:100/0/0(n36)
RbsConduitCurve        2017:100/0/0(n20)
WallSweep              2017:100/0/0(n17)
AnalyticalModelWall    2017:100/0/0(n15)
Stairs                 2017:100/0/0(n13)
AnalyticalModelSlab    2017:100/0/0(n8)
ShaftOpening           2017:100/0/0(n8)
MassLevelData          2017:100/0/0(n6)
ProfileRoof            2017:100/0/0(n6)
ExtrusionElem          2017:100/0/0(n5)

(2276 type/symbol definition rows excluded; 0 rows judged against the same element in another year's Revit dump of the same model, because their own year's dump lacks them)

not solids (2D / annotation / system / container classes, excluded from the solid criterion): Dimension (1), ElementGroup (80), FamilySymbol (532), ImportInstance (4), LegendComponent (419), LegendComponentGRepHolder (4), RbsPipingSystem (7), SketchGrid (192), TextNote (693)
sheet-like classes (zero-volume faces; counted ACCURATE when a mesh exists - validated vs the oracle): AnalyticalModelBeam (782), AnalyticalModelColumn (538), AnalyticalModelSlab (10), AnalyticalModelWall (15), FilledRegion (78), MassLevelD
```

## Parameter reproduction, FINAL, all 60 gt4 files (c5-geometry, 2026-10-16 afternoon; pout_c9 on host1 = rules from the TRAIN split, geometry-derived values on; before = pout_c2g)
ALL 94.1% exact (86.5% before; 93.7% in the earlier pout_c5 table): 2020 94.7, 2021 95.3, 2022 95.3, 2023 94.6, 2024 93.0, 2025 92.9, 2026 91.9. Added since the 93.7% table: electrical/lighting node rule, room Area/Perimeter, MEP Section/System Name, pipe fitting Fine volume, rebar + RebarInSystem, beam level offsets, Head Height, built-in symbol values. Derived AFTER this run and validated on single files only (pout_c11: rst_basic 2020 96.60%, rst_advanced 2023 91.27%): structural Elevation at Top/Bottom (incl. z offset), AnalyticalMember releases.
```
year files    values  before%  exact%  exact+approx%   Double / Integer / String / ElementId exact%   not reproduced: a_lookup b_geom c_mep d_other (% of values)
2020    6   1068534     89.7    94.7     94.8        85.0 / 96.3 / 93.2 / 99.7     1.0 2.3 1.2 0.6
2021    9   1426259     90.6    95.3     95.5        86.8 / 96.5 / 93.1 / 99.7     1.0 2.1 0.9 0.6
2022    9   1438591     90.7    95.3     95.4        87.1 / 96.5 / 92.7 / 99.7     1.0 2.0 0.9 0.6
2023    9   1529686     88.2    94.6     94.7        88.0 / 91.9 / 93.6 / 99.3     1.9 1.8 0.9 0.7
2024    9   1294307     80.1    93.0     93.2        83.5 / 96.9 / 97.2 / 98.4     0.9 2.4 2.3 1.2
2025    9   1105074     79.4    92.9     93.0        83.8 / 95.7 / 96.5 / 98.5     1.3 2.2 1.9 1.6
2026    9   1113559     84.7    91.9     92.0        81.7 / 95.2 / 96.1 / 98.0     1.5 2.3 2.0 2.2
ALL    60   8976010              94.1     94.2
== a_lookup_candidate 112929
     3880 Leader Line [Integer]
     3610 Family and Type [String]
     3434 Connection Status [Integer]
     3278 Column Location Mark [String]
     2914 Sheet Number [String]
     2731 Has Association [Integer]
     2492 Referencing Sheet [String]
     2476 Occupancy Unit [Integer]
     2472 Ways [Integer]
     2374 Export to IFC [Integer]
     2319 Referencing Detail [String]
     1946 Family [String]
     1834 Host [String]
     1699 Moves With Grids [Integer]
     1699 Location Mark [String]
     1699 Associated Level [ElementId]
     1517 Far Clipping [Integer]
     1470 Rebar Number [String]
     1438 Sheet Name [String]
     1419 Type [ElementId]
     1403 Associated Level [String]
     1368 Structural Material [ElementId]
     1291 Detail Number [String]
     1248 y Justification [Integer]
     1233 Family [ElementId]
== b_geom 191619
    46158 Area [Double]
    37536 Volume [Double]
    16011 Invert Elevation [Double]
     7078 Elevation at Bottom [Double]
     6951 Length [Double]
     6354 Elevation at Top [Double]
     6116 Cut Length [Double]
     6052 OffsetHeight [Double]
     6052 OffsetWidth [Double]
     4928 Slope [Double]
     4088 End Join Cutback [Double]
     3961 Elevation from Level [Double]
     3333 Perimeter [Double]
     2875 Unconnected Height [Double]
     2669 Start Join Cutback [Double]
     2476 Area per Person [Double]
     2336 Takeoff Length Projection [Double]
     2316 Cross-Section Rotation [Double]
     1904 Width [Double]
     1703 Elevation at Top Survey [Double]
     1703 Elevation at Bottom Survey [Double]
     1699 Associated Level Offset [Double]
     1659 Height [Double]
     1149 Total Bar Length [Double]
     1071 Angle [Double]
== c_mep 124439
    30169 Pressure Drop [Double]
    13361 Velocity Pressure [Double]
    12686 System Type [ElementId]
    11121 Flow [Double]
    10180 Friction [Double]
    10180 Velocity [Double]
     9270 System Classification [String]
     5880 Loss Coefficient [Double]
     4107 Section [Integer]
     3246 Relative Roughness [Double]
     2348 Circuit Description [String]
     2204 Additional Flow [Double]
     1930 Electrical Data [String]
     1627 Friction Factor [Double]
     1016 System Length [Double]
      744 Static Pressure [Double]
      
```

## 2017-2019 geometry fidelity, COMPLETE (c5-geometry, 2026-10-16 evening; fid_table_old.py over fidold/, FID_TABLE_2017_2019.txt; supersedes the 4-file 2017 section above)
Revit 2017-2019 files have no oracle dump: each is compared with the Revit 2020/2021 dump of the SAME model (element ids survive the upgrade). 15 files: rst_basic, rst_advanced, Arch_Link, rme_basic, rme_advanced for each of 2017, 2018, 2019 (rac_advanced 2017/18 has no matching dump). Per year the classes are 99-100% in every row: FamilyInstance 100/100/99% (n 1911/1937/1950), SWall 99%, RoomElem 99%, MEP curves/Ceiling/Floor/Stairs/ProfileRoof 100%. Totals: FamilyInstance 99.8% (n=5798), SWall 99.1%, RoomElem 99.4%.
```
class                      n   ACCURATE   true-off   box-only   (median IoU, median |vol err| where Revit gives Volume)
CurveElem                  6028    100.0%      0.0%      0.0%   iou nan  vol nan%
FamilyInstance             5798     99.8%      0.2%      0.0%   iou 0.991  vol 0.00%
RbsDuctCurve               2400    100.0%      0.0%      0.0%   iou 1.000  vol nan%
RbsPipeCurve               2400    100.0%      0.0%      0.0%   iou 1.000  vol nan%
SWall                      1311     99.1%      0.0%      0.9%   iou 0.977  vol 0.00%
RoomElem                    978     99.4%      0.6%      0.0%   iou 1.000  vol 0.00%
RbsFlexDuctCurve            678    100.0%      0.0%      0.0%   iou 1.000  vol nan%
Ceiling                     402    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
FilledRegion                249    100.0%      0.0%      0.0%   iou 0.000  vol nan%
Floor                       207    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
BaseRailing                 150    100.0%      0.0%      0.0%   iou 0.667  vol nan%
DPart                       135    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
RbsConduitCurve             117    100.0%      0.0%      0.0%   iou 1.000  vol nan%
Stairs                       63    100.0%      0.0%      0.0%   iou 1.000  vol nan%
WallSweep                    51    100.0%      0.0%      0.0%   iou 1.000  vol nan%
CableTray                    51    100.0%      0.0%      0.0%   iou 1.000  vol nan%
AnalyticalModelWall          45    100.0%      0.0%      0.0%   iou 0.000  vol nan%
AnalyticalModelSlab          24    100.0%      0.0%      0.0%   iou 0.000  vol nan%
ShaftOpening                 24    100.0%      0.0%      0.0%   iou 1.000  vol nan%
ExtrusionElem                21    100.0%      0.0%      0.0%   iou 1.000  vol nan%
MassLevelData                18    100.0%      0.0%      0.0%   iou 0.000  vol nan%
ProfileRoof                  18    100.0%      0.0%      0.0%   iou 1.000  vol 0.04%
ContFooting                  12    100.0%      0.0%      0.0%   iou 1.000  vol 0.00%
SiteSurface                   9    100.0%      0.0%      0.0%   iou 1.000  vol nan%
SWallRectOpening              9    100.0%      0.0%      0.0%   iou 1.000  vol nan%
FormElem                      6    100.0%      0.0%      0.0%   iou 1.000  vol nan%
StairsSupport                 6    100.0%      0.0%      0.0%   iou 0.238  vol nan%
Text3dElem                    6    100.0%      0.0%      0.0%   iou 0.957  vol nan%
BlendElem                     6    100.0%      0.0%      0.0%   iou 1.000  vol nan%
FamilyGeomCombination         6    100.0%      0.0%      0.0%   iou 1.000  vol nan%

per year (all classes with >=5 elements with graphics):
CurveElem              2017:100/0/0(n2008) 2018:100/0/0(n2009) 2019:100/0/0(n2011)
FamilyInstance         2017:100/0/0(n1911) 2018:100/0/0(n1937) 2019:99/1/0(n1950)
RbsDuctCurve           2017:100/0/0(n800) 2018:100/0/0(n800) 2019:100/0/0(n800)
RbsPipeCurve           2017:100/0/0(n800) 2018:100/0/0(n800) 2019:100/0/0(n800)
SWall                  2017:99/0/1(n437) 2018:99/0/1(n437) 2019:99/0/1(n437)
RoomElem               2017:99/1/0(n326) 2018:99/1/0(n326) 2019:99/1/0(n326)
RbsFlexDuctCurve  
```

## Parameter reproduction, FINAL #2, all 60 gt4 files (c5-geometry, 2026-10-17; pout_c22 on host1 = rules from the TRAIN split, geometry-derived values on; before = pout_c2g; supersedes the 94.1% table)
ALL 94.5% exact (86.5% before, 94.1% in pout_c9): 2020 95.2, 2021 95.7, 2022 95.7, 2023 95.5, 2024 93.2, 2025 93.2, 2026 92.1; no file below its pout_c9 value. Added since pout_c9: structural Elevation at Top/Bottom (reference level, z offset, justification, section depth), AnalyticalMember releases, hub / reference point Connection Status (enum 2 in 2020-22, 1 in 2023) and Associated Level (nearest level), Location Mark and Column Location Mark (grid names + mm offsets), pipe Invert Elevation, duct fitting Offset Width/Height, tag Leader Line, Referencing Sheet/Detail. Round duct fitting offsets (Diameter/2) were already in the later files of this run (validated: rme_basic 2020 Offset Width 308 of 473 ok).
```
year files    values  before%  exact%  exact+approx%   Double / Integer / String / ElementId exact%   not reproduced: a_lookup b_geom c_mep d_other (% of values)
2020    6   1068534     89.7    95.2     95.3        86.6 / 96.3 / 93.6 / 99.7     1.0 1.9 1.2 0.6
2021    9   1426259     90.6    95.7     95.8        88.0 / 96.5 / 93.7 / 99.7     1.0 1.7 0.9 0.6
2022    9   1438591     90.7    95.7     95.8        88.2 / 96.5 / 93.3 / 99.7     1.0 1.7 0.9 0.6
2023    9   1529686     88.2    95.5     95.6        89.2 / 94.4 / 95.0 / 99.5     1.3 1.5 0.9 0.7
2024    9   1294307     80.1    93.2     93.4        84.1 / 96.9 / 97.2 / 98.4     0.9 2.1 2.3 1.2
2025    9   1105074     79.4    93.2     93.3        84.6 / 95.7 / 96.6 / 98.5     1.2 1.9 1.9 1.6
2026    9   1113559     84.7    92.1     92.3        82.5 / 95.2 / 96.1 / 98.0     1.5 2.0 2.0 2.2
ALL    60   8976010              94.5     94.6
== a_lookup_candidate 100987
     3880 Leader Line [Integer]
     3610 Family and Type [String]
     3354 Connection Status [Integer]
     2914 Sheet Number [String]
     2731 Has Association [Integer]
     2486 Referencing Sheet [String]
     2476 Occupancy Unit [Integer]
     2472 Ways [Integer]
     2374 Export to IFC [Integer]
     2313 Referencing Detail [String]
     1946 Family [String]
     1834 Host [String]
     1699 Moves With Grids [Integer]
     1517 Far Clipping [Integer]
     1470 Rebar Number [String]
     1438 Sheet Name [String]
     1419 Type [ElementId]
     1403 Associated Level [String]
     1368 Structural Material [ElementId]
     1291 Detail Number [String]
     1248 y Justification [Integer]
     1233 Family [ElementId]
     1182 Category [ElementId]
     1124 Type Id [ElementId]
     1124 Family and Type [ElementId]
== b_geom 164049
    46158 Area [Double]
    37536 Volume [Double]
     6951 Length [Double]
     6116 Cut Length [Double]
     4928 Slope [Double]
     4088 End Join Cutback [Double]
     3961 Elevation from Level [Double]
     3876 OffsetHeight [Double]
     3778 Elevation at Top [Double]
     3596 OffsetWidth [Double]
     3333 Perimeter [Double]
     3065 Elevation at Bottom [Double]
     2875 Unconnected Height [Double]
     2669 Start Join Cutback [Double]
     2476 Area per Person [Double]
     2336 Takeoff Length Projection [Double]
     2316 Cross-Section Rotation [Double]
     1904 Width [Double]
     1703 Elevation at Top Survey [Double]
     1703 Elevation at Bottom Survey [Double]
     1659 Height [Double]
     1361 Invert Elevation [Double]
     1149 Total Bar Length [Double]
     1071 Angle [Double]
      953 Display Elevations [Integer]
== c_mep 124439
    30169 Pressure Drop [Double]
    13361 Velocity Pressure [Double]
    12686 System Type [ElementId]
    11121 Flow [Double]
    10180 Friction [Double]
    10180 Velocity [Double]
     9270 System Classification [String]
     5880 Loss Coefficient [Double]
     4107 Section [Integer]
     3246 Relative Roughness [Double]
     2348 Circuit Description [String]
     2204 Additional Flow [Double]
     1930 Electrical Data [String]
     1627 Friction Factor [Double]
     1016 System Length [Double]
      744 Static Pressure [Double]
      462 Reynolds numb
```

## 2026-10-17 (c3-geometry): spline sweeps, twisted lofts, blends (viewer item 23)
Causes (reader, rvt_mesh.tessellate_geometry): (1) `_rect_grid` returned None when the two u-borders of a rectangle loop carry different v samples (zipper rows; the two Hermite halves of a tube swept along a spline: 105-sample loop, u-border rows differ) -> earcut chords + `refine_curved` capped at 2000 triangles -> 2 x 2001 triangles spanning the tube, area 140.9 vs Revit 13.01. (2) A twisted ruled loft side is ONE quad (4 border samples): 2 triangles for a hyperbolic paraboloid.
Fix: `_col_grid` (zipper columns, union of the border u samples when the v-borders differ; border columns keep their own samples so shared edges still weld) and `_subdivide_grid` (1->4 midpoint split of grid triangles until interior edge midpoints are within tol, tol >= border chord error). Measured vs Revit gt_geom (2024 base files, ours / Revit): fam_sweep_spline_path area 12.99/13.01 vol 1.5766/1.5640; fam_blend_twist 38.593/38.593 vol 14.4388/14.4379; fam_blend_rect_circle 29.90/29.91 vol 11.1325/11.1385; fam_sweptblend now closed, area 8.77/8.73, vol 1.0700/1.0608 (+0.9%). Lighting Fixtures: the extra body 1000100000 is a stored mesh (nid >= 10**9), never counted as a solid (volume_by_node), reply posted to the viewer.
Final rules (after regression check on 2024/2026 Facades, 2024 Site, 2020 Residential): `_col_grid` only for ruled/hermite faces, border samples never merged (union columns made T-junctions: revolution volumes -12%, Toposolid collapsed); `_subdivide_grid` only for single-quad ruled grids. RVT_NOCOLGRID=1 disables. Demo smoke test OK.


## Parameter reproduction, FINAL #3, all 60 gt4 files (c3-geometry, 2026-10-17; pout_c26 on host1 = FINAL #2 rules + pipe Fixture Units, Start/End Join Cutback, referencing sheet/detail, duct fitting offsets, Location Mark, Invert Elevation; NOT the room heat-gain / Room Cavity Ratio forced edits made after 08:25)
Overall 94.8% of 8.98M values reproduced (FINAL #2: 94.5%); every year at or above its FINAL #2 value (2020 95.3 / 2021 95.8 / 2022 95.7 / 2023 95.6 / 2024 93.9 / 2025 93.9 / 2026 92.8).
```
year files    values  before%  exact%  exact+approx%   Double / Integer / String / ElementId exact%   not reproduced: a_lookup b_geom c_mep d_other (% of values)
2020    6   1068534     89.7    95.3     95.4        86.9 / 96.3 / 93.6 / 99.7     1.0 1.9 1.2 0.6
2021    9   1426259     90.6    95.8     95.9        88.3 / 96.5 / 93.7 / 99.7     1.0 1.7 0.9 0.6
2022    9   1438591     90.7    95.7     95.9        88.5 / 96.5 / 93.3 / 99.7     1.0 1.7 0.9 0.6
2023    9   1529686     88.2    95.6     95.7        89.6 / 94.4 / 95.0 / 99.5     1.3 1.5 0.9 0.6
2024    9   1294307     80.1    93.9     94.0        86.0 / 96.9 / 97.2 / 98.4     0.9 2.0 2.3 0.7
2025    9   1105074     79.4    93.9     94.0        86.7 / 95.7 / 96.6 / 98.5     1.2 1.8 1.9 1.1
2026    9   1113559     84.7    92.8     93.0        84.6 / 95.2 / 96.1 / 98.0     1.5 1.8 2.0 1.6
ALL    60   8976010              94.8     94.9
```

Validation of the room heat-gain constants + Room Cavity Ratio edits (c3-geometry, 2026-10-17, pout_c28 = same rules as pout_c26 + those edits; 2020 Residential, rst_basic, rme_basic): exact 95.4% -> 95.5% (Double 87.2 -> 87.6), no class got worse; the edits are kept. A full run #4 would add them to the FINAL #3 table (expected +0.1% on the 2020 group).

Door Width/Height from the body (c3-geometry, 2026-10-17; pout_c29 = c26 + rule, 2020 Commercial/Residential + 2023 Arch Link): exact 96.0% -> 96.1% on the 3 files, no regression; Commercial curtain-wall doors 101A-D Height exact, Width approx (PCA axis, 4.5e-5 ft) -> now measured in the instance frame (2.89583 exact in a probe on 191870/191872/191880; not re-run through the params pipeline).

Residual review (c3-geometry, 2026-10-18, from fidfull9): (1) Plumbing 2024 FamilyInstance: 398 of 400 elements within 2% volume (2 outliers: a 0.0020 ft3 part -5.5%, element 1389546 -3.2%), the old "pipe fittings ~4% low" is no longer visible. (2) Text3dElem 13 elements: IoU 0.941-0.987 against Revit's stored element bbox (2 below 0.95 only because Revit's BB for model text is not the glyph hull); the oracle solid of the Commercial 'Pharmacy' signs matches exactly (volume 38.1535, area 229.803, 564 faces), so the 76.9% line is a bbox artefact, not a geometry error. (3) Toposolid 2026 Site 1264746 (10.6M ft3): mesh is open (582 boundary edges among 4,700 small planar side faces), volume -2.3%; the 2025 version is closed at -0.8%. Single element, documented residual.


## Parameter reproduction, FINAL #4, all 60 gt4 files (c3-geometry, 2026-10-18; pout_c30 on host1 = FINAL #3 + room heat-gain constants / Room Cavity Ratio + door Width/Height from the body + the 2026-10-17 mesh changes)
Overall 94.9% of 8.98M values exact (FINAL #3 94.8%, FINAL #2 94.5%); per year 2020 95.4 / 2021 95.9 / 2022 95.8 / 2023 95.7 / 2024 93.9 / 2025 93.9 / 2026 92.8, none below FINAL #3.
```
year files    values  before%  exact%  exact+approx%   Double / Integer / String / ElementId exact%   not reproduced: a_lookup b_geom c_mep d_other (% of values)
2020    6   1068534     89.7    95.4     95.5        87.3 / 96.3 / 93.6 / 99.7     1.0 1.8 1.2 0.5
2021    9   1426259     90.6    95.9     96.0        88.6 / 96.5 / 93.7 / 99.7     1.0 1.7 0.9 0.5
2022    9   1438591     90.7    95.8     95.9        88.8 / 96.5 / 93.3 / 99.7     1.0 1.7 0.9 0.5
2023    9   1529686     88.2    95.7     95.8        89.8 / 94.4 / 95.0 / 99.5     1.3 1.5 0.9 0.6
2024    9   1294307     80.1    93.9     94.0        86.0 / 96.9 / 97.2 / 98.4     0.9 2.0 2.3 0.7
2025    9   1105074     79.4    93.9     94.0        86.7 / 95.7 / 96.6 / 98.5     1.2 1.8 1.9 1.1
2026    9   1113559     84.7    92.8     93.0        84.6 / 95.2 / 96.1 / 98.0     1.5 1.8 2.0 1.6
ALL    60   8976010              94.9     95.0
```

Host (String) rules (c3-geometry, 2026-10-18): FamilyInstance whose host is a Toposolid -> 'Sub-Division' (Snowdon Site 2024: 43/43 missing values now ok, pout_c32 vs pout_c30, no other row changed; same 43 in 2025/2026). No host and no associated level -> 'None' (Snowdon Electrical: 392 per year in the oracle; validation of that rule in pout_c32 Electrical 2024 pending).
Validated (pout_c32, Snowdon Electrical 2024): the 'None' rule fixes all 392 missing Host values (ok 182,580 -> 182,972 of 193,273 values, no row changed otherwise). Both Host rules stay; they are in the next full run (not yet in FINAL #4's 94.9%: expected +0.3% on the 2024-2026 Electrical / Site files).

### 2026-10-18 (c6-geometry, continuation of c3) 
* par33 (Rebar Number from m_cellList.m_schemaId2SubelemIdNumbers, rvt_params._rebar_number) validated on rst_basic 2020 / rst_advanced 2020 + 2023 (pout_c33 vs pout_c30, same 3 files): 94.9 -> 95.0% exact, Rebar Number [String] 368 not-reproduced -> 0, no row worse. KEPT (RVT_NORBN=1 disables).
* rvt_geometry.wall fills bbox for analytic walls (edit-lab add_wall walls).
* 2026-10-18 (c6-geometry) new param rules, each validated with pq.sh/pdiff.py (non-geometry probe vs pout_c30full, only the named param changes): IndependentTag Leader Type from m_leaderEndCondition (+220 on 2024/25 Electrical), Leader Line for the inline m_taggedEntitiesCell (2024) and the 2025 m_cellList m_references layout fills only when no stored value (+1002, 0 worse), FamilyInstance Enable Analytical Model from the cell (+40/415), ElementGroup Type/Type Id/Family/Family and Type = group id (+77), SpotElevation Leader from leader-segment offsets (+313, -1), RoomElem Room Name/Number = Name/Number (+60/+54 of 87 in rme_basic), uint32-max ints -> -1 (RoomElem Occupancy Unit +165 per file). Full run #4b = pout_c34 queued (h1retry par34).
* 2026-10-18 (c6-geometry, later) view/sheet params: a DBView with a viewport whose sheet did not resolve now reports Sheet Number '---' (+91 on rme_basic 2020 + Snowdon Electrical 2025: DBViewPlan +52, DBViewSection +19, DBView3d +17); view markers get Sheet Name = their view's sheet name or '---' (+17, -3 Section/Viewer3d). Open: Viewport 'Sheet Name' is Revit's literal 'Unnamed' in rme_basic (434396), Referencing Sheet/Detail and Associated Level of markers.
* 2026-10-18 marker (Viewer/Section) Associated Level = target view's level: +91 (rme_basic 2020 + Snowdon Electrical 2025), 0 worse.
* rvt_geomparams._drop_form_nodes: only nodes with index > 0 are dropped (2024+ Electrical Fixtures/Lighting Devices: 470+196 families [flagged, plain] were wrong; 25/25 now; 2020/2023 rme_basic unchanged).
* rvt_geomparams: Plumbing Equipment (-2008234) Volume/Area from the Medium mesh in 2026 files too (15/15 vs 0/15 Fine, Snowdon Plumbing 2026).
* 2026-10-18 framing 'z Offset Value' / 'y Offset Value' = first entry of the beam cell's m_zOffsets / m_yOffsets (Snowdon Structural 2024: z Offset Value 795 -> 942 of 942 exact, 0 worse). (Not in par34, which started earlier.)
* 2026-10-18 structural framing Cut Length = extent of the solid along the straight location curve (rvt_geomparams): rst_basic 2020 +370 values, 0 worse (probe with geometry on: net +803 of 130604 incl. the other new rules).
* 2026-10-18 FamilyInstance without a level (m_assocLevelId invalid) reports Elevation from Level 0.0: +385 on rst_basic/rme_basic/Commercial 2020, 0 worse (must be applied at the very end: fam_instance writes the bare key later).
* 2026-10-18 SWall Unconnected Height of a level-constrained wall = (top level + top offset) - (base level + base offset): +299 on rme_basic/Commercial/Residential 2020 + Snowdon Structural 2024, 0 worse.
* 2026-10-18 rvt_viewdisp.view_clip + params Far Clipping / Far Clip Offset / Crop View (section/elevation depth + crop; all verified 2020-2025); pdiff: Far Clipping +64 on 2 files, 0 worse.
* 2026-10-18 pipe/duct Slope sign: Revit's Slope = (start z - end z) / horizontal run (positive when the run descends from its start): RbsDuctCurve +71, RbsPipeCurve +3 on rme_basic 2020 + Snowdon HVAC 2024, 0 worse (rvt_geom.mep_curve).
* 2026-10-18 RoomElem Area/Perimeter: floor face = the largest horizontal face of the room solid (floor or ceiling) instead of whatever touches the lowest z: Area +38, Perimeter +19 on rme_basic/Commercial/Residential 2020 + Arch_Link 2023, 0 worse (rvt_geomparams.room_params).
* 2026-10-18 round ducts (size string with ø): Area = pi d L, Diameter instead of Width/Height: RbsDuctCurve Area +1054 on rme_basic 2020 + Snowdon HVAC 2024, 0 worse (rvt_geom.mep_curve).
* 2026-10-18 centre lines take the owner run's Area (override, own slot stale): SegmentCenterLine Area +1235; pipe Slope +98 on Snowdon Plumbing 2024.
* 2026-10-18 centre lines also take the owner run's Slope: SegmentCenterLine Slope +1117 (rme_basic 2020 + Snowdon HVAC/Plumbing 2024), 0 worse.
* 2026-10-18 pipe/duct engine results straight from m_pDesignPropManager (Flow, Additional Flow, Velocity, Friction, Pressure Drop, Velocity Pressure, Loss Coefficient, Hydraulic/Equivalent Diameter, Reynolds Number): +3945 on rme_basic 2020 + Snowdon HVAC/Plumbing 2024, 0 worse.
* 2026-10-18 centre lines inherit Additional Flow (+765) and Loss Coefficient (+8) from the owner run; inheriting Pressure Drop / Reynolds made them WORSE (-1938 / -2485: the centre lines keep their own values), so only those four (Area, Slope, Additional Flow, Loss Coefficient) are overridden.
* 2026-10-18 MEP Section from the connectors' modifier m_nSection: RbsDuctCurve +646, flex +4 (rme_basic 2020 + Snowdon HVAC 2024), 0 worse.
* 2026-10-18 pipe/duct System Type = dpm.m_idSystemType (SegmentCenterLine +232, RbsDuctCurve -45: ducts whose learned slot was already right; net +187 on rme_basic 2020 + Snowdon HVAC/Plumbing 2024). Open: those 45.
* 2026-10-19 rvt_geomparams: Balusters (-2000127) Volume/Area use only the symbol nodes present at Coarse detail (Arch_Link 2022 25/25 at 2e-3 vs 17/25; no other category changed: Duct Fittings got worse so the filter is baluster-only).

### 2026-10-19 fidelity table refresh (campaign r1, c6-fidtables, 51 of 60 gt4 files, final code): FamilyInstance 99.8%, SWall 99.2%, RoomElem 99.4%, every other class >= 99.9% ACCURATE (unchanged vs FID_TABLE_FINAL.txt, which stays the per-class/per-year table of record). Ranked residuals and my verdicts: NEEDS-FROM-READER.md (c6-fidtables items 1-6): 2022 balusters fixed in the parameter path (Coarse-node rule), 4 SWalls are exact by Area (stale header bbox), 3 CurveElem rows are 2D detail components, RoomElem 576007 / 159906 not resolvable from the saved graphics. Full tables: fid-campaign/RESULTS.md.
* 2026-10-19 beam y/z/yz Justification from the cell's m_yJustification[0] / m_zJustification[0] / m_yzJustification: +602 y, +130 z on rst_advanced 2020/2023 + Snowdon Structural 2024, 0 worse.
* 2026-10-19 Has Association: AnalyticalMember always 1; FamilyInstance = its Enable Analytical Model: +600 / +484 on rst_basic+rst_advanced 2020 and rst_advanced 2023, 0 worse.
* 2026-10-19 Revit 2025+ renamed the electrical loads (Apparent/True Load -> Apparent/True Power, also Branch Circuit / Feed Through Lugs variants): aliases added for files >= 2025: +6409 on Snowdon Electrical 2025 alone (x2 with 2026), 0 worse. LOOK FOR MORE RENAMES BETWEEN VERSIONS.
* 2026-10-19 structural framing Length from the location curve (+12 rst_basic 2020) and, in Revit 2026 files, 'Length' is named 'System Length' (+885 on Snowdon Structural 2026), 0 worse.
* 2026-10-19 2025+/2026 constants and renames: Sheet Collection / Referencing Sheet Collection -1 (2025+), Saved Position -1 / View Anchor 0 (2026), OmniClass -> Classification (2026), electrical circuit Core Type 0 / Circuit State 0 (2026): checked on Snowdon Electrical 2025/2026 (all ok; most were already covered by the learned defaults, +16 net).
* 2026-10-19 static check of the untested _CONST_PARAMS rules against gt4 (all files): Wire Export to IFC 0 (3398 of 3398), SpotDimension Display Elevations 1 (945 of 953), Duct Lining/Insulation Thickness 0 (all), Dimension Label -1 (all), Viewer3d Parts Visibility 1 (526 of 547 view 3D rows; 21 are 0/2 and will be wrong). Probe pqconst still queued (host1 memory).

### 2026-10-19 parameter reproduction, run #4b (pout_c34; 53 of 60 gt4 files, stopped externally at 02:00; code of 2026-10-18 evening = FINAL #4 + Host/None rules, Rebar Number from the cell list, IndependentTag Leader Type/Line, Enable Analytical Model, ElementGroup type ids, SpotElevation Leader, Room Name/Number, uint32 max -> -1, Sheet Number '---', marker Sheet Name / Associated Level; NOT the later MEP / beam / justification / rename rules)
Exact 95.4% of 8,129,228 values (exact+approx 95.5%); per year 2020 95.6, 2021 96.2, 2022 96.2, 2023 96.0, 2024 94.3 (7 of 9 files), 2025 94.7 (6 of 9), 2026 93.5 (7 of 9). Table: PARAM_REPORT_c34_partial.txt. Run #5 (par35, all rules of 2026-10-18/19, 60 files) is queued.
* 2026-10-19 view Family / Type / 'Family: Type' / plural strings (GT ids -1139999 Family, -1012109 plural, -1139997 Type, -1139998 'Family: Type', -1012106 'Plurals (Type)') from the view's m_dbViewTypeId -> DBViewType.m_systemFamilyIdx (table _VIEW_FAMILY, 13 indexes from 2020 Commercial + rst_basic) and the system default type name (_VIEW_TYPE_DEFAULT; the type's own name is not in its record, so custom-named view types stay unresolved): +60 on rst_basic 2020 (DBViewPlan Family and Type +16, DBView3d Family +12, Schedule +10, Drafting +8 ...), 0 worse. NOTE: a single small file (rst_basic 2020, ~100 s) runs fine on host3 as ALLOW_HOST3=1 systemd-run --user --scope -p MemoryMax=1500M ... python3 eval_params_all.py (no geometry), usable while host1 is blocked.
* 2026-10-19 Rebar Bend Diameter / Standard Bend Diameter = the bar type's m_standardBendDiam, or m_stirrupTieBendDiam when the rebar shape's m_style is 1: +244 on rst_basic 2020 (122 of 122), 0 worse.
* 2026-10-19 AnalyticalModelColumn (2020-2022) Base/Top Release, Fx..Mz from m_startReleases / m_endReleases: +203 on Commercial 2020 (29 columns x 7), 0 worse.
* 2026-10-19 defaults when absent: SketchGrid Work Plane Grid Spacing 0, SWall Location Line Offset 0, WallSweep Offset From Level 0, FamilySymbol CWFU/WFU/HWFU/Apparent Load 0: +79 on Commercial 2020, 0 worse.
* 2026-10-19 FamilySymbol Assembly Description from the Assembly Code via assembly_desc.json (46 unambiguous codes from the corpus): +31 Residential 2020 (all 31), 0 worse.
* 2026-10-19 Rebar Model Bar Diameter (2022+) = bar type m_barModelDiameter (+122 rst_basic 2023); AnalyticalMember Has Association = 1 iff the file's physical members have it (rst_basic 2023 +90); replaces the unconditional AM=1 rule.
* 2026-10-19 Has Association also for AnalyticalPanel; AnalyticalMember 600/600 on rst_advanced 2023 (+600, the earlier unconditional rule was wrong on rst_basic 2023).
* 2026-10-19 defaults when absent (checked on Arch_Link 2021): RoomElem load densities / Occupancy Unit 0, FamilySymbol Analytic Construction '<None>', SketchGrid Work Plane Grid Spacing -1 (was wrongly 0; -1 in 98% of the corpus): +668 on Arch_Link 2021, 0 worse.
* 2026-10-19 type records: DBViewType Default Reference Label (m_refLabelStr); compound-structure types (BasicWallType / FloorAttributes / RoofAttributes / CeilingAttributes): Default Thickness / Width = sum of layer widths, Structural Material = the structure layer's material (Construction 2026 template +38 incl. BasicWallType Structural Material +18).
* 2026-10-19 analytical Hub / ReferencePoint Connection Status = 2 when a connector holds two references, else 0 (34 of 38 on Residential 2020; the 4 outliers have one reference but status 2).
2026-10-19 Has Association FamilyInstance rule fixed: only override when cell key 'Enable Analytical Model|Integer' present (learned enum put a stale bare 1); rst_basic 2023 +102 (AnalyticalMember/Panel), rst_advanced 2023 unchanged, nothing worse (pout_h23). Full run par35c still gated on host1 (3.8 GB free, VMs).
2026-10-19 face materials re-verified on host3 (own venv ~/rvt-env-h3): 52 oracle elements, 49 identical sets, 3 superset (ours has extra faces with default material 24/18437 on 155712 Commercial, 493612/493879 rst_basic; Revit lists 6 faces vs our 12; no volume effect). 0 'other'.
