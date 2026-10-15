import sys,zlib,olefile
sys.path.insert(0,"/home/user1/rvt-research")
import rvt2text as T
f,pn=sys.argv[1],sys.argv[2]
o=olefile.OleFileIO(f); st=o.openstream(pn).read(); data=T.strip_pages(st)
GZ=T.GZ; pos=0; gaps=[]; errs=0; mem=0; tot_out=0; last_end=0
while True:
    i=data.find(GZ,pos)
    if i<0: break
    d=zlib.decompressobj(-15)
    try: out=d.decompress(data[i+10:])
    except zlib.error: errs+=1; pos=i+4; continue
    if i>last_end: gaps.append((last_end,i-last_end))
    end=len(data)-len(d.unused_data); mem+=1; tot_out+=len(out); last_end=end; pos=end
if len(data)>last_end: gaps.append((last_end,len(data)-last_end))
print(pn,'stored',len(st),'stripped',len(data),'members',mem,'zlib errors',errs,'decoded bytes',tot_out)
import collections
print('gaps',len(gaps),'total gap bytes',sum(g for _,g in gaps),collections.Counter(g for _,g in gaps).most_common(5))
big=[g for g in gaps if g[1]>1000][:5]; print('big gaps',big)
