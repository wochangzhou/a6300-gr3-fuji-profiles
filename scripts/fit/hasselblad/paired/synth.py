# Synthetic targets for the A6300 cells: target = g(A6300 Adobe Standard export at the cell), where g (Adobe Standard
# Lab -> Phocus Lab) is a Lab kernel regression learned from the same-camera X2D pairs (pairs_phocus.py / flatfield.py).
# Usage: synth.py <dir with lab.py> <pairs.npy> <A6300 Adobe Standard export .tif> <cells.npz> <out dir>
# Writes <out>/samples6.npz (xy, wheel, base, tgt) for pure_correct.py; only cells with enough pair support are kept.
import sys, os, numpy as np, tifffile
W, PAIRS, EXPORT, CELLS, OUTD = sys.argv[1:6]
sys.path.insert(0, W); from lab import *
W50 = np.array([0.9642, 1, 0.8249])
def lab2pp(L):
    fy = (L[:, 0]+16)/116; fx = fy+L[:, 1]/500; fz = fy-L[:, 2]/200
    inv = lambda f: np.where(f**3 > 216/24389, f**3, (116*f-16)/(24389/27))
    return (np.stack([inv(fx), inv(fy), inv(fz)], 1)*W50) @ np.linalg.inv(PP2X).T
P = np.load(PAIRS); pa = lab_lr(P[:, 2:5]); d = lab_phocus(P[:, 5:8])-pa
k = np.stack([np.floor(pa[:, 0]/4), np.floor(pa[:, 1]/3), np.floor(pa[:, 2]/3)], 1)
u, inv_ = np.unique(k, axis=0, return_inverse=True); inv_ = inv_.ravel()
BC = np.array([np.median(pa[inv_ == j], 0) for j in range(len(u))]); BD = np.array([np.median(d[inv_ == j], 0) for j in range(len(u))])
BN = np.minimum(np.bincount(inv_), 30)
def g(q, s=(5, 4, 4), lam=0.5):
    out = np.zeros_like(q); conf = np.zeros(len(q))
    for i in range(0, len(q), 4000):
        z = q[i:i+4000]; w = np.exp(-0.5*(((z[:, None, :]-BC[None])/np.array(s))**2).sum(-1))*np.sqrt(BN)[None]
        out[i:i+4000] = z+(w@BD)/(w.sum(1)+lam)[:, None]; conf[i:i+4000] = w.sum(1)
    return out, conf
E = tifffile.memmap(EXPORT); h, w = E.shape[0]//2*2, E.shape[1]//2*2
Ew = np.zeros((h//2, w//2, 3), np.float32)
for i in range(0, h, 512): Ew[i//2:(i+512)//2] = np.asarray(E[i:min(i+512, h), :w], np.float32).reshape(-1, 2, w//2, 2, 3).mean((1, 3))
C = np.load(CELLS); ex = np.round(C['exy']-3).astype(int)
A = np.array([Ew[y:y+6, x:x+6].reshape(-1, 3).mean(0) for x, y in ex])
q = lab_lr(np.clip(A, 0, 65535)); t, conf = g(q); ok = conf > 2.0
print(f"cells {len(ok)}, kept {ok.sum()} (conf>2), colour kept {(ok & (np.hypot(q[:,1],q[:,2])>5)).sum()}")
os.makedirs(OUTD, exist_ok=True)
np.savez(OUTD+'/samples6.npz', xy=C['xy'][ok], wheel=C['wheel'][ok], base=C['base'][ok], tgt=lab2pp(t[ok]))
