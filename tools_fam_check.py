import sys, glob, os, re, collections; sys.path.insert(0,'/home/user1/rvt-research')
import rvt_elemmesh as EM, rvt_mesh as M
for g in sorted(glob.glob('gt_geom/*_fam_*.tsv')):
    f='rosetta/'+os.path.basename(g)[:-4]+'.rte'; d=EM.Doc(f)
    gt=collections.defaultdict(lambda:[0,0])
    for l in open(g):
        if l.startswith('G\t'):
            p=l.split('\t'); e=int(p[1].split('.')[0]); kv=dict(x.split('=',1) for x in p[2:] if '=' in x)
            gt[e][0]+=float(kv['volume']); gt[e][1]+=float(kv['area'])
    for e,(gv,ga) in gt.items():
        m=EM.element_mesh(d,e)
        v,c,a,n=M.volume_by_node(m['tris'],m.get('meta'),m.get('nid'),fid=m.get('fid')) if m['tris'] else (0,0,0,0)
        print('%-40s %d  vol %.4f/%.4f (%.2f%%)  area %.4f/%.4f (%.2f%%) %s'%(os.path.basename(g)[:-4],e,v,gv,100*(v-gv)/gv if gv else 0,a,ga,100*(a-ga)/ga if ga else 0,m['flags']))
