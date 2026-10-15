import json,glob,collections,sys,re
GEOM={'Area','Volume','Length','Perimeter','Slope','Width','Height','Depth','Thickness','Radius','Diameter','Offset','Angle','Cut Length','Elevation','Cross-Section Rotation','Unconnected Height','Base Offset','Top Offset','Sill Height','Head Height'}
MEP={'Flow','Pressure Drop','Velocity','Friction','Reynolds number','Loss Coefficient','Velocity Pressure','System Name','System Classification','System Type','Hydraulic Diameter','Equivalent Diameter','Additional Flow','Overall Size','Size','Calculated Size','Relative Roughness','Roughness','Pressure','Voltage','Load','Power','Current','Number of Poles','Apparent Load','Panel','Circuit Number','Circuit Name','Electrical Data','Flow Direction','Flow State','Section','Demand','System Abbreviation'}
LOOKUP={'Category','Family Name','Type Name','Family','Type','Design Option','Phase Created','Phase Demolished','Workset','Edited by','Host Id','Room','Space','Level','Reference Level','Schedule Level','Base Constraint','Top Constraint','Mark','Comments','Type Mark','Type Comments','Assembly Code','Assembly Description','Description','Manufacturer','Model','URL','Keynote','Fire Rating','Structural Usage','Image','Phase','Created Phase','Demolished Phase','View Template','Sheet Number','Sheet Name','Name','Code','Material','Cost','Mirrored','Moves With Nearby Elements','Enable Analytical Model','Room Bounding','Top Is Attached','Base Is Attached','Function','Structural','Location Line','Related to Mass','Rotation','Orientation'}
def bucket(nm,stg):
    base=re.sub(r'\s*\(.*\)$','',nm)
    if base in MEP or any(w in nm for w in ('Flow','Pressure','System','Velocity','Friction','Circuit','Voltage')): return 'c_mep'
    if base in GEOM or any(w in nm for w in ('Elevation','Offset','Area','Volume','Length','Extension','Cutback','Perimeter','Slope')): return 'b_geom'
    if stg in('String','ElementId','Integer') or base in LOOKUP: return 'a_lookup_candidate'
    return 'd_other'
files=sorted(glob.glob('pout/*.json'))
tot=collections.Counter(); byy=collections.defaultdict(lambda:collections.Counter()); un=collections.defaultdict(collections.Counter); stor=collections.defaultdict(collections.Counter)
for f in files:
    d=json.load(open(f)); y=re.match(r'(\d{4})',open(f).name[0:0] or f.split('/')[-1]).group(1) if False else None
    fn=d['file']
    # year from corpus path unknown in file name; look up gt file
    for k,n in d['rows']:
        cls,gcls,pid,nm,stg,st=k
        yr=d.get('year')
        tot[st]+=n; stor[stg][st]+=n
        if st!='ok': un[bucket(nm,stg)][(nm,stg)]+=n
print('files',len(files),dict(tot))
for s,c in stor.items(): print(s,dict(c), 'ok%% %.1f'%(100*c['ok']/max(1,sum(c.values()))))
for b,c in sorted(un.items()):
    print('==',b,sum(c.values()))
    for (nm,stg),n in c.most_common(int(sys.argv[1]) if len(sys.argv)>1 else 30): print('  %7d %s [%s]'%(n,nm,stg))
