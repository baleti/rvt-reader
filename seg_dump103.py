import sys,zlib,olefile,struct
sys.path.insert(0,"/home/user1/rvt-research")
import rvt2text as T
f,pn,chan,k=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
o=olefile.OleFileIO(f); data=T.strip_pages(o.openstream(pn).read()); GZ=T.GZ
pos=0; last_end=0; n=0
while True:
    i=data.find(GZ,pos)
    if i<0: break
    d=zlib.decompressobj(-15)
    try: out=d.decompress(data[i+10:])
    except zlib.error: pos=i+4; continue
    end=len(data)-len(d.unused_data); gap=data[last_end:i]
    if len(gap)>=8 and struct.unpack_from('<Q',gap,len(gap)-8)[0]==chan:
        if n==k:
            print('gap',gap.hex(' ')); print(len(out)); print(out[:900].hex(' ')); break
        n+=1
    last_end=end; pos=end
