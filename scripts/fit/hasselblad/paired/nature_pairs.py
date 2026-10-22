# Usage: nature_pairs.py <dir with lab.py> <Phocus Standard.tif> <Phocus Nature.tif> <out.npy>
# Phocus Standard vs Phocus Nature of the same X2D RAW (same app, same size: pixel-aligned), flat 6x6 cells at /4.
# Rows: x, y, Standard rgb, Nature rgb (both Phocus Adobe RGB encoding).
import sys,numpy as np,tifffile
sys.path.insert(0,sys.argv[1]); from lab import *
L=tifffile.memmap(sys.argv[2]); X=tifffile.memmap(sys.argv[3]); assert L.shape==X.shape
F=4
def box(a):
    h,w=a.shape[0]//F*F,a.shape[1]//F*F; out=np.zeros((h//F,w//F,3),np.float32)
    for i in range(0,h,F*256): out[i//F:(i+F*256)//F]=np.asarray(a[i:min(i+F*256,h),:w],np.float32).reshape(-1,F,w//F,F,3).mean((1,3))
    return out
Ld=box(L); Xd=box(X); h,w=Ld.shape[:2]; C=6; rows=[]
for y in range(3,h-C-3,C):
    for x in range(3,w-C-3,C):
        a=Ld[y:y+C,x:x+C].reshape(-1,3); b=Xd[y:y+C,x:x+C].reshape(-1,3)
        if a.mean()<300 or (a>64000).any() or (b>64000).any(): continue
        if (a.std(0)/np.maximum(a.mean(0),1)).max()>0.04 or (b.std(0)/np.maximum(b.mean(0),1)).max()>0.04: continue
        rows.append((x*F,y*F,*a.mean(0),*b.mean(0)))
R=np.array(rows); np.save(sys.argv[4],R)
A=lab_phocus(R[:,2:5]); B=lab_phocus(R[:,5:8]); Cc=np.hypot(A[:,1],A[:,2]); neu=Cc<3
print(f"cells {len(R)} (neutral {neu.sum()})")
for lo,hi in ((0,20),(20,40),(40,60),(60,80),(80,101)):
    m=neu&(A[:,0]>=lo)&(A[:,0]<hi)
    if m.sum()>20: print(f"  neutral L{lo}-{hi}: dL {np.median(B[m,0]-A[m,0]):+.2f} da {np.median(B[m,1]-A[m,1]):+.2f} db {np.median(B[m,2]-A[m,2]):+.2f} n {m.sum()}")
x,y=R[:,0],R[:,1]; cx,cy=(x.max()+x.min())/2,(y.max()+y.min())/2; r=np.hypot(x-cx,y-cy)/np.hypot(x.max()-cx,y.max()-cy)
print("  position check (neutral L40-80 db):"," ".join(f"r{lo:.1f}:{np.median((B[:,2]-A[:,2])[neu&(r>=lo)&(r<lo+.3)&(A[:,0]>40)&(A[:,0]<80)]):+.2f}" for lo in (0,.3,.6)))
k=(Cc>10); print(f"  colour cells {k.sum()}: dC {np.median(np.hypot(B[k,1],B[k,2])-Cc[k]):+.2f}  dL {np.median(B[k,0]-A[k,0]):+.2f}")
