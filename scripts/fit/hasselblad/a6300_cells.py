# A6300 cells for the Hasselblad transfer: flat 6x6 cells on the /2 work grid of the A6300 RAW (linear camera RGB from
# scripts/raw/decode.py), their Adobe Standard base colours (white balance -> ForwardMatrix -> HueSatMap, exposure
# normalised on the chart white, as rawbase.py), and the matching position in the Lightroom Adobe Standard export
# (lens correction off) from a block registration RAW -> export (affine + quadratic, on log-luminance gradients).
# The two colour wheels are flagged and kept out of training.
# Usage: a6300_cells.py <scripts> <LR CameraProfiles> <a6300_lin.npy> <patches_raw.json> <export.tif> <out.npz>
import sys,json,numpy as np,tifffile
GS,LRP,LIN,PATCHES,EXPORT,OUTNPZ=sys.argv[1:7]
sys.argv=[sys.argv[0],GS,LRP,'.','/dev/null']; sys.path.insert(0,GS)
S=GS; src=open(GS+'/rawbase.py').read(); exec(src[src.index('from dcp import read'):src.index('P=json.load(open(PATCHES))')])
def box(a,f):
    h,w=a.shape[0]//f*f,a.shape[1]//f*f; out=np.zeros((h//f,w//f,3),np.float32)
    for i in range(0,h,f*256): out[i//f:(i+f*256)//f]=np.asarray(a[i:min(i+f*256,h),:w],np.float32).reshape(-1,f,w//f,f,3).mean((1,3))
    return out
Acam=box(np.load(LIN,mmap_mode='r'),2)           # RAW work grid (camera linear, raw units)
E2=box(tifffile.memmap(EXPORT),2)                 # export work grid (ProPhoto gamma 1.8, 16-bit)
# registration RAW work -> export work
fa=np.hypot(*np.gradient(np.log(Acam@[0.3,0.6,0.1]+50))); fb=np.hypot(*np.gradient(np.log(E2.mean(2)+50)))
T=96; Rr=16; pts=[]
for y in range(Rr+T//2,fa.shape[0]-Rr-T//2,T):
    for x in range(Rr+T//2,fa.shape[1]-Rr-T//2,T):
        a=fa[y-T//2:y+T//2,x-T//2:x+T//2]
        if a.std()<0.01: continue
        a=(a-a.mean())/a.std(); sc_=np.full((2*Rr+1,2*Rr+1),-9.0)
        for dy in range(-Rr,Rr+1):
            for dx in range(-Rr,Rr+1):
                yy,xx=y+dy,x+dx
                if yy-T//2<0 or xx-T//2<0 or yy+T//2>fb.shape[0] or xx+T//2>fb.shape[1]: continue
                b=fb[yy-T//2:yy+T//2,xx-T//2:xx+T//2]; sc_[dy+Rr,dx+Rr]=(a*(b-b.mean())).mean()/(b.std()+1e-9)
        iy,ix=np.unravel_index(sc_.argmax(),sc_.shape)
        if sc_[iy,ix]<0.5 or iy in (0,2*Rr) or ix in (0,2*Rr): continue
        sub=lambda m,c,p:(m-p)/(2*(m-2*c+p)) if (m-2*c+p)!=0 else 0
        pts.append((x,y,ix-Rr+sub(sc_[iy,ix-1],sc_[iy,ix],sc_[iy,ix+1]),iy-Rr+sub(sc_[iy-1,ix],sc_[iy,ix],sc_[iy+1,ix])))
Pp=np.array(pts); u=(Pp[:,0]-1500)/1500; v=(Pp[:,1]-1000)/1500
Fm=lambda u,v: np.stack([np.ones_like(u),u,v,u*u,u*v,v*v],-1)
cx=np.linalg.lstsq(Fm(u,v),Pp[:,2],rcond=None)[0]; cy=np.linalg.lstsq(Fm(u,v),Pp[:,3],rcond=None)[0]
rx=Pp[:,2]-Fm(u,v)@cx; ry=Pp[:,3]-Fm(u,v)@cy
print(f"registration blocks {len(Pp)}, shift x {Pp[:,2].min():.1f}..{Pp[:,2].max():.1f}, y {Pp[:,3].min():.1f}..{Pp[:,3].max():.1f}, residual rms {np.sqrt((rx**2).mean()):.2f}/{np.sqrt((ry**2).mean()):.2f} px")
# base colours
P=json.load(open(PATCHES))['a6300']; t=read(f"{LRP}/Adobe Standard/Sony ILCE-6300 Adobe Standard.dcp")
neutral=[P['n8'][k]+P['n6.5'][k]+P['n5'][k] for k in range(3)]; s=neutral[1]; neutral=[x/s for x in neutral]
f,Tc,w=base_fn(t)(neutral); sc=0.9/(P['white'][1]/neutral[1])
wheels=[((3724+207*553/400)/2,(461+195*553/400)/2,170/2*553/400*2),(1998/2,3276/2,240)]
C=6; rows=[]; h,w_,_=Acam.shape
for y in range(0,h-C,C):
    for x in range(0,w_-C,C):
        a=Acam[y:y+C,x:x+C].reshape(-1,3); la=a@[0.3,0.6,0.1]
        if la.mean()<=0 or la.std()/la.mean()>0.08 or (a.std(0)/np.maximum(a.mean(0),1)).max()>0.12 or a.max()>0.9*P['white'][1]*1.6: continue
        cx0,cy0=x+C/2,y+C/2; uu,vv=(cx0-1500)/1500,(cy0-1000)/1500; ex=cx0+Fm(np.array(uu),np.array(vv))@cx; ey=cy0+Fm(np.array(uu),np.array(vv))@cy
        if not (3<=ex<E2.shape[1]-4 and 3<=ey<E2.shape[0]-4): continue
        rows.append((cx0,cy0,ex,ey,int(any((cx0-a_)**2+(cy0-b_)**2<r_*r_ for a_,b_,r_ in wheels)),*a.mean(0)))
R=np.array(rows); base=np.array([f([v*sc for v in r[5:8]]) for r in R])
np.savez(OUTNPZ,xy=R[:,:2],exy=R[:,2:4],wheel=R[:,4],cam=R[:,5:8],base=base)
print(f"CCT {Tc:.0f}K | cells {len(R)} (wheels {int(R[:,4].sum())}) | base max {base.max(0).round(3)}")
