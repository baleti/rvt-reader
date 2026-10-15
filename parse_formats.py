#!/usr/bin/env python3
"""Tolerant tokenizer for the decompressed Formats/Latest stream (Revit class schema).
Class record: u16 len + name. Field: u32 len + name. Nested/inline class definitions are preceded by a u16 tag with bit15 set.
Output is a flat ordered token list plus a best-effort class->fields grouping (fields attach to the most recent class)."""
import re, sys, json, struct
IDENT = re.compile(rb'[A-Za-z_][A-Za-z0-9_:<>, *&]*')
def scan(b):
    toks=[]; p=0; n=len(b)
    while p<n-4:
        # field: u32 len
        L=struct.unpack_from('<I',b,p)[0]
        if 1<=L<=80 and p+4+L<=n:
            s=b[p+4:p+4+L]
            if IDENT.fullmatch(s) and (p+4+L>=n or True):
                toks.append(('field',p,s.decode())); p+=4+L; continue
        L=struct.unpack_from('<H',b,p)[0]
        if 3<=L<=100 and p+2+L<=n:
            s=b[p+2:p+2+L]
            if IDENT.fullmatch(s) and b[p+2+L:p+4+L] != b'':
                tag=struct.unpack_from('<H',b,p-4)[0] if p>=4 else 0
                toks.append(('class',p,s.decode(),bool(tag&0x8000))); p+=2+L; continue
        p+=1
    return toks
if __name__=='__main__':
    b=open(sys.argv[1],'rb').read(); t=scan(b)
    classes=[]; cur=None
    for k in t:
        if k[0]=='class': cur={'name':k[2],'offset':k[1],'nested':k[3],'fields':[]}; classes.append(cur)
        elif cur: cur['fields'].append(k[2])
    json.dump(classes,open(sys.argv[2],'w'),indent=1)
    print(len(classes),'classes',sum(len(c['fields']) for c in classes),'fields')
