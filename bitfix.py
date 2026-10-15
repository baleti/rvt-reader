import olefile,zlib,sys
sys.path.insert(0,'/home/user1/rvt-research')
import fmt_parser as fp
def tobits(b): return ''.join(f'{c:08b}'[::-1] for c in b)   # LSB-first per byte
def frombits(s):
    s+= '0'*((-len(s))%8)
    return bytes(int(s[i:i+8][::-1],2) for i in range(0,len(s),8))
def score(out):
    pr=fp.P(out,(6,4,6)); pr.p=2
    try:
        while pr.p<len(out): pr.record()
    except Exception: pass
    return len(pr.classes)
if __name__=='__main__':
    b=olefile.OleFileIO('/home/user1/rvt-research/F106-LAC724-MOD-AR-00061.rvt').openstream('Formats/Latest').read()
    pre=b[:10]; body=b[10:]
    bits=tobits(body); base=(64896-10)*8
    res=[]
    for P in range(base-48,base+48):
        for k in list(range(-16,0))+list(range(1,17)):
            nb= bits[:P]+bits[P+k:] if k>0 else bits[:P]+('0'*(-k))+bits[P:]
            d=zlib.decompressobj(-15)
            try: out=d.decompress(frombits(nb))
            except zlib.error: continue
            if len(out)<141200: continue
            res.append((score(out),k,P-base,len(out)))
    res.sort(reverse=True); print(res[:10])
