# Nature tone curve from the X2D Phocus Standard->Nature pair (nature_pairs.py): on neutral cells, dL(L_std)
# (2.5-L* bands, smoothed, tapered at both ends); Nature curve = Y(L_std + dL), L_std = the Standard profile's own curve output.
# Writes START for analytic.py: the Standard profile with this curve (no DefaultBlackRender).
# Usage: nature_tone.py <dir with lab.py> <scripts> <pairs.npy> <Standard.dcp> <out start.dcp>
import sys,struct,numpy as np
LABDIR,G,PAIRS,STD,OUT=sys.argv[1:6]
sys.path.insert(0,LABDIR); from lab import *
sys.path.insert(0,G); from dcp import read
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
tags={k:(v[0],v[1],v[3]) for k,v in t.items()}; tags.pop(51110,None); pts=np.stack([x,y],1).ravel().astype('<f4'); tags[50940]=(11,pts.size,pts.tobytes())
ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
for k,(typ,cnt,raw) in ents:
    if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
    else:
        if (off+len(data))%2: data+=b'\0'
        ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
open(OUT,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data); print("wrote",OUT)
