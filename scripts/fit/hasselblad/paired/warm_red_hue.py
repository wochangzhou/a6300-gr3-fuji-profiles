# Local hue fix for reds/skin under warm light: add a smooth hue bump to the StdA HueSatMap (H1) only,
# compensate H2 so the daylight blend (weight Dc.w) is unchanged. Only the hue channel is touched.
# Usage: warm_red_hue.py <warm_matrix.py> <profile name> <out.dcp> <warm_matrix.py arguments: scripts LRP profile.dcp de2000.py ref_dir low_dir day_dir raw_dir out_dir>
# The amplitude is the grid value that nulls the red/modred/skin patch and in-band scene hue error (X1D 4.75, X2D 4.25).
import sys,struct,numpy as np
src=open(sys.argv[1]).read(); NAME=sys.argv[2]; DST=sys.argv[3]; sys.argv=[sys.argv[0]]+sys.argv[4:]
exec(src[:src.index('base=metrics(FM1,FM2,"current")')])
Hn,Sn,Vn=HD; hn=np.arange(Hn)*360/Hn; sn=np.arange(Sn)/(Sn-1)
P0,P1,R=348.0,8.0,12.0     # plateau 348..8 deg (HSM input hue), cosine ramps of 12 deg -> zero outside 336..20
def bump(h):
    d=lambda a,b:(a-b+180)%360-180
    x=np.where(d(h,P0)<0,-d(h,P0),np.where(d(h,P1)>0,d(h,P1),0.0))
    return np.where(x>=R,0.0,0.5*(1+np.cos(np.pi*x/R)))
SR=np.minimum(1,sn/0.12)                 # fade to zero toward neutrals
shape=bump(hn)[:,None]*SR[None,:]        # (H,S)
wd=Dc.w
def tables(A):
    h1=H1.copy(); h2=H2.copy(); dlt=A*shape[None]
    h1[...,0]+=dlt; h2[...,0]-=wd/(1-wd)*dlt; return h1,h2
def run(h1,h2,ds):
    FM=ds.w*FM1+(1-ds.w)*FM2; p=np.clip(ds.c@(X2PP@FM).T,0,None); b=table(p,HD,ds.w*h1+(1-ds.w)*h2,False)
    gg=g if ds in (Lc,Ld) else 1.0
    return tone(table(np.clip(K*gg*b,0,1),LD,LTB,True),CV)
hue=lambda L:np.degrees(np.arctan2(L[:,2],L[:,1]))%360
LB=lab(Ld.tgt); hB=hue(LB); CB=np.hypot(LB[:,1],LB[:,2])
pin=np.clip(Ld.c@(X2PP@FM1).T,0,None); hin,sin_,_=hsv(pin); inband=ok&~wh&(bump(hin)>0.5)&(sin_>0.12)&(CB>8)
FIT=[NAMES.index(n) for n in ("red","modred","skin")]
def score(A):
    h1,h2=tables(A); oc=run(h1,h2,Lc); od=run(h1,h2,Ld)
    dp=(hue(lab(oc[FIT]))-hue(lab(cTl[FIT]))+180)%360-180; ds=(hue(lab(od[inband]))-hB[inband]+180)%360-180
    return np.abs(dp).mean()+abs(np.median(ds)), dp, np.median(ds)
grid=np.arange(0,16.01,0.25); sc=[score(a)[0] for a in grid]; A=grid[int(np.argmin(sc))]
print(f"in-band scene cells {inband.sum()}; best amplitude A = {A:+.2f} deg")
for a in (0.0,A):
    s,dp,dsm=score(a); print(f"  A={a:5.2f}: patch dh red/modred/skin {np.round(dp,1).tolist()}  scene in-band median dh {dsm:+.2f}")
h1,h2=tables(A)
# ---- verification
o0=run(H1,H2,Lc); o1=run(h1,h2,Lc); d0=run(H1,H2,Dc); d1=run(h1,h2,Dc); s0=run(H1,H2,Ld); s1=run(h1,h2,Ld); z0=run(H1,H2,Dd); z1=run(h1,h2,Dd)
print("lowlight chart dE to target, before -> after:")
for i,n in enumerate(NAMES):
    a,b=de(o0[[i]],cTl[[i]])[0],de(o1[[i]],cTl[[i]])[0]; ch=de(o0[[i]],o1[[i]])[0]
    print(f"  {n:13s} {a:5.2f} -> {b:5.2f}   (change {ch:4.2f})")
cc=np.arange(24)<18; print(f"lowlight chart colour mean {de(o0[cc],cTl[cc]).mean():.3f} -> {de(o1[cc],cTl[cc]).mean():.3f}")
out=ok&~wh&~inband; chg=de(s0[out][::3],s1[out][::3]); print(f"lowlight scene cells OUTSIDE band: change dE mean {chg.mean():.4f} max {chg.max():.3f} (n {len(chg)})")
chg=de(s0[inband],s1[inband]); print(f"lowlight scene cells in band: change dE mean {chg.mean():.2f}; dE to target {de(s0[inband],Ld.tgt[inband]).mean():.2f} -> {de(s1[inband],Ld.tgt[inband]).mean():.2f}")
print(f"DAYLIGHT chart max change dE {de(d0,d1).max():.2e}; daylight scene cells max change {de(z0[::7],z1[::7]).max():.2e}")
GI=[NAMES.index(n) for n in ("white","n8","n6.5","n5","n3.5","black")]; print(f"lowlight greys max change {de(o0[GI],o1[GI]).max():.2e}")
# ---- write DCP (only 50938/50939 and name change)
tags={k:(v[0],v[1],v[3]) for k,v in t.items()}
for k,tb in ((50938,h1),(50939,h2)): f=tb.astype('<f4').ravel(); tags[k]=(11,len(f),f.tobytes())
nm=(NAME+"\0").encode(); tags[50936]=(2,len(nm),nm)
ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
for k,(typ,cnt,raw) in ents:
    if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
    else:
        if (off+len(data))%2: data+=b'\0'
        ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
open(DST,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data)
r=read(DST); print("built",r[50936][2],"| differing tags vs source:",sorted(k for k in set(r)|set(t) if k not in r or k not in t or r[k][3]!=t[k][3]))
