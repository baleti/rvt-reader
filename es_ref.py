
import struct
def find_ref(ES, D, d, sch, W):
    out = {}
    if 'ESSchema' not in sch.by: return out
    dec = D.Dec(sch, idsize=W); dec.STOP = ()
    n = len(d)
    for pre, mid, post, counted in ((0, 0, 0, True), (0, 0, 4, True), (1, 4, 0, False), (1, 0, 4, False)):
        p = 0
        while p < n - 60:
            q = p + 4 if counted else p
            if counted:
                cnt = struct.unpack_from('<I', d, p)[0]
                if not 1 <= cnt <= 5000: p += 1; continue
            qq = q + pre + 16 + post
            if qq + 4 > n: break
            ln = struct.unpack_from('<I', d, qq)[0]
            if not (0 <= ln <= 4000 and qq + 4 + 2 * ln <= n and all(d[qq + 4 + 2 * i + 1] == 0 and 0x20 <= d[qq + 4 + 2 * i] < 0x7f for i in range(min(ln, 3)))): p += 1; continue
            try:
                pp = q; got = []
                for _ in range(cnt if counted else 100000):
                    try: key, sc, q2 = ES.decode_entry(dec, sch, d, pp, pre, mid, post)
                    except Exception: break
                    if not ES._good(key, sc): break
                    got.append(sc); pp = q2
                if got:
                    for sc in got: out[sc['m_guid']['m_guid']] = sc
                    p = pp; continue
            except Exception: pass
            p += 1
    return out
