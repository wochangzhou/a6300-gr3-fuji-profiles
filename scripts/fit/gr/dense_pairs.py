# Dense A6300 <-> GR cell pairs from the dpreview studio RAWs (linear camera RGB from scripts/raw/decode.py).
# 1. registration: affine from known points (chart corner patches, wheel centre, the four portraits), then per-tile
#    shifts on log-luminance gradients (/4 grid) and a robust cubic polynomial warp A -> GR;
# 2. flat 4x4 cells on the A6300 /4 grid (16x16 RAW px), GR sampled through the warp;
# 3. position-dependent light (lens fall-off, studio light) removed from the GR camera RGB: per channel, log(GR/A6300)
#    on neutral cells fitted as a 2-D polynomial of position, normalised to 0 at the colour chart;
# 4. each camera's Adobe Standard base colour (rawbase.py: WB from chart greys, exposure on chart white).
# Usage: dense_pairs.py <scripts> <LR CameraProfiles> <a6300_lin.npy> <gr_lin.npy> <gr3|gr4> <patches_raw.json> <out.npz>
import sys,json,math,numpy as np
GS,LRP,ALIN,BLIN,CAM,PATCHES,OUTNPZ=sys.argv[1:8]
sys.argv=[sys.argv[0],GS,LRP,'.','/dev/null']; sys.path.insert(0,GS); S=GS
src=open(GS+'/rawbase.py').read(); exec(src[src.index('from dcp import read'):src.index('P=json.load(open(PATCHES))')])
A=np.load(ALIN,mmap_mode='r'); B=np.load(BLIN,mmap_mode='r')
def box(a,f):
    h,w=a.shape[0]//f*f,a.shape[1]//f*f; out=np.zeros((h//f,w//f,3),np.float32)
    for i in range(0,h,f*256): out[i//f:(i+f*256)//f]=np.asarray(a[i:min(i+f*256,h),:w],np.float32).reshape(-1,f,w//f,f,3).mean((1,3))
    return out
F=4; A4=box(A,F); B4=box(B,F)
# known points (full-res RAW px)
CH={"a6300":((2409,501),(134,127,1064,676)),"gr3":((2357,451),(176,153,1117,706)),"gr4":((2515,492),(130,150,1090,710))}
WH={"a6300":((3724,461),(207,195),553/400),"gr3":((3737,441),(205,197),552/400),"gr4":((3877,466),(200,200),1.42)}
FC={"a6300":(6.024,[(138,300),(137,395),(862,295),(862,398)]),"gr4":(6.224,[(140,303),(140,402),(865,300),(862,402)]),"gr3":(6.020,[(133,298),(132,395),(866,292),(862,395)])}
def pts(c):
    (ox,oy),(x0,y0,x1,y1)=CH[c]; (wx,wy),(cx,cy),f=WH[c]; k,fc=FC[c]
    return np.array([(ox+x0,oy+y0),(ox+x1,oy+y1),(ox+x0,oy+y1),(ox+x1,oy+y0),(wx+cx*f,wy+cy*f)]+[(x*k,y*k) for x,y in fc],float)
PA,PB=pts("a6300"),pts(CAM); Maff=np.linalg.lstsq(np.c_[PA,np.ones(len(PA))],PB,rcond=None)[0]
print("affine residual on known points (px):",np.abs(np.c_[PA,np.ones(len(PA))]@Maff-PB).max().round(1))
def bil(img,x,y):
    x=np.clip(x,0,img.shape[1]-2); y=np.clip(y,0,img.shape[0]-2); x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); fx=(x-x0)[...,None]; fy=(y-y0)[...,None]
    return img[y0,x0]*(1-fx)*(1-fy)+img[y0,x0+1]*fx*(1-fy)+img[y0+1,x0]*(1-fx)*fy+img[y0+1,x0+1]*fx*fy
def poly(x,y,deg):
    u,v=(x-3000)/3000,(y-2000)/3000; return np.stack([u**i*v**j for i in range(deg+1) for j in range(deg+1-i)],-1)
h,w,_=A4.shape; yy,xx=np.mgrid[0:h,0:w].astype(np.float64); fxA=xx*F+F/2; fyA=yy*F+F/2
def warp(fx,fy,C=None):
    q=np.stack([fx,fy,np.ones_like(fx)],-1)@Maff
    if C is not None: Pm=poly(fx,fy,3); q=q+np.stack([Pm@C[0],Pm@C[1]],-1)
    return q[...,0],q[...,1]
