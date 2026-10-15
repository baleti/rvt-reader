"""Publish the fid_table.py result (current best row per element across fidfull*/): FID_TABLE_FINAL.txt, a dated section in NOTES.md and the headline line of GEOMETRY_API.md.
usage: publish_fid_table.py 'note on code/date'"""
import subprocess,sys,re,datetime
note=sys.argv[1] if len(sys.argv)>1 else ''
out=subprocess.run(['python3','fid_table.py','5','-y'],capture_output=True,text=True,cwd='/home/user1/rvt-research').stdout
open('FID_TABLE_FINAL.txt','w').write(out)
m=re.search(r'^FamilyInstance\s+(\d+)\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%',out,re.M)
acc={r.group(1):float(r.group(2)) for r in re.finditer(r'^(\w+)\s+\d+\s+([\d.]+)%',out,re.M)}
d=datetime.date.today().isoformat()
head=('FamilyInstance %s%% accurate / %s%% true-off / %s%% box-only over %s placed instances, SWall %s%%, Ceiling %s%%, Floor %s%%, RoomElem %s%%, ProfileRoof %s%%, SiteSurface %s%%, Toposolid %s%%'
      %(m.group(2),m.group(3),m.group(4),m.group(1),acc.get('SWall'),acc.get('Ceiling'),acc.get('Floor'),acc.get('RoomElem'),acc.get('ProfileRoof'),acc.get('SiteSurface'),acc.get('Toposolid'))) if m else ''
open('NOTES.md','a').write('\n## FINAL per-class / per-year geometry table, refreshed %s (c5-geometry; replaces the 2026-10-14 table; %s)\nfid_table.py over the newest row per file (fidfull9 = final code of 2026-10-15 where present). SiteSurface is classed as a flat sheet (topography surface: mesh area equals Revit Surface Area exactly, 2020 Commercial 16201.727).\n```\n%s\n```\n'%(d,note,out))
g=open('GEOMETRY_API.md').read()
line='## Final per-class/per-year table (%s): see NOTES.md "FINAL per-class / per-year geometry table, refreshed %s" (FID_TABLE_FINAL.txt). Headline for the viewer: %s.\n'%(d,d,head)
g=re.sub(r'^## Final per-class/per-year table \(2026-10-14\).*\n',lambda _:line,g,flags=re.M) if re.search(r'^## Final per-class/per-year table \(2026-10-14\)',g,re.M) else g+'\n'+line
open('GEOMETRY_API.md','w').write(g); print(head)
