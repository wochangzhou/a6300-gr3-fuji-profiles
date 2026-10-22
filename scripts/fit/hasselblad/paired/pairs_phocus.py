# Same-camera X2D pairs: Lightroom Adobe Standard export vs Phocus Standard export of the same RAW (same white balance,
# mid grey matched at export, lens corrections off). Small residual shifts are found per tile; flat 6x6 cells at /4.
# Usage: pairs_phocus.py <dir with lab.py> <de2000.py> <Adobe Standard .npy> <Phocus .npy> <out.npy>
# Rows: x, y, Adobe Standard rgb (ProPhoto gamma 1.8), Phocus rgb (Adobe RGB gamma 563/256).
import sys, math, numpy as np
sys.path.insert(0, sys.argv[1]); from lab import *
exec(open(sys.argv[2]).read())
L = np.load(sys.argv[3], mmap_mode='r'); X = np.load(sys.argv[4], mmap_mode='r')
F = 4
def box(a, f):
    h, w = a.shape[0]//f*f, a.shape[1]//f*f
    return np.asarray(a[:h, :w], dtype=np.float32).reshape(h//f, f, w//f, f, 3).mean((1, 3))
Ld = box(L, F); Xd = box(X, F)
# small residual geometric shift (lens correction differences): per-tile integer shift on gradients, +-3 px at /4
lumL = np.log(Ld.mean(2)+50); lumX = np.log(Xd.mean(2)+50)
gL = np.hypot(*np.gradient(lumL)); gX = np.hypot(*np.gradient(lumX))
h, w = lumL.shape; T = 128; sh = np.zeros((h//T+1, w//T+1, 2), int)
for i in range(0, h-T+1, T):
    for j in range(0, w-T+1, T):
        a = gL[i:i+T, j:j+T]; best = (-2, 0, 0)
        if a.std() < 1e-3: continue
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                y0, x0 = i+dy, j+dx
                if y0 < 0 or x0 < 0 or y0+T > h or x0+T > w: continue
                v = np.corrcoef(a.ravel(), gX[y0:y0+T, x0:x0+T].ravel())[0, 1]
                if v > best[0]: best = (v, dx, dy)
        sh[i//T, j//T] = best[1:]
C = 6; rows = []
for y in range(3, h-C-3, C):
    for x in range(3, w-C-3, C):
        dx, dy = sh[y//T, x//T]
        a = Ld[y:y+C, x:x+C].reshape(-1, 3); b = Xd[y+dy:y+dy+C, x+dx:x+dx+C].reshape(-1, 3)
        if a.mean() < 300 or (a > 64000).any() or (b > 64000).any(): continue
        if (a.std(0)/np.maximum(a.mean(0), 1)).max() > 0.04 or (b.std(0)/np.maximum(b.mean(0), 1)).max() > 0.04: continue
        rows.append((x*F, y*F, *a.mean(0), *b.mean(0)))
R = np.array(rows); np.save(sys.argv[5], R)
A = lab_lr(R[:, 2:5]); B = lab_phocus(R[:, 5:8])
Ch = np.hypot(A[:, 1], A[:, 2]); neu = Ch < 5
e = np.array([de2000(A[i], B[i]) for i in range(len(A))])
print(f"flat cells {len(R)}  neutral {neu.sum()}  colour {(~neu).sum()}")
print(f"Adobe Std -> Phocus dE00: neutral {e[neu].mean():.2f}  colour {e[~neu].mean():.2f} (p90 {np.percentile(e[~neu],90):.1f})")
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
