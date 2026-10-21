# Lens-uncorrected A6300 export -> sample positions: block registration against the lens-corrected export (on which
# the dense_sample.py cell offsets were measured), on the /2 work grid.
# Usage: lens_shift.py <uncorrected export.tif> <corrected export.npy> <out dir>. Finds s(p) with new(p+s) ~ old(p); fits a smooth quadratic field; saves the field and the new export as .npy.
import sys, numpy as np, tifffile
new = tifffile.memmap(sys.argv[1]); old = np.load(sys.argv[2], mmap_mode='r'); OUT = sys.argv[3]
np.save(OUT+'/lr_sony_nolens.npy', np.asarray(new))
def work(a):
    return np.asarray(a, np.float32).reshape(2000, 2, 3000, 2, 3).mean((1, 3))
A = work(old); Bn = work(new)
def feat(w):
    l = np.log(w.mean(2)+50); g = np.hypot(*np.gradient(l)); return g
fa, fb = feat(A), feat(Bn)
T = 96; R = 14; pts = []
for y in range(R+T//2, 2000-R-T//2, T):
    for x in range(R+T//2, 3000-R-T//2, T):
        a = fa[y-T//2:y+T//2, x-T//2:x+T//2]
        if a.std() < 0.01: continue
        a = (a-a.mean())/a.std(); best = None; sc = np.full((2*R+1, 2*R+1), -9.0)
        for dy in range(-R, R+1):
            for dx in range(-R, R+1):
                b = fb[y+dy-T//2:y+dy+T//2, x+dx-T//2:x+dx+T//2]; sc[dy+R, dx+R] = (a*(b-b.mean())).mean()/(b.std()+1e-9)
        iy, ix = np.unravel_index(sc.argmax(), sc.shape)
        if sc[iy, ix] < 0.5 or iy in (0, 2*R) or ix in (0, 2*R): continue
        def sub(m, c, p): return (m-p)/(2*(m-2*c+p)) if (m-2*c+p) != 0 else 0
        sy = iy-R + sub(sc[iy-1, ix], sc[iy, ix], sc[iy+1, ix]); sx = ix-R + sub(sc[iy, ix-1], sc[iy, ix], sc[iy, ix+1])
        pts.append((x, y, sx, sy, sc[iy, ix]))
P = np.array(pts); print("blocks", len(P), "shift x range", P[:, 2].min().round(2), P[:, 2].max().round(2), "y", P[:, 3].min().round(2), P[:, 3].max().round(2))
u = (P[:, 0]-1500)/1500; v = (P[:, 1]-1000)/1500
X = np.stack([np.ones_like(u), u, v, u*u, u*v, v*v, u*(u*u+v*v), v*(u*u+v*v)], 1)
cx = np.linalg.lstsq(X, P[:, 2], rcond=None)[0]; cy = np.linalg.lstsq(X, P[:, 3], rcond=None)[0]
rx = P[:, 2]-X@cx; ry = P[:, 3]-X@cy
print("fit residual rms x %.3f y %.3f px (work grid)" % (np.sqrt((rx**2).mean()), np.sqrt((ry**2).mean())))
np.savez(OUT+'/shift_field.npz', cx=cx, cy=cy, pts=P)