lum=lambda im: np.log(im@np.array([0.3,0.6,0.1])+20)
gA=np.hypot(*np.gradient(lum(A4)))
C=None
for it in range(2):
    bx,by=warp(fxA,fyA,C); Bw=bil(B4,bx/F-0.5,by/F-0.5); gB=np.hypot(*np.gradient(lum(Bw)))
    T=40; Rr=8 if it==0 else 4; offs=[]
    for ty in range(T,h-T,T//2):
        for tx in range(T,w-T,T//2):
            a=gA[ty-T//2:ty+T//2,tx-T//2:tx+T//2]
            if a.std()<0.05: continue
            a=(a-a.mean())/a.std(); best=(-1,0,0)
            for dy in range(-Rr,Rr+1):
                for dx in range(-Rr,Rr+1):
                    b=gB[ty-T//2+dy:ty+T//2+dy,tx-T//2+dx:tx+T//2+dx]
                    if b.shape!=a.shape: continue
                    v=(a*(b-b.mean())).mean()/(b.std()+1e-9)
                    if v>best[0]: best=(v,dx,dy)
            if best[0]>0.5 and abs(best[1])<Rr and abs(best[2])<Rr: offs.append((tx*F+F/2,ty*F+F/2,best[1],best[2]))
    o=np.array(offs); fx,fy=o[:,0],o[:,1]
    # tile shift (in warped-B /4 px) -> needed correction of B coordinates: B(x+dx) matches A(x); express in full-res B px via local Jacobian ~ affine scale
    bx0,by0=warp(fx,fy,C); bx1,by1=warp(fx+o[:,2]*F,fy+o[:,3]*F,C); tx_,ty_=bx1-bx0,by1-by0
    Pm=poly(fx,fy,3); Cx=np.zeros(Pm.shape[1]); Cy=np.zeros(Pm.shape[1]); wgt=np.ones(len(o),bool)
    prevx=Pm@C[0] if C is not None else 0; prevy=Pm@C[1] if C is not None else 0
    for _ in range(5):
        Cx=np.linalg.lstsq(Pm[wgt],(prevx+tx_)[wgt],rcond=None)[0]; Cy=np.linalg.lstsq(Pm[wgt],(prevy+ty_)[wgt],rcond=None)[0]
        r=np.hypot(Pm@Cx-(prevx+tx_),Pm@Cy-(prevy+ty_)); wgt=r<max(3*np.median(r),2*F)
    C=(Cx,Cy); print(f"iter {it}: tiles {len(o)}, inliers {wgt.sum()}, residual median {np.median(r[wgt]):.1f} px (full res)")
# cells
bx,by=warp(fxA,fyA,C); Bw=bil(B4,bx/F-0.5,by/F-0.5)
Pa=json.load(open(PATCHES)); C4=4; rows=[]
for y in range(0,h-C4,C4):
    for x in range(0,w-C4,C4):
        a=A4[y:y+C4,x:x+C4].reshape(-1,3); b=Bw[y:y+C4,x:x+C4].reshape(-1,3)
        if a.mean()<=50 or b.mean()<=50: continue
        if (a.std(0)/np.maximum(a.mean(0),1)).max()>0.06 or (b.std(0)/np.maximum(b.mean(0),1)).max()>0.08: continue
        if a.max()>0.9*Pa['a6300']['white'][1]*1.6 or b.max()>0.9*Pa[CAM]['white'][1]*1.6: continue
        rows.append(((x+C4/2)*F,(y+C4/2)*F,*a.mean(0),*b.mean(0)))
R=np.array(rows); print("flat cells",len(R))
def basefun(cam,prof):
    t=read(f"{LRP}/Adobe Standard/{prof} Adobe Standard.dcp"); p=Pa[cam]; n=[p['n8'][k]+p['n6.5'][k]+p['n5'][k] for k in range(3)]; s=n[1]; n=[x/s for x in n]
    f,T,wt=base_fn(t)(n); sc=0.9/(p['white'][1]/n[1]); return lambda v: f([x*sc for x in v])
fA=basefun('a6300','Sony ILCE-6300'); fB=basefun(CAM,{'gr3':'RICOH GR III','gr4':'RICOH GR IV'}[CAM])
bA=np.array([fA(v) for v in R[:,2:5]])
def hsv_(p):
    mx=p.max(-1); mn=p.min(-1); g=mx-mn; return np.where(mx>0,g/np.maximum(mx,1e-12),0)
# light field on neutral cells (camera RGB ratios), normalised at the chart centre
(ox,oy),(x0,y0,x1,y1)=CH['a6300']; cxA,cyA=ox+(x0+x1)/2,oy+(y0+y1)/2
bB0=np.array([fB(v) for v in R[:,5:8]]); neu=(hsv_(bA)<0.05)&(hsv_(bB0)<0.05)
lr=np.log(R[:,5:8]/R[:,2:5]); Pm=poly(R[:,0],R[:,1],4); P0=poly(np.array([cxA]),np.array([cyA]),4)[0]; field=np.zeros((len(R),3))
for c in range(3):
    m=neu.copy()
    for _ in range(4):
        k=np.linalg.lstsq(Pm[m],lr[m,c],rcond=None)[0]; r=lr[:,c]-Pm@k; m=neu&(np.abs(r)<3*np.median(np.abs(r[neu]))*1.4826)
    field[:,c]=Pm@k-P0@k
print("light field GR/A6300 (rel. to chart): p5..p95 per channel", np.percentile(np.exp(field),[5,95],axis=0).round(3).tolist(), "| neutral cells",neu.sum())
Bc=R[:,5:8]*np.exp(-field); bB=np.array([fB(v) for v in Bc])
wheels=[(WH['a6300'][0][0]+WH['a6300'][1][0]*WH['a6300'][2],WH['a6300'][0][1]+WH['a6300'][1][1]*WH['a6300'][2],170*WH['a6300'][2]),(1998,3276,240*2)]
wh=np.array([any((x-a)**2+(y-b)**2<r*r for a,b,r in wheels) for x,y in R[:,:2]])
np.savez(OUTNPZ,xy=R[:,:2],camA=R[:,2:5],camB=Bc,baseA=bA,baseB=bB,wheel=wh)
print(f"saved {len(R)} pairs (wheel {wh.sum()})")
