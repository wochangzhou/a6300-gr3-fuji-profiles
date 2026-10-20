# Same-camera, same-app pairs (Standard): LR Adobe Standard export vs LR Camera Standard export (identical settings,
# ProPhoto RGB gamma 1.8, pixel-aligned: no geometric shift). Output rows as pairs.py: x, y, AS rgb, CS rgb.
# Usage: pairs_lr.py <dir with lab.py> <de2000.py> <Adobe Standard.tif> <Camera Standard.tif> <out.npy>
import sys, math, numpy as np, tifffile
sys.path.insert(0, sys.argv[1]); from lab import *
exec(open(sys.argv[2]).read())
L = tifffile.memmap(sys.argv[3]); X = tifffile.memmap(sys.argv[4])
assert L.shape == X.shape, (L.shape, X.shape)
F = 4
def box(a, f):
    h, w = a.shape[0]//f*f, a.shape[1]//f*f; out = np.zeros((h//f, w//f, 3), np.float32)
    for i in range(0, h, f*256): out[i//f:(i+f*256)//f] = np.asarray(a[i:min(i+f*256, h), :w], np.float32).reshape(-1, f, w//f, f, 3).mean((1, 3))
    return out
Ld = box(L, F); Xd = box(X, F); h, w = Ld.shape[:2]
C = 6; rows = []
for y in range(3, h-C-3, C):
    for x in range(3, w-C-3, C):
        a = Ld[y:y+C, x:x+C].reshape(-1, 3); b = Xd[y:y+C, x:x+C].reshape(-1, 3)
        if a.mean() < 300 or (a > 64000).any() or (b > 64000).any(): continue
        if (a.std(0)/np.maximum(a.mean(0), 1)).max() > 0.04 or (b.std(0)/np.maximum(b.mean(0), 1)).max() > 0.04: continue
        rows.append((x*F, y*F, *a.mean(0), *b.mean(0)))
R = np.array(rows); np.save(sys.argv[5], R)
A = lab_lr(R[:, 2:5]); B = lab_lr(R[:, 5:8])
Ch = np.hypot(A[:, 1], A[:, 2]); neu = Ch < 5
e = np.array([de2000(A[i], B[i]) for i in range(len(A))])
print(f"flat cells {len(R)}  neutral {neu.sum()}  colour {(~neu).sum()}")
print(f"Adobe Std -> Camera Std dE00: neutral {e[neu].mean():.2f}  colour {e[~neu].mean():.2f} (p90 {np.percentile(e[~neu],90):.1f})")
for lo, hi in ((0, 30), (30, 50), (50, 70), (70, 101)):
    m = neu & (A[:, 0] >= lo) & (A[:, 0] < hi)
    if m.sum(): print(f"  neutral L*{lo}-{hi}: dL {(B[m,0]-A[m,0]).mean():+.2f} da {(B[m,1]-A[m,1]).mean():+.2f} db {(B[m,2]-A[m,2]).mean():+.2f} n {m.sum()}")
hA = np.degrees(np.arctan2(A[:, 2], A[:, 1])) % 360; hB = np.degrees(np.arctan2(B[:, 2], B[:, 1])) % 360; CB = np.hypot(B[:, 1], B[:, 2])
print("by hue (colour cells, C*>10): hue sector | n | dL | dC* | dh deg")
for s in range(0, 360, 30):
    m = (~neu) & (Ch > 10) & (hA >= s) & (hA < s+30)
    if m.sum() < 20: continue
    dh = ((hB[m]-hA[m]+180) % 360)-180
    print(f"  {s:3d}-{s+30:3d}  {m.sum():5d}  {(B[m,0]-A[m,0]).mean():+5.1f}  {(CB[m]-Ch[m]).mean():+5.1f}  {np.median(dh):+5.1f}")
