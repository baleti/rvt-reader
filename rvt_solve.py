#!/usr/bin/env python3
"""Per-record layout solver: DFS over per-class layout hints (prefix bytes, field order, suffix bytes) so that the whole record
(fixed part + all pointer bodies in order) decodes plausibly and ends exactly at the next record header."""
import sys, os, struct, math, collections, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_decode as D

def plausible(v, depth=0):
    if depth > 8: return True
    if isinstance(v, float): return math.isfinite(v) and (v == 0.0 or 1e-12 < abs(v) < 1e9)
    if isinstance(v, str): return all(c.isprintable() for c in v)
    if isinstance(v, dict):
        return all(plausible(x, depth + 1) for k, x in v.items() if not k.startswith('_'))
    if isinstance(v, list):
        return len(v) < 100000 and all(plausible(x, depth + 1) for x in v[:200])
    return True

OPTS = []
for pre in range(0, 13):
    for suf in (0, 1, 2, 3, 4):
        for order in ('base', 'derived'):
            OPTS.append({'prefix': pre, 'suffix': suf, 'order': order})
OPTS.sort(key=lambda o: (o['prefix'] > 0) + (o['suffix'] > 0) + (o['order'] != 'base'))   # prefer simple

class Solver:
    def __init__(self, dec, ids, et, W, F, budget=60000):
        self.d = dec; self.ids = ids; self.et = et; self.W = W; self.F = F; self.budget = budget; self.nest = 'depth'; self.rev = False; self.nodes = 0; self.chosen = []; self.dead = set()
    def header_at(self, chunk, q):
        if q == len(chunk): return True
        if q + 24 > len(chunk): return False
        return struct.unpack_from(self.F, chunk, q + 4)[0] in self.ids and struct.unpack_from('<H', chunk, q + 12 + self.W)[0] in self.et
    def go(self, chunk, queue, p, maxh, base_hints):
        if not queue: return p if self.header_at(chunk, p) else None
        self.nodes += 1
        if self.nodes > self.budget: return None
        key = (p, tuple(t for _, t in queue), maxh, tuple(sorted((k, v.get('prefix', 0), v.get('suffix', 0), v.get('order', 'base')) for k, v in base_hints.items() if k in {self.d.s.name(t) for _, t in queue})))
        if key in self.dead: return None
        slot, tag = queue[0]; rest = queue[1:]; name = self.d.s.name(tag)
        has_chain = len(self.d.s.chain(tag - 12)) > 1
        known = base_hints.get(name)
        cands = [known] if known else OPTS
        for opt in cands:
            if opt['order'] == 'derived' and not has_chain: continue
            self.d.hints = {**base_hints, name: opt}; self.d.maxh = maxh
            pend = []
            try: v, p2 = self.d.struct(chunk, p, tag - 12, pend, [name])
            except (D.Desync, struct.error, IndexError, KeyError, RecursionError, UnicodeDecodeError, TypeError): continue
            if not plausible(v): continue
            slot['obj'] = v; mh2 = self.d.maxh
            r = self.go(chunk, (pend + rest) if self.nest == 'depth' else (rest + pend), p2, mh2, {**base_hints, name: opt})
            if r is not None:
                self.chosen.append((name, opt)); return r
        self.dead.add(key)
        return None
    def solve(self, chunk, i, base_hints):
        d = self.d; d.hints = base_hints; d.maxh = 2; d.err = None
        W = self.W; eid = struct.unpack_from(self.F, chunk, i + 4)[0]; tag = struct.unpack_from('<H', chunk, i + 12 + W)[0]
        pend = []
        try: v, p = d.struct(chunk, i + 4 + W + 10, tag - 12, pend, [d.s.name(tag)], top_out={})
        except D.Desync: return None
        self.nodes = 0; self.chosen = []; self.dead = set()
        if self.rev: pend = pend[::-1]
        end = self.go(chunk, pend, p, d.maxh, dict(base_hints))
        return end, v
