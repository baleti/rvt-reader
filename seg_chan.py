import sys,zlib,olefile,struct,collections
sys.path.insert(0,"/home/user1/rvt-research")
import rvt2text as T
f,pn=sys.argv[1],sys.argv[2]
o=olefile.OleFileIO(f); data=T.strip_pages(o.openstream(pn).read()); GZ=T.GZ
pos=0; last_end=0; ch=collections.Counter(); byt=collections.Counter(); ex={}
while True:
    i=data.find(GZ,pos)
    if i<0: break
    d=zlib.decompressobj(-15)
    try: out=d.decompress(data[i+10:])
    except zlib.error: pos=i+4; continue
    end=len(data)-len(d.unused_data)
    gap=data[last_end:i]
    if len(gap)>=8:
        c=struct.unpack_from('<Q',gap,len(gap)-8)[0]; ch[c]+=1; byt[c]+=len(out); ex.setdefault(c,(len(gap),gap.hex(' ')[:120],out[:48].hex(' ')))
    last_end=end; pos=end
for c,n in ch.most_common(): print('channel',c,'segments',n,'decoded bytes',byt[c],ex[c])
