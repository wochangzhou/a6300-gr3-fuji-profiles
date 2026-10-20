# Apply the X1D Nature look to another Standard profile: per LookTable node, the Nature/Standard difference
# (hue offset, saturation and value ratios) and the Nature tone curve are carried over unchanged.
# Usage: transfer_nature.py <scripts> <X1D Standard.dcp> <X1D Nature.dcp> <target Standard.dcp> <out.dcp> <name>
import sys, struct, numpy as np
sys.path.insert(0, sys.argv[1]); from dcp import read
S1, N1, S2 = (read(p) for p in sys.argv[2:5]); OUT, NAME = sys.argv[5:7]
assert S1[50981][2] == N1[50981][2] == S2[50981][2]
assert S1[50940][3] == S2[50940][3], "Standard tone curves differ"
a, b, c = (np.array(t[50982][2]).reshape(-1, 3) for t in (S1, N1, S2))
d = c.copy(); d[:, 0] += b[:, 0]-a[:, 0]; d[:, 1] *= b[:, 1]/a[:, 1]; d[:, 2] *= b[:, 2]/a[:, 2]
tags = {k: (v[0], v[1], v[3]) for k, v in S2.items()}
tags[50982] = (11, d.size, d.astype('<f4').tobytes()); tags[50940] = (N1[50940][0], N1[50940][1], N1[50940][3])
for k, s in ((50936, NAME), (50942, NAME+": X1D Nature look (LookTable and tone curve difference) on the X2D Standard profile")):
    e = (s+'\0').encode(); tags[k] = (2, len(e), e)
ents = sorted(tags.items()); n = len(ents); off = 8+2+12*n+4; ifd = b''; data = b''
for k, (typ, cnt, raw) in ents:
    if len(raw) <= 4: ifd += struct.pack('<HHI', k, typ, cnt)+raw.ljust(4, b'\0')
    else:
        if (off+len(data)) % 2: data += b'\0'
        ifd += struct.pack('<HHII', k, typ, cnt, off+len(data)); data += raw
open(OUT, 'wb').write(b'IIRC'+struct.pack('<I', 8)+struct.pack('<H', n)+ifd+b'\0\0\0\0'+data)
r = read(OUT); print("built", r[50936][2], "| max |dh| change", round(float(np.abs(b[:, 0]-a[:, 0]).max()), 2))
