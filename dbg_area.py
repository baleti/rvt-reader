import sys; sys.path.insert(0,'/home/user1/rvt-research')
import rvt_params as RP
p=RP.params(sys.argv[1],geom=True)
for e in map(int,sys.argv[2:]):
    o=p[e]; print(e,o['class'],{k:v for k,v in o['params'].items() if k.split('|')[0] in('Area','Volume','Category')})
