# Transfer test: learn g = (Adobe Standard Lab -> Phocus Lab) on same-camera X1D pairs, apply to the A6300
# Adobe Standard export of the same scene, compare with X1D Phocus on the dense_sample.py cells (no A6300 data is fitted).
# Usage: validate.py <paired_dir> <de2000.py> <samples_dir> <pairs.npy> <A6300 AS export .npy> [gain]
import sys, os, math, numpy as np
W, DE, SAMP, PAIRS, LRA = sys.argv[1:6]
sys.path.insert(0, W); from lab import *
exec(open(DE).read())
d = np.load(SAMP+'/samples6.npz'); keep = d['base'].max(1) < 0.985   # same cell filter as the LookTable fits
xyc = d['xy'][keep]; T = np.clip(d['tgt'][keep], 1e-6, None); wh = d['wheel'][keep] > 0
def labpp(p):   # ProPhoto linear (D50) -> Lab
    t = np.clip(p, 1e-7, None)@PP2X.T/W50; f = np.where(t > 216/24389, np.cbrt(t), (24389/27*t+16)/116)
    return np.stack([116*f[..., 1]-16, 500*(f[..., 0]-f[..., 1]), 200*(f[..., 1]-f[..., 2])], -1)
if os.environ.get('XW'):
    _X=np.load(os.environ['XW']); _i=np.clip(np.round(xyc).astype(int),3,None)
    T=np.array([((_X[y-3:y+3,x-3:x+3].reshape(-1,3).mean(0)/65535.0)**(563/256)) for x,y in _i])@(np.linalg.inv(PP2X)@A2X).T  # X1D Phocus target in ProPhoto linear
# ---- A6300 Adobe Standard export sampled on the same cells (LR work = Ad - offset, offset ~ plane fit)
La = np.load(LRA, mmap_mode='r')
Lw = np.asarray(La, np.float32).reshape(2000, 2, 3000, 2, 3).mean((1, 3))
def off(x, y): return 7-2*x/3000, 7-2*y/2000
A_as = []
for cx, cy in xyc:
    dx, dy = off(cx, cy); x0 = int(round(cx-dx-3)); y0 = int(round(cy-dy-3))
    A_as.append(Lw[max(y0, 0):y0+6, max(x0, 0):x0+6].reshape(-1, 3).mean(0) if 0 <= x0 < 2994 and 0 <= y0 < 1994 else [np.nan]*3)
A_as = np.array(A_as); ok = np.isfinite(A_as).all(1)
GAIN = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0  # linear exposure fix for the A6300 export
la = lab_lr(np.clip(A_as[ok]*GAIN**(1/1.8), 0, 65535)); lt = labpp(T[ok]); wk = wh[ok]; xs = xyc[ok, 0]
# ---- g from same-camera pairs
P = np.load(PAIRS); pa = lab_lr(P[:, 2:5]); pb = lab_phocus(P[:, 5:8]); d = pb-pa
k = np.stack([np.floor(pa[:, 0]/4), np.floor(pa[:, 1]/3), np.floor(pa[:, 2]/3)], 1)
u, inv = np.unique(k, axis=0, return_inverse=True); inv = inv.ravel()
BC = np.array([np.median(pa[inv == j], 0) for j in range(len(u))]); BD = np.array([np.median(d[inv == j], 0) for j in range(len(u))])
BN = np.minimum(np.bincount(inv), 30)
def g(q, s=(5, 4, 4), lam=0.5):
    out = np.zeros_like(q)
    for i in range(0, len(q), 4000):
        z = q[i:i+4000]; w = np.exp(-0.5*(((z[:, None, :]-BC[None])/np.array(s))**2).sum(-1))*np.sqrt(BN)[None]
        out[i:i+4000] = z+(w@BD)/(w.sum(1)+lam)[:, None]
    return out
lg = g(la)
def dE(a, b): return np.array([de2000(a[i], b[i]) for i in range(len(a))])
C = np.hypot(lt[:, 1], lt[:, 2]); col = (C > 5) & ~wk; neu = (C <= 5) & ~wk; right = xs >= 1506
rows = [("A6300 Adobe Standard", la), ("A6300 AS + g(X1D pairs)", lg)]
print(f"cells {ok.sum()} (colour {col.sum()}, neutral {neu.sum()}, wheel {wk.sum()})")
for name, v in rows:
    e = dE(v, lt)
    print(f"{name:30s} colour {e[col].mean():.2f} (right half {e[col&right].mean():.2f}, p90 {np.percentile(e[col],90):.1f}) | neutral {e[neu].mean():.2f} | wheel cells {e[wk].mean():.2f}"
          f" | dL colour {(v[col,0]-lt[col,0]).mean():+.2f}")
