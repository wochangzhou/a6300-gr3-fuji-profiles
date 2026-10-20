# Match the Phocus neutral axis to the Adobe Standard neutral axis of the same pair, per L* band:
# near-neutral cells (AS C*<3): per-channel log ratio r_c = log(T_c/P_c), T = Y_P*AS_c/Y_AS (Phocus luminance,
# AS chromaticity). Median r_c in 5-L* bins (>=20 cells), interpolated over each cell's Phocus L*, constant at the ends.
# Every Phocus value is multiplied by exp(r_c(L*)), so g no longer carries a grey-axis cast; luminance is kept.
import sys, numpy as np
sys.path.insert(0, sys.argv[1]); from lab import *
R = np.load(sys.argv[2])
P2 = ((R[:, 5:8]/65535)**(563/256)) @ A2X.T @ np.linalg.inv(PP2X).T   # Phocus -> ProPhoto linear D50
PA = (R[:, 2:5]/65535)**1.8                                               # LR export, ProPhoto linear
Yp = P2 @ PP2X[1]; Ya = PA @ PP2X[1]; aL = lab_lr(R[:, 2:5]); neu = np.hypot(aL[:, 1], aL[:, 2]) < 3
Lp = lab_phocus(R[:, 5:8])[:, 0]
T = Yp[:, None]*PA/np.maximum(Ya, 1e-9)[:, None]
r = np.log(np.maximum(T, 1e-9)/np.maximum(P2, 1e-9))
cen = []; rc = []; cnt = []
for lo in range(0, 100, 5):
    m = neu & (Lp >= lo) & (Lp < lo+5)
    if m.sum() >= 20: cen.append(np.median(Lp[m])); rc.append(np.median(r[m], 0)); cnt.append(m.sum())
cen = np.array(cen); rc = np.array(rc); cnt = np.array(cnt, float)
# smooth across L*: Gaussian (sigma 8 L*) weighted by sqrt(cell count), removes bin-to-bin noise
w = np.exp(-0.5*((cen[:, None]-cen[None])/8)**2)*np.sqrt(cnt)[None]; rc = (w @ rc)/w.sum(1)[:, None]
print("bins", len(cen), "L*", cen.round(0).astype(int).tolist())
print("log-ratio R,G,B per bin:", np.round(rc, 3).tolist())
k = np.stack([np.interp(Lp, cen, rc[:, c]) for c in range(3)], 1)
out = P2*np.exp(k)
enc = (np.clip(out @ PP2X.T @ np.linalg.inv(A2X).T, 0, 1)**(256/563))*65535
R2 = R.copy(); R2[:, 5:8] = enc; np.save(sys.argv[3], R2)
for nm, RR in (("before", R), ("after", R2)):
    A = lab_lr(RR[:, 2:5]); B = lab_phocus(RR[:, 5:8]); n = np.hypot(A[:, 1], A[:, 2]) < 3; s = []
    for lo, hi in ((15, 35), (35, 55), (55, 75), (75, 95)):
        m = n & (A[:, 0] >= lo) & (A[:, 0] < hi)
        if m.sum() > 50: s.append(f"L{lo}-{hi} Δa{np.median(B[m,1]-A[m,1]):+.2f} Δb{np.median(B[m,2]-A[m,2]):+.2f} ΔL{np.median(B[m,0]-A[m,0]):+.2f} n{m.sum()}")
    c = np.hypot(A[:, 1], A[:, 2]) > 10
    print(f"{nm:6s} neutral Phocus−AS (median): "+" | ".join(s)+f" || colour dC {(np.hypot(B[c,1],B[c,2])-np.hypot(A[c,1],A[c,2])).mean():+.2f}, colour dL {(B[c,0]-A[c,0]).mean():+.2f}")
