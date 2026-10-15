import sys,re,struct
sys.path.insert(0,'/home/user1/rvt-research')
import parse_formats as pf
def vocab(out,limit=141000):
    return {t[2] for t in pf.scan(out[:limit])}
def quality(out,vocab_,a=141100,b=160000):
    toks=pf.scan(out[a:b])
    if not toks: return 0.0,0
    hit=sum(1 for t in toks if t[2] in vocab_)
    return hit/len(toks),len(toks)
