# regression (corpus 2026-10-23): element_worksets must stop at the ElemTable header row count; a second table follows in real office files. Synthetic table, no files.
import sys, os, struct; sys.path.insert(0, os.path.expanduser('~/rvt-research'))
import rvt_worksets as W
rows = b''.join(struct.pack('<7I', i, i, 0, 1, 1, 0, 0xffffffff)[:24] + struct.pack('<I', 7) for i in range(1, 11))    # 10 rows of 28 bytes, workset word 7 at +24
junk = b''.join(struct.pack('<7I', 100000 + i, 9, 9, 9, 9, 9, 9) for i in range(20))                                   # second section
et = struct.pack('<HI', 1, 10) + rows + junk
class _S:
    def read(self): return b''
class _O:
    def __init__(s, p): pass
    def openstream(s, n): return _S()
W.olefile = type('o', (), {'OleFileIO': _O}); W.inflate_stream = lambda b: (0, et)
r = W.element_worksets('x'); assert sorted(r) == list(range(1, 11)) and set(r.values()) == {7}, r; print('ok')
