"""Minimal pure-Python inflate that logs block structure. Debug tool for Revit's non-matching deflate streams."""
import struct,sys
LBASE=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258]
LEXT=[0]*8+[1]*4+[2]*4+[3]*4+[4]*4+[5]*4+[0]
DBASE=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577]
DEXT=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13]
class BR:
    def __init__(s,b): s.b=b; s.pos=0   # bit position
    def bits(s,n):
        v=0
        for i in range(n):
            byte=s.b[s.pos>>3]; v|=((byte>>(s.pos&7))&1)<<i; s.pos+=1
        return v
def build(lengths):
    cnt={}; 
    for l in lengths:
        if l: cnt[l]=cnt.get(l,0)+1
    code=0; nxt={}; 
    for l in range(1,16): code=(code+cnt.get(l-1,0))<<1; nxt[l]=code
    tbl={}
    for sym,l in enumerate(lengths):
        if l: tbl[(l,nxt[l])]=sym; nxt[l]+=1
    return tbl
def decode(br,tbl):
    code=0; l=0
    while True:
        code=(code<<1)|br.bits(1); l+=1
        if (l,code) in tbl: return tbl[(l,code)]
        if l>15: raise ValueError('bad huffman')
def inflate(b,log=None,maxblocks=10**9):
    br=BR(b); out=bytearray(); n=0
    while n<maxblocks:
        start_in=br.pos; start_out=len(out)
        final=br.bits(1); typ=br.bits(2)
        if typ==0:
            br.pos=(br.pos+7)&~7; L=br.bits(16); NL=br.bits(16)
            for _ in range(L): out.append(br.bits(8))
        else:
            if typ==1:
                ll=[8]*144+[9]*112+[7]*24+[8]*8; dl=[5]*30
            else:
                hlit=br.bits(5)+257; hdist=br.bits(5)+1; hclen=br.bits(4)+4
                order=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]; cl=[0]*19
                for i in range(hclen): cl[order[i]]=br.bits(3)
                ct=build(cl); ls=[]
                while len(ls)<hlit+hdist:
                    s=decode(br,ct)
                    if s<16: ls.append(s)
                    elif s==16: ls+= [ls[-1]]*(3+br.bits(2))
                    elif s==17: ls+=[0]*(3+br.bits(3))
                    else: ls+=[0]*(11+br.bits(7))
                ll=ls[:hlit]; dl=ls[hlit:]
            lt=build(ll); dt=build(dl)
            while True:
                s=decode(br,lt)
                if s<256: out.append(s)
                elif s==256: break
                else:
                    s-=257; L=LBASE[s]+br.bits(LEXT[s]); d=decode(br,dt); D=DBASE[d]+br.bits(DEXT[d])
                    if D>len(out): raise ValueError(f'dist {D} > out {len(out)} at in-bit {br.pos}')
                    for _ in range(L): out.append(out[-D])
        if log is not None: log.append((n,typ,final,start_in>>3,br.pos>>3,start_out,len(out)))
        n+=1
        if final: break
    return bytes(out),(br.pos+7)>>3
if __name__=='__main__':
    import olefile
    o=olefile.OleFileIO(sys.argv[1]); b=o.openstream(sys.argv[2]).read()
    log=[]; out,used=inflate(b[10:],log)
    print('out',len(out),'in used',used)
    for r in log: print('blk %d type=%d final=%d in=%d..%d out=%d..%d'%r)
