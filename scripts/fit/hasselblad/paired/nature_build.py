# Nature from the X2D Phocus Standard->Nature pair, applied on top of an existing Standard profile:
#  tone: neutral pair cells, dL(L_std) (2.5-L* bands, smoothed, tapered at both ends) -> Nature curve = Y(L_std + dL)
#        where L_std is the Standard profile's own curve output;
#  colour: target_nat(cell) = g(render_std(cell)), g = Lab kernel regression of (Nature - Standard) on Standard Lab
#        (same estimator as synth.py), applied to the Standard profile's rendering of every A6300 cell.
# Usage: nature_build.py <dir with lab.py> <scripts> <pairs.npy> <Standard.dcp> <samples6.npz> <pure_correct.py> <KMODEL> <out dir>
# Writes: <out>/samples6.npz (tgt = Nature target, tgt1 = Standard render) and <out>/start.dcp (Standard profile with
# the Nature curve and an identity-ready LookTable start for pure_correct.py).
import sys,struct,os,numpy as np
LABDIR,G,PAIRS,STD,SAMPLES,PC,K,OUT=sys.argv[1:9]; K=float(K)
sys.path.insert(0,LABDIR); from lab import *
sys.path.insert(0,G); from dcp import read
os.makedirs(OUT,exist_ok=True)
src=open(PC).read(); a=src.index("def hsv(p)"); b=src.index("t=read(CUR)"); exec(src[a:b]); c0=src.index("def look_apply"); e0=src.index("cbk="); exec(src[c0:e0])
W50=np.array([0.9642,1,0.8249])
def labpp(p):
    q=np.clip(p,1e-7,None)@PP2X.T/W50; f=np.where(q>216/24389,np.cbrt(q),(24389/27*q+16)/116); return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def lab2pp(L):
    fy=(L[:,0]+16)/116; fx=fy+L[:,1]/500; fz=fy-L[:,2]/200; inv=lambda f: np.where(f**3>216/24389,f**3,(116*f-16)/(24389/27))
    return (np.stack([inv(fx),inv(fy),inv(fz)],1)*W50)@np.linalg.inv(PP2X).T
Lof=lambda y: np.where(y>216/24389,116*np.cbrt(np.maximum(y,1e-12))-16,y*24389/27)
Yof=lambda L: np.where(L>8,((L+16)/116)**3,L*27/24389)
P=np.load(PAIRS); A=lab_phocus(P[:,2:5]); B=lab_phocus(P[:,5:8])
# tone
neu=np.hypot(A[:,1],A[:,2])<3; cen=[];val=[]
for lo in np.arange(0,100,2.5):
    m=neu&(A[:,0]>=lo)&(A[:,0]<lo+2.5)
    if m.sum()>=20: cen.append(np.median(A[m,0])); val.append(np.median(B[m,0]-A[m,0]))
cen=np.array(cen); val=np.array(val); w=np.exp(-0.5*((cen[:,None]-cen[None])/4)**2); val=(w@val)/w.sum(1)
def dL(L):
    d=np.interp(L,cen,val,left=val[0],right=val[-1]); d=np.where(L>cen[-1],d*np.clip((100-L)/(100-cen[-1]),0,1),d); return d*np.clip(L/5,0,1)
t=read(STD); c=np.array(t[50940][2]); cx,cy=c[0::2],c[1::2]
x=np.linspace(0,1,1025); Ls=Lof(np.interp(x,cx,cy)); y=Yof(np.clip(Ls+dL(Ls),0,100)); y=np.maximum.accumulate(y); y=y/y[-1]; y[0]=0
print("Nature curve monotone:",bool((np.diff(y)>0).all())," | Std->Nature at Std L* 10/30/50/70/90:",[round(float(Lof(np.interp(np.interp(Yof(L),cy,cx),x,y))-L),2) for L in (10,30,50,70,90)])
# colour difference g (Standard Lab -> Nature-Standard)
d=B-A; kk=np.stack([np.floor(A[:,0]/4),np.floor(A[:,1]/3),np.floor(A[:,2]/3)],1); u,inv_=np.unique(kk,axis=0,return_inverse=True); inv_=inv_.ravel()
BC=np.array([np.median(A[inv_==j],0) for j in range(len(u))]); BD=np.array([np.median(d[inv_==j],0) for j in range(len(u))]); BN=np.minimum(np.bincount(inv_),30)
def g(q,s=(5,4,4),lam=0.5):
    out=np.zeros_like(q); conf=np.zeros(len(q))
    for i in range(0,len(q),4000):
        z=q[i:i+4000]; ww=np.exp(-0.5*(((z[:,None,:]-BC[None])/np.array(s))**2).sum(-1))*np.sqrt(BN)[None]
        out[i:i+4000]=z+(ww@BD)/(ww.sum(1)+lam)[:,None]; conf[i:i+4000]=ww.sum(1)
    return out,conf
# Standard render of the A6300 cells
Sm=np.load(SAMPLES); Hh,Ss,Vv=t[50981][2]; LT=np.array(t[50982][2]).reshape(Vv,Hh,Ss,3)
std=rgbtone(look_apply(K*Sm['base'],LT,Hh,Ss,Vv),cx,cy); q=labpp(std); tq,conf=g(q); ok=conf>2.0
print(f"A6300 cells {len(q)}, kept {ok.sum()} (conf>2); Nature-Std on kept colour cells: dC {np.median(np.hypot(tq[ok,1],tq[ok,2])-np.hypot(q[ok,1],q[ok,2])):+.2f}")
D={k:Sm[k][ok] for k in Sm.files if k not in ('tgt','tgt1')}; D['tgt']=lab2pp(tq[ok]); D['tgt1']=std[ok]
np.savez(OUT+'/samples6.npz',**D)
tags={k:(v[0],v[1],v[3]) for k,v in t.items()}; tags.pop(51110,None); pts=np.stack([x,y],1).ravel().astype('<f4'); tags[50940]=(11,pts.size,pts.tobytes())
ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
for k,(typ,cnt,raw) in ents:
    if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
    else:
        if (off+len(data))%2: data+=b'\0'
        ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
open(OUT+'/start.dcp','wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data); print("start profile written (BEO",read(OUT+'/start.dcp')[51109][2],")")
