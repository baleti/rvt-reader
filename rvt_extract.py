#!/usr/bin/env python3
"""Basic .rvt text/metadata extractor (OLE2 + Revit's chunked-deflate streams). No third-party SDK.
usage: rvt_extract.py file.rvt [--raw-dir DIR]   -> text summary on stdout"""
import sys, re, zlib, zipfile, io, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olefile

U16 = re.compile(rb'(?:[\x20-\x7e]\x00){4,}')

def inflate_chunks(stored):
    """Strip Revit's 353-byte page checksums, then inflate every truncated-gzip member (1 for Global/*, ~1000+ for Partitions/*)."""
    from rvtfmt import strip_pages, GZ
    data = strip_pages(stored); out = bytearray(); pos = 0
    while True:
        i = data.find(GZ, pos)
        if i < 0: break
        d = zlib.decompressobj(-15)
        try: o = d.decompress(data[i+10:])
        except zlib.error: pos = i + 4; continue
        out += o; pos = len(data) - len(d.unused_data)
    return bytes(out)

def u16(b, minlen=4):
    return [m.group().decode('utf-16le') for m in U16.finditer(b)]

def noise(s):
    return s.startswith(('autodesk.', 'revit.local')) or not re.search(r'[A-Za-z]{3}', s)

def main(path, rawdir=None):
    o = olefile.OleFileIO(path)
    rd = lambda p: o.openstream(p).read()
    streams = {'/'.join(e): rd('/'.join(e)) for e in o.listdir(streams=True)}
    raw_info = streams.get('BasicFileInfo', b'')
    print('## BasicFileInfo')
    # newer builds put a "Key: value" text block at an odd byte offset; anchor on the first key
    i = raw_info.find('Worksharing'.encode('utf-16le'))
    if i >= 0:
        for line in raw_info[i:].decode('utf-16le', 'replace').splitlines():
            if line.strip(): print(' ', line.strip())
    else:
        for s_ in re.findall(r'[\x20-\x7e]{3,}', raw_info.decode('utf-16le', 'replace')): print(' ', s_)
    if 'ProjectInformation' in streams:
        z = zipfile.ZipFile(io.BytesIO(streams['ProjectInformation']))
        print('## ProjectInformation (atom xml)')
        for n in z.namelist(): print(' ', re.sub(r'<[^>]+>', ' ', z.read(n).decode('utf-8', 'replace')).split())
    t = streams.get('TransmissionData', b'').decode('utf-16le', 'ignore')
    print('## External references:', re.findall(r'<LastSavedAbsolutePath>([^<]+)', t))
    raw = {}
    for name in ('Global/DocumentIncrementTable', 'Global/PartitionTable', 'Global/History',
                 'Global/Latest', 'Global/ElemTable', 'Formats/Latest', 'Global/ContentDocuments'):
        if name in streams: raw[name] = inflate_chunks(streams[name])
    for name in streams:
        if name.startswith('Partitions/'): raw[name] = inflate_chunks(streams[name])
    if rawdir:
        os.makedirs(rawdir, exist_ok=True)
        for k, v in raw.items(): open(os.path.join(rawdir, k.replace('/', '__')), 'wb').write(v)
    print('## Editors (DocumentIncrementTable)')
    for s, n in collections.Counter(u16(raw.get('Global/DocumentIncrementTable', b''))).most_common(): print(f'  {n:4} {s}')
    print('## Views/families (PartitionTable)')
    for s in sorted(set(u16(raw.get('Global/PartitionTable', b'')))): 
        if not noise(s): print(' ', s)
    print('## Strings in element partitions (freq<=50, noise filtered)')
    c = collections.Counter()
    for k, v in raw.items():
        if k.startswith('Partitions/'): c.update(u16(v))
    for s, n in sorted(c.items()):
        if n <= 50 and not noise(s) and len(s) >= 5: print(' ', s)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[sys.argv.index('--raw-dir')+1] if '--raw-dir' in sys.argv else None)
