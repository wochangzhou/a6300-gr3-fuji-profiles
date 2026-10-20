# Remove Phocus Nature's fixed-WB cast (5500K/+10) from the paired Phocus values: per-channel log-log curves,
# fitted on neutral cells (Adobe Standard C*<3), map each ProPhoto channel onto the cell's luminance Y.
# The 5500K preset adds the cast back with RGB curves, as before.
import sys, numpy as np
sys.path.insert(0, sys.argv[1]); from lab import *
R = np.load(sys.argv[2])
P2 = ((R[:, 5:8]/65535)**(563/256)) @ A2X.T @ np.linalg.inv(PP2X).T  # ProPhoto linear (D50)
Y = P2 @ PP2X[1]; aL = lab_lr(R[:, 2:5]); neu = np.hypot(aL[:, 1], aL[:, 2]) < 3
ly = np.log(np.maximum(Y[neu], 1e-6)); bins = np.quantile(ly, np.linspace(0, 1, 25))
out = np.empty_like(P2)
for c in range(3):
    lc = np.log(np.maximum(P2[neu, c], 1e-6)); xs = []; ys = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (ly >= lo) & (ly <= hi)
        if m.sum() > 20: xs.append(np.median(lc[m])); ys.append(np.median(ly[m]))
    xs, ys = np.array(xs), np.array(ys); o = np.argsort(xs); xs, ys = xs[o], ys[o]
    l = np.log(np.maximum(P2[:, c], 1e-6))
    out[:, c] = np.exp(np.interp(l, xs, ys, left=None, right=None) + np.where(l < xs[0], l-xs[0], 0) + np.where(l > xs[-1], l-xs[-1], 0))
    print("channel", c, "offset at mid grey (log)", round(float(np.interp(np.median(ly), ys, xs)-np.median(ly)), 3))
enc = (np.clip(out @ PP2X.T @ np.linalg.inv(A2X).T, 0, 1)**(256/563))*65535
R2 = R.copy(); R2[:, 5:8] = enc; np.save(sys.argv[3], R2)
A = lab_lr(R2[:, 2:5]); B = lab_phocus(R2[:, 5:8]); n = np.hypot(A[:, 1], A[:, 2]) < 5
print("after: neutral cells mean a/b of Nature", B[n, 1].mean().round(2), B[n, 2].mean().round(2), "| colour cells dC", (np.hypot(B[~n,1],B[~n,2])-np.hypot(A[~n,1],A[~n,2])).mean().round(1))
