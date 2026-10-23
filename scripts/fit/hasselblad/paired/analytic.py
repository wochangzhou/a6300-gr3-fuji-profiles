# Node-exact LookTable: for every LookTable node X (exposure-scaled base colour), render it the way the source profile
# does (SRC: its LookTable with its own value encoding, then its tone curve), map the result with g (Lab kernel
# regression learned on same-camera pairs), and solve for the node value that makes THIS profile (its tone curve,
# hue-preserving RGB tone) produce that target. No scene sampling: every node is defined.
# Then: top two value layers copied from the layer below (the tone curve is too flat there to invert), clamp
# (hue +-25 deg, sat x0.6-1.6, value x0.85-1.15), neutral axis identity (tone only from the curve), corrections faded
# to identity below HSV saturation 0.12. Run monotone.py afterwards.
# Usage: analytic.py <lab dir> <scripts> <pairs.npy> <src lab: lr|phocus> <target lab: lr|phocus> <SRC.dcp | "as:<Adobe Standard.dcp>:<acr3.txt>"> <START.dcp> <H> <S> <V> <name> <note> <out.dcp>
# (used: 90 32 32; Standard: SRC = the A6300 Adobe Standard, pairs = cm_pairs.py output, lr lr, START = cm_tone.py output;
#  Nature: SRC = the Standard built here, pairs = nature_pairs.py output, phocus phocus, START = nature_tone.py output)
import sys,struct,numpy as np
LABDIR,G,PAIRS,SRCLAB,TGTLAB,SRC,START,HD,SD,VD,NAME,NOTE,OUT=sys.argv[1:14]; HD,SD,VD=int(HD),int(SD),int(VD)
sys.path.insert(0,LABDIR); from lab import *
sys.path.insert(0,G); from dcp import read
SIG=np.array([4.0,10.0,10.0]); LAM=0.02; FADE=0.5      # g parameters chosen by left/right-half cross-validation
W50=np.array([0.9642,1,0.8249])
def labpp(p):
    q=np.clip(p,1e-7,None)@PP2X.T/W50; f=np.where(q>216/24389,np.cbrt(q),(24389/27*q+16)/116); return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def lab2pp(L):
    fy=(L[:,0]+16)/116; fx=fy+L[:,1]/500; fz=fy-L[:,2]/200; inv=lambda f: np.where(f**3>216/24389,f**3,(116*f-16)/(24389/27))
    return (np.stack([inv(fx),inv(fy),inv(fz)],1)*W50)@np.linalg.inv(PP2X).T
