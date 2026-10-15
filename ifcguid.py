import uuid
_C="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
def compress(g):
    n=int.from_bytes(g.bytes,'big'); out=[]
    # first char encodes top 2 bits, then 21 chars x 6 bits
    out.append(_C[(n>>126)&3])
    for i in range(21): out.append(_C[(n>>(120-6*i))&63])
    return ''.join(out)
def from_unique(u):
    g=u[:36]; eid=int(u[37:],16)
    b=bytearray(uuid.UUID(g).bytes)
    x=int.from_bytes(b[12:],'big')^(eid&0xffffffff)
    b[12:]=x.to_bytes(4,'big')
    return compress(uuid.UUID(bytes=bytes(b)))
