import re,sys,collections
b=open(sys.argv[1],'rb').read()
rx=re.compile(rb'(?:[\x20-\x7e]\x00){4,}')
c=collections.Counter(m.group().decode('utf-16le') for m in rx.finditer(b))
for s,n in c.most_common(int(sys.argv[2])): print(n,s)
print(len(c),'unique',file=sys.stderr)
