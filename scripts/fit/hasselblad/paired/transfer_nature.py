# Nature on the Lightroom-based Standard: per LookTable node the X1D Nature/Standard difference (hue offset,
# saturation and value ratios), and the tone difference carried through the Standard curve:
# new curve = ACR3( PhStd^-1( PhNat(x) ) ); BaselineExposureOffset chosen so mid grey (N5) matches Adobe Standard.
# Usage: transfer_nature.py <scripts> <X1D Standard (Phocus ref)> <X1D Nature> <target Standard (ACR3)> <out.dcp> <name> <base.json> <K model>
import sys, struct, json, numpy as np
sys.path.insert(0, sys.argv[1]); from dcp import read
S1, N1, S2 = (read(p) for p in sys.argv[2:5]); OUT, NAME, BASE, K = sys.argv[5], sys.argv[6], sys.argv[7], float(sys.argv[8])
assert S1[50981][2] == N1[50981][2] == S2[50981][2] and S1[51109][2] == N1[51109][2]
cv = lambda t: (np.array(t[50940][2])[0::2], np.array(t[50940][2])[1::2])
sx, sy = cv(S1); nx, ny = cv(N1); ax, ay = cv(S2)
x = np.linspace(0, 1, 1025); f = np.interp(np.interp(x, nx, ny), sy, sx)       # PhStd^-1(PhNat(x))
curve = np.interp(f, ax, ay)
a, b, c = (np.array(t[50982][2]).reshape(-1, 3) for t in (S1, N1, S2))
d = c.copy(); d[:, 0] += b[:, 0]-a[:, 0]; d[:, 1] *= b[:, 1]/a[:, 1]; d[:, 2] *= b[:, 2]/a[:, 2]
B = json.load(open(BASE))['a6300']; y5 = K*np.mean(B['n5'])
fx = lambda v: np.interp(np.interp(v, nx, ny), sy, sx)
lo, hi = -2.0, 2.0
for _ in range(80):
    m = (lo+hi)/2
    if fx(y5*2**m) < y5: lo = m
    else: hi = m
beo = round((lo+hi)/2, 4)
L = lambda yv: 116*np.cbrt(yv)-16
g = ["white", "n8", "n6.5", "n5", "n3.5", "black"]; Y = K*np.array([np.mean(B[k]) for k in g])
print("greys L* Adobe Std :", L(np.interp(Y, ax, ay)).round(1))
print("greys L* Nature new:", L(np.interp(Y*2**beo, x, curve)).round(1), "BEO %+.4f" % beo)
tags = {k: (v[0], v[1], v[3]) for k, v in S2.items()}
tags[50982] = (11, d.size, d.astype('<f4').tobytes())
pts = np.stack([x, curve], 1).ravel().astype('<f4'); tags[50940] = (11, pts.size, pts.tobytes())
tags[51109] = (10, 1, struct.pack('<iI', int(round(beo*10000)), 10000))
for k, s in ((50936, NAME), (50942, NAME+": X1D Nature difference (LookTable and tone) on the Lightroom-based Standard")):
    e = (s+'\0').encode(); tags[k] = (2, len(e), e)
ents = sorted(tags.items()); n = len(ents); off = 8+2+12*n+4; ifd = b''; data = b''
for k, (typ, cnt, raw) in ents:
    if len(raw) <= 4: ifd += struct.pack('<HHI', k, typ, cnt)+raw.ljust(4, b'\0')
    else:
        if (off+len(data)) % 2: data += b'\0'
        ifd += struct.pack('<HHII', k, typ, cnt, off+len(data)); data += raw
open(OUT, 'wb').write(b'IIRC'+struct.pack('<I', 8)+struct.pack('<H', n)+ifd+b'\0\0\0\0'+data)
r = read(OUT); print("built", r[50936][2], "BEO", r[51109][2])
