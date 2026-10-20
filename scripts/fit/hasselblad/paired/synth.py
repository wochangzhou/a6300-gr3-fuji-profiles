# Synthetic HNCS targets for A6300 cells: target = g_X2D(A6300 Adobe Standard export), where g is learned from
# same-camera X2D pairs (Adobe Standard -> Phocus). Writes sample files in the formats the existing fit scripts read.
import sys, os, json, shutil, numpy as np
W, PAIRS, LREXP, SAMPLES, OUTD, GAIN, KIND = sys.argv[1:8]; GAIN = float(GAIN)
sys.path.insert(0, W); from lab import *
PP2X = np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]); W50 = np.array([0.9642,1,0.8249])
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
La = np.load(LREXP, mmap_mode='r'); Lw = np.asarray(La, np.float32).reshape(2000, 2, 3000, 2, 3).mean((1, 3))
def sample_cells(xy):
    out = []
    for cx, cy in xy:
        dx, dy = 7-2*cx/3000, 7-2*cy/2000; x0 = int(round(cx-dx-3)); y0 = int(round(cy-dy-3))
        out.append(Lw[y0:y0+6, x0:x0+6].reshape(-1, 3).mean(0) if 0 <= x0 < 2994 and 0 <= y0 < 1994 else [np.nan]*3)
    return np.array(out)
def target(rgb16):
    q = lab_lr(np.clip(rgb16*GAIN**(1/1.8), 0, 65535)); t, c = g(q); return lab2pp(t), c, q
S = np.load(SAMPLES); A = sample_cells(S['xy']); ok = np.isfinite(A).all(1)
T, conf, q = target(np.nan_to_num(A)); ok &= conf > 2.0
print(f"{KIND}: cells {len(ok)}, kept {ok.sum()} (conf>2), colour kept {(ok & (np.hypot(q[:,1],q[:,2])>5)).sum()}")
os.makedirs(OUTD, exist_ok=True)
D = {k: S[k][ok] for k in S.files}; D['tgt1'] = S['tgt'][ok]; D['tgt'] = T[ok]
# chart: A6300 export patches, grid measured on the export preview (scale 6)
NAMES = ["brown","skin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan","white","n8","n6.5","n5","n3.5","black"]
ch = np.array([np.asarray(La[(101+32*r)*6-36:(101+32*r)*6+36, int((425+30.6*c)*6)-36:int((425+30.6*c)*6)+36], float).reshape(-1, 3).mean(0) for r in range(4) for c in range(6)])
cT, cconf, cq = target(ch)
print("chart AS L*:", np.round(cq[:, 0], 1).tolist()); print("chart conf min %.1f" % cconf.min())
np.savez(OUTD+'/samples6.npz', **D)
np.save(OUTD+f'/chart_{KIND}.npy', cT)
