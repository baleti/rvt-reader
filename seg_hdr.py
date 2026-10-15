import sys,zlib,olefile,struct,collections
sys.path.insert(0,"/home/user1/rvt-research")
import rvt2text as T
f,pn=sys.argv[1],sys.argv[2]
o=olefile.OleFileIO(f); data=T.strip_pages(o.openstream(pn).read()); GZ=T.GZ
pos=0; last_end=0; n=0; chans=collections.Counter()
while True:
    i=data.find(GZ,pos)
    if i<0: break
    d=zlib.decompressobj(-15)
    try: out=d.decompress(data[i+10:])
    except zlib.error: pos=i+4; continue
    end=len(data)-len(d.unused_data)
    gap=data[last_end:i]
    if n<6 or (len(gap)>100 and n<40): print('seg',n,'gap',len(gap),gap.hex(' ')[:300],'| decoded',len(out),'| gz start at',i)
    n+=1; last_end=end; pos=end
print(n)
