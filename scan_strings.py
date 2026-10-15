import re,struct,collections,sys
PR=re.compile(rb'(?:[\x20-\x7e]\x00){2,}')
def records(b):
    """yield (offset, tag, text) for [u32 tag][u32 nchars][utf16] records"""
    for m in PR.finditer(b):
        s=m.start()
        if s<8: continue
        L=struct.unpack_from('<I',b,s-4)[0]; run=(m.end()-s)//2
        if 1<=L<=run:
            yield s-8, struct.unpack_from('<I',b,s-8)[0], b[s:s+2*L].decode('utf-16le')
if __name__=='__main__':
    b=open(sys.argv[1],'rb').read()
    tags=collections.defaultdict(list)
    for off,tag,txt in records(b): tags[tag].append((off,txt))
    print(len(tags),'distinct tags;',sum(len(v) for v in tags.values()),'records')
    for tag,v in sorted(tags.items(),key=lambda kv:-len(kv[1]))[:40]:
        print(f"tag={tag:#010x} n={len(v):6}", [t for _,t in v[:5]])
