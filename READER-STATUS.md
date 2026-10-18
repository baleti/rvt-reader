# Reader status (c5-geometry), 2026-10-16

## Geometry (ACCEPTANCE.md): FID_TABLE_FINAL.txt, NOTES.md "FINAL per-class / per-year geometry table, refreshed 2026-10-16"
Corpus 2020-2026 (60 of 61 gt4 files, final code): FamilyInstance 99.5% accurate (14,435 placed), SWall 99.3%, RoomElem 99.4%, Ceiling/Floor/ProfileRoof/SiteSurface/MEP curves 100%, Toposolid 97.6% (2026 Site toposolid: open mesh, 2.3% low volume, documented residual), Text3dElem 76.9% of 13 (one element, IoU 0.94 < 0.95).
2017-2019: 15 files vs the 2020/21 dump of the same model (FID_TABLE_2017_2019.txt): FamilyInstance 99.8% (n=5798), SWall 99.1%, RoomElem 99.4%, all other classes 100%. Not covered: rac_advanced (no matching dump).
Speed: rvt_mesh.face_loops_uv quadratic edge scan fixed (_face_edges): 2024 Site 51.5 s -> 11.1 s on 7 elements, meshes identical.

## Parameters (OBJECTIVES.md #2): NOTES.md "Parameter reproduction, FINAL, all 60 gt4 files"
94.9% of 8.98M values exact (86.5% before); per year 2020 95.4, 2021 95.9, 2022 95.8, 2023 95.7, 2024 93.9, 2025 93.9, 2026 92.8 (pout_c30, FINAL #4).
Included in the final table: structural Elevation, AnalyticalMember releases, hub/reference-point status + levels, Location Mark (467/499), Column Location Mark (199/203), pipe Invert Elevation (484/491), duct fitting offsets; earlier single-file numbers: structural Elevation at Top/Bottom, AnalyticalMember releases, hub/reference-point Connection Status + Associated Level, Location Mark (467/499), Column Location Mark (199/203), pipe Invert Elevation (484/491): rst_basic 2020 96.6%, rst_advanced 2023 93.95%, rme_basic 2020 94.86%.
Deliberately absent (better missing than wrong): duct fitting Area, room Volume, some curtain-panel Area, Fixture Units, duct Pressure Drop / Loss Coefficient.
Open (largest first): Fixture Units 19.7k and MEP engine values (Pressure Drop 30k, Velocity Pressure, Flow, Friction, Velocity), Area/Volume of MEP/curtain families (46k/37k mixed), Cut Length 6k, Has Association 2.7k, tag Leader Line 3.9k (mostly 0), Sheet Number/Referencing Sheet 5.4k, Occupancy Unit 2.5k, electrical Ways/Number of Elements, RebarInSystem Total Bar Length (approx).

## How to re-run
Single file: RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=<dir> python eval_params_all.py corpus/<y>/<file> gt4/<y>_<file>.tsv ; table: python3 param_report.py pout_c2g <dir> 40
Geometry: python3 publish_fid_table.py "<note>" after fidelity_full.py runs (fid_h1c.sh). Everything heavy runs on host1 via ~/.local/share/offload/h1run (queue in ~/demo-state/H1-QUEUE.md); host3 only tiny single-file checks (MemoryMax 1.5G).
Data files used by rvt_params: omniclass_titles.json, conceptual_construction_names.json (not in the allow-listed GitHub mirror: the reader falls back to empty tables).
