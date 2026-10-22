# Monotone chroma along input saturation: for every (value, hue) column of the LookTable, walk the saturation nodes and,
# where a node's rendered chroma (through this profile's tone curve) is below the previous node's, raise that node's
# saturation multiplier (bisection) until it is not. Only those nodes change, and only upward.
# Usage: monotone.py <lab dir> <scripts> <in.dcp> <out.dcp>
import sys,os,struct,numpy as np
LABDIR,G,INP,OUTP=sys.argv[1:5]
sys.path.insert(0,G); from dcp import read
sys.path.insert(0,LABDIR); from lab import *
src=open(os.path.dirname(os.path.abspath(sys.argv[0]))+'/analytic.py').read(); a=src.index("W50=np.array"); b=src.index("def tbl(t)"); exec(src[a:b])
t=read(INP); Hh,Ss,Vv=t[50981][2]; LT=np.array(t[50982][2]).reshape(Vv,Hh,Ss,3).copy(); c=np.array(t[50940][2]); cx,cy=c[0::2],c[1::2]
hh=np.arange(Hh)*360/Hh; sv=np.arange(Ss)/(Ss-1); vv=np.arange(Vv)/(Vv-1)
def chroma_at(vi,si,sr,f):   # chroma at fraction f between node si-1 and si (DNG linear interpolation of node params)
    n0=LT[vi,:,si-1]; n1=LT[vi,:,si]; dh=(1-f)*n0[:,0]+f*n1[:,0]; srr=(1-f)*n0[:,1]+f*sr; vr=(1-f)*n0[:,2]+f*n1[:,2]
    s_=sv[si-1]+(sv[si]-sv[si-1])*f; Z=hsv2rgb(hh+dh,np.minimum(s_*srr,1),dec(np.minimum(vv[vi]*vr,1))); L=labpp(rgbtone(Z,cx,cy)); return np.hypot(L[:,1],L[:,2])
FR=(0.25,0.5,0.75,1.0)
def worst(vi,si,sr,prev):   # running max must not drop anywhere in the interval
    m=prev.copy(); ok=np.ones(Hh,bool)
    for f in FR: c=chroma_at(vi,si,sr,f); ok&=c>=m-1e-3; m=np.maximum(m,c)
    return ok,m
changed=0; maxup=1.0
for vi in range(1,Vv):
    prev=np.zeros(Hh)
    for si in range(1,Ss):
        ok,m=worst(vi,si,LT[vi,:,si,1],prev)
        if (~ok).any() and si>=2:
            lo=LT[vi,:,si,1].copy(); hi=np.full(Hh,1.0/sv[si])
            for _ in range(30):
                mid=(lo+hi)/2; okm,_=worst(vi,si,mid,prev); hi=np.where(okm,mid,hi); lo=np.where(okm,lo,mid)
            new=np.where(ok,LT[vi,:,si,1],hi); maxup=max(maxup,float((new/LT[vi,:,si,1]).max())); changed+=int((~ok).sum()); LT[vi,:,si,1]=new
            ok,m=worst(vi,si,LT[vi,:,si,1],prev)
        prev=m
print(f"nodes raised: {changed} of {Vv*Hh*Ss} | largest raise x{maxup:.3f}")
tags={k:(v[0],v[1],v[3]) for k,v in t.items()}; flat=LT.astype('<f4').ravel(); tags[50982]=(11,flat.size,flat.tobytes())
ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
for k,(typ,cnt,raw) in ents:
    if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
    else:
        if (off+len(data))%2: data+=b'\0'
        ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
open(OUTP,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data)
