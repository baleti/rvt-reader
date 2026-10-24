"""Core stream handling for Revit (.rvt/.rfa/.rte) files. Clean implementation; page layout constants learned by experiment,
also published by DrunkOnJava/rvt-rs (Apache-2.0; prior art, no code used) and confirmed here by experiment on 14 files (Revit 2011-2025)."""
import zlib, re
PAGE_STORED = 65249     # bytes per stored page
PAGE_PAYLOAD = 64896    # payload bytes at the start of each page; the rest (353 bytes) is a checksum/ECC trailer
GZ = b'\x1f\x8b\x08\x00'

def strip_pages(stored: bytes) -> bytes:
    """Remove the 353-byte trailer after every FULL 65,249-byte page. A short final page is kept whole."""
    full = len(stored) // PAGE_STORED
    if full == 0: return stored
    out = bytearray()
    for p in range(full):
        s = p * PAGE_STORED
        out += stored[s:s + PAGE_PAYLOAD]
    out += stored[full * PAGE_STORED:]
    return bytes(out)

def inflate_stream(stored: bytes):
    """Return (prefix_bytes, decompressed). prefix = bytes before the gzip magic (custom header, 0/8 bytes)."""
    data = strip_pages(stored)
    i = data.find(GZ)
    if i < 0 or i > 16: raise ValueError('no gzip header near start')
    d = zlib.decompressobj(-15)
    out = d.decompress(data[i + 10:])
    return data[:i], out, d.unused_data