enc=lambda x:np.where(x<=0.0031308,12.92*x,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
dec=lambda y:np.where(y<=0.04045,y/12.92,((np.clip(y,0,None)+0.055)/1.055)**2.4)
def hsv(p):
    mx=p.max(-1); mn=p.min(-1); g_=mx-mn; s=np.where(mx>0,g_/np.maximum(mx,1e-12),0); r,gg,b=p[...,0],p[...,1],p[...,2]; gs=np.maximum(g_,1e-12)
    h=np.where(mx==r,((gg-b)/gs)%6,np.where(mx==gg,2+(b-r)/gs,4+(r-gg)/gs)); return np.where(g_>0,h*60,0),s,mx
def hsv2rgb(h,s,v):
    h=(h/60)%6; i=np.floor(h).astype(int)%6; f=h-np.floor(h); p=v*(1-s); q=v*(1-s*f); t=v*(1-s*(1-f))
    return np.stack([np.choose(i,[v,q,p,p,t,v]),np.choose(i,[t,v,v,q,p,p]),np.choose(i,[p,p,t,v,v,q])],-1)
def rgbtone(p,cx,cy):
    p=np.clip(p,0,1); o=np.argsort(p,-1); lo=np.take_along_axis(p,o[...,:1],-1); hi=np.take_along_axis(p,o[...,2:],-1); mi=np.take_along_axis(p,o[...,1:2],-1)
    L=np.interp(lo,cx,cy); Hh=np.interp(hi,cx,cy); M=L+(Hh-L)*np.where(hi>lo,(mi-lo)/np.maximum(hi-lo,1e-12),0)
    out=np.empty_like(p); np.put_along_axis(out,o[...,:1],L,-1); np.put_along_axis(out,o[...,1:2],M,-1); np.put_along_axis(out,o[...,2:],Hh,-1); return out
def look(X,LT,dims,encoding):   # DNG LookTable (V,H,S order), trilinear, hue wrap
    Hh,Ss,Vv=dims; h,s,v=hsv(X); ve=enc(v) if encoding else v
    hs=h/360*Hh; h0=np.floor(hs).astype(int)%Hh; h1=(h0+1)%Hh; hf=hs-np.floor(hs)
    ss=np.clip(s,0,1)*(Ss-1); s0=np.minimum(ss.astype(int),Ss-2); sf=ss-s0; vs=np.clip(ve,0,1)*(Vv-1); v0=np.minimum(vs.astype(int),Vv-2); vf=vs-v0
    acc=0
    for vi,wv in ((v0,1-vf),(v0+1,vf)):
        for hi,wh in ((h0,1-hf),(h1,hf)):
            for si,ws in ((s0,1-sf),(s0+1,sf)): acc=acc+LT[vi,hi,si]*(wv*wh*ws)[:,None]
    vo=dec(np.minimum(ve*acc[:,2],1)) if encoding else np.minimum(v*acc[:,2],1)
    return hsv2rgb(h+acc[:,0],np.minimum(s*acc[:,1],1),vo)
def tbl(t): d=t[50981][2]; return np.array(t[50982][2]).reshape(d[2],d[0],d[1],3),tuple(d),(t[51108][2][0] if 51108 in t else 0)
def curve(t): c=np.array(t[50940][2]); return c[0::2],c[1::2]
# source renderer
if SRC.startswith("as:"):
    _,asdcp,acr3=SRC.split(":"); ta=read(asdcp); LTs,ds,es=tbl(ta); a=np.loadtxt(acr3); scx,scy=np.linspace(0,1,len(a)),a
else:
    ts=read(SRC); LTs,ds,es=tbl(ts); scx,scy=curve(ts)
def render_src(X): return rgbtone(look(X,LTs,ds,es),scx,scy)
# g
Pp=np.load(PAIRS); A=lab_lr(Pp[:,2:5]) if SRCLAB=="lr" else lab_phocus(Pp[:,2:5]); B=lab_lr(Pp[:,5:8]) if TGTLAB=="lr" else lab_phocus(Pp[:,5:8])
k=np.stack([np.floor(A[:,0]/4),np.floor(A[:,1]/3),np.floor(A[:,2]/3)],1); u,inv_=np.unique(k,axis=0,return_inverse=True); inv_=inv_.ravel()
BC=np.array([np.median(A[inv_==j],0) for j in range(len(u))]); BD=np.array([np.median((B-A)[inv_==j],0) for j in range(len(u))]); BN=np.minimum(np.bincount(inv_),30)
def g(q):
    out=np.zeros_like(q); conf=np.zeros(len(q))
    for i in range(0,len(q),2000):
        z=q[i:i+2000]; w=np.exp(-0.5*(((z[:,None,:]-BC[None])/SIG)**2).sum(-1))*np.sqrt(BN)[None]; ws=w.sum(1)
        out[i:i+2000]=z+(w@BD)/(ws+LAM)[:,None]*np.minimum(1,ws/FADE)[:,None]; conf[i:i+2000]=ws
    return out,conf
# this profile
t=read(START); cx,cy=curve(t)
def solve(X):
    q=labpp(render_src(X)); tq,conf=g(q); T=np.clip(lab2pp(tq),0,1)
    return rgbtone(T,cy,cx),conf      # hue-preserving inverse of this profile's tone curve
hh=np.arange(HD)*360/HD; sv=np.arange(SD)/(SD-1); vv=np.arange(VD)/(VD-1)
Hg,Sg,Vg=np.meshgrid(hh,sv,vv,indexing='ij'); Xn=hsv2rgb(Hg.ravel(),Sg.ravel(),dec(Vg.ravel()))
Zn,conf=solve(Xn); hX,sX,vX=hsv(Xn); hZ,sZ,vZ=hsv(Zn)
dh=np.where(sX>0,((hZ-hX)+180)%360-180,0); sr=np.where(sX>0,sZ/np.maximum(sX,1e-6),1); vr=np.where(vX>1e-6,enc(vZ)/np.maximum(enc(vX),1e-9),1)
dh=np.where(sZ<1e-4,0,dh)
LT=np.stack([dh,sr,vr],-1).reshape(HD,SD,VD,3).transpose(2,0,1,3).astype('<f4')   # -> V,H,S
LT[0]=[0,1,1]
CL=[25,0.6,1.6,0.85,1.15]
TOPV=2                                                         # top value layers copied from the layer below
for vi in range(VD-TOPV,VD): LT[vi]=LT[VD-TOPV-1]
LT[...,0]=np.clip(LT[...,0],-CL[0],CL[0]); LT[...,1]=np.clip(LT[...,1],CL[1],CL[2]); LT[...,2]=np.clip(LT[...,2],CL[3],CL[4])
LT[:,:,0,:]=[0,1,1]                                           # neutral axis: tone comes from the curve only
SF=0.12                                                        # fade corrections to identity below this HSV saturation
if SF>0:
    f=np.minimum(1,(np.arange(SD)/(SD-1))/SF)[None,None,:]
    LT[...,0]*=f; LT[...,1]=1+(LT[...,1]-1)*f; LT[...,2]=1+(LT[...,2]-1)*f
print(f"nodes {LT.shape} | dh |mean| {np.abs(LT[...,0]).mean():.2f} max {np.abs(LT[...,0]).max():.1f} | sat x {LT[...,1].min():.3f}..{LT[...,1].max():.3f} | val x {LT[...,2].min():.3f}..{LT[...,2].max():.3f} | neutral nodes val x {LT[:,:,0,2].min():.3f}..{LT[:,:,0,2].max():.3f} | nodes with g support (conf>0.5) {(conf>0.5).mean()*100:.0f}%")
tags={k_:(v[0],v[1],v[3]) for k_,v in t.items()}; tags.pop(51110,None)
tags[50981]=(4,3,struct.pack('<3I',HD,SD,VD)); tags[50982]=(11,LT.size,LT.ravel().tobytes()); tags[51108]=(4,1,struct.pack('<I',1))
for k_,s_ in ((50936,NAME),(50942,NOTE)): e=(s_+'\0').encode(); tags[k_]=(2,len(e),e)
ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
for k_,(typ,cnt,raw) in ents:
    if len(raw)<=4: ifd+=struct.pack('<HHI',k_,typ,cnt)+raw.ljust(4,b'\0')
    else:
        if (off+len(data))%2: data+=b'\0'
        ifd+=struct.pack('<HHII',k_,typ,cnt,off+len(data)); data+=raw
open(OUT,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data); print("wrote",OUT)
