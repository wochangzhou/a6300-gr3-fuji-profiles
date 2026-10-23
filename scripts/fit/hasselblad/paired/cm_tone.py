# Camera Matching tone curve on top of the Adobe Standard rendering: on near-neutral pair cells (AS C*<3), map the
# Lightroom Adobe Standard luminance to the Camera Matching luminance (median per 2.5-L* band, smoothed, monotone),
# then new ProfileToneCurve = T(ACR3(x)). Writes the starting DCP for analytic.py: the A6300 Adobe Standard
# matrices and HueSatMap, an identity 90x16x16 LookTable (sRGB-encoded value axis), this curve, BEO 0, no DefaultBlackRender.
# Usage: cm_tone.py <dir with lab.py> <scripts> <pairs.npy (cm_pairs.py)> <ACR3 curve .txt> <Sony ILCE-6300 Adobe Standard.dcp> <out.dcp>
import sys,struct,numpy as np
sys.path.insert(0,sys.argv[1]); from lab import *
sys.path.insert(0,sys.argv[2]); from dcp import read
PAIRS,ACR3,CUR,OUT=sys.argv[3:7]
R=np.load(PAIRS); A=lab_lr(R[:,2:5]); B=lab_lr(R[:,5:8]); neu=np.hypot(A[:,1],A[:,2])<3
Y=lambda L: np.where(L>8,((L+16)/116)**3,L*27/24389)
cen=[];val=[]
for lo in np.arange(0,100,2.5):
    m=neu&(A[:,0]>=lo)&(A[:,0]<lo+2.5)
    if m.sum()>=20: cen.append(np.median(A[m,0])); val.append(np.median(B[m,0]-A[m,0]))
cen=np.array(cen); val=np.array(val); w=np.exp(-0.5*((cen[:,None]-cen[None])/4)**2); val=(w@val)/w.sum(1)
print("L* bands",cen.round(0).astype(int).tolist()); print("CM-AS dL",val.round(2).tolist())
a=np.loadtxt(ACR3); ax=np.linspace(0,1,len(a))
x=np.linspace(0,1,1025); yA=np.interp(x,ax,a); LA=np.where(yA>216/24389,116*np.cbrt(np.maximum(yA,1e-12))-16,yA*24389/27)
dLc=np.interp(LA,cen,val,left=0.0,right=val[-1]); top=cen[-1]; dLc=np.where(LA>top,dLc*np.clip((100-LA)/(100-top),0,1),dLc); dLc=dLc*np.clip(LA/5,0,1)  # taper to 0 at L*100 and at L*0: no clipping at either end
LP=LA+dLc; LP[0]=0; y=Y(np.clip(LP,0,100))
y=np.maximum.accumulate(y); y=y/y[-1]; y[0]=0
print('  monotone & no flat top:', bool((np.diff(y)>0).all()), '| shadow slope %.3f' % ((y[20]-y[0])/(x[20]-x[0])), '| slope near white %.3f' % ((y[-1]-y[-20])/(x[-1]-x[-20])))
for xx in (0.05,0.1,0.18,0.3,0.5,0.8,0.95): yy=np.interp(xx,x,y); print(f"  x {xx:.2f}: ACR3 L* {np.interp(xx,x,LA):5.1f} -> CM L* {(116*np.cbrt(yy)-16 if yy>216/24389 else yy*24389/27):5.1f}")
t=read(CUR); tags={k:(v[0],v[1],v[3]) for k,v in t.items() if k not in (50981,50982,51110)}
lt=np.zeros((16,90,16,3),'<f4'); lt[...,1:]=1; tags[50981]=(4,3,struct.pack('<3I',90,16,16)); tags[50982]=(11,lt.size,lt.ravel().tobytes()); tags[51108]=(4,1,struct.pack('<I',1))
pts=np.stack([x,y],1).ravel().astype('<f4'); tags[50940]=(11,pts.size,pts.tobytes()); tags[51109]=(10,1,struct.pack('<iI',0,10000))
ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
for k,(typ,cnt,raw) in ents:
    if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
    else:
        if (off+len(data))%2: data+=b'\0'
        ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
open(OUT,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data); print("wrote",OUT)
