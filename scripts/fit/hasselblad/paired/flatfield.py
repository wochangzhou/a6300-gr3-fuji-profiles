# Position-dependent gain that Phocus applies before its tone curve (sensor/lens shading correction), relative to
# the Lightroom export. Model per channel on neutral pair cells:  log(Phocus/AS) = f(L*) + s(L*) * g(r),
# s = log-slope of the tone curve at that level (ACR3 used as the curve shape), g(r) = r^2, r^4, r^6 polynomial.
# Removal: v -> curve( curve^-1(v) / G_c(r) ) on the Phocus side, i.e. the gain is taken out before the curve.
# Usage: flatfield.py <dir with lab.py> <pairs.npy> <ACR3 curve .txt> <out.npy>
import sys,numpy as np
sys.path.insert(0,sys.argv[1]); from lab import *
R=np.load(sys.argv[2]); ACR3=sys.argv[3]; OUT=sys.argv[4]
a=np.loadtxt(ACR3); ax=np.linspace(0,1,len(a))
lx=np.log(np.maximum(ax[1:],1e-6)); ly=np.log(np.maximum(a[1:],1e-6)); slope_y=np.gradient(ly,lx)   # dlny/dlnx vs y
def s_of(v): return np.interp(v,a[1:],slope_y)
Pp=(((R[:,5:8]/65535)**(563/256)) @ A2X.T) @ np.linalg.inv(A2X).T
Pa=(((R[:,2:5]/65535)**1.8) @ PP2X.T) @ np.linalg.inv(A2X).T
A=lab_lr(R[:,2:5]); neu=(np.hypot(A[:,1],A[:,2])<3)&(A[:,0]>15)&(A[:,0]<92)&(Pp.min(1)>1e-4)&(Pa.min(1)>1e-4)
x,y=R[:,0],R[:,1]; cx,cy=(x.max()+x.min())/2,(y.max()+y.min())/2; r=np.hypot(x-cx,y-cy)/np.hypot(x.max()-cx,y.max()-cy)
M=np.stack([r**2,r**4,r**6],1); Lbin=np.clip(((A[neu,0]-15)//2.5).astype(int),0,31)
coef=[]
for c in range(3):
    lr=np.log(Pp[neu,c]/Pa[neu,c]); s=s_of(Pp[neu,c]); k=np.zeros(3); w=np.ones(neu.sum(),bool)
    for it in range(15):
        g=s*(M[neu]@k); f=np.zeros(32)
        for j in range(32):
            m=(Lbin==j)&w
            if m.sum()>=10: f[j]=np.median((lr-g)[m])
        res0=lr-f[Lbin]; Ms=M[neu]*s[:,None]; k=np.linalg.lstsq(Ms[w],res0[w],rcond=None)[0]
        res=res0-Ms@k; mad=np.median(np.abs(res))*1.4826; w=np.abs(res)<3*mad
    coef.append(k)
coef=np.array(coef); G=np.exp(M@coef.T)
print("pre-curve gain (R,G,B) r=0.5:",np.exp(np.array([.25,.0625,.015625])@coef.T).round(3)," r=0.9:",np.exp(np.array([.81,.6561,.531441])@coef.T).round(3))
inv=lambda v: np.interp(v,a,ax); fwd=lambda u: np.interp(u,ax,a)
Pp2=fwd(np.clip(inv(np.clip(Pp,0,1))/G,0,1))
enc=(np.clip(Pp2,0,1)**(256/563))*65535; R2=R.copy(); R2[:,5:8]=enc; np.save(OUT,R2); np.save(OUT.replace('.npy','_coef.npy'),coef)
B0=lab_phocus(R[:,5:8]); B1=lab_phocus(enc); C=np.hypot(A[:,1],A[:,2])
for lo,hi in ((0,.25),(.25,.45),(.45,.65),(.65,.85),(.85,1.01)):
    out=[]
    for Llo,Lhi in ((15,40),(40,65),(65,95)):
        k=(C<3)&(r>=lo)&(r<hi)&(A[:,0]>=Llo)&(A[:,0]<Lhi)
        if k.sum()>=30: out.append(f"L{Llo}-{Lhi} dL {np.median(B0[k,0]-A[k,0]):+.2f}->{np.median(B1[k,0]-A[k,0]):+.2f} db {np.median(B0[k,2]-A[k,2]):+.2f}->{np.median(B1[k,2]-A[k,2]):+.2f}")
    print(f"  r {lo:.2f}-{hi:.2f}: "+" | ".join(out))
