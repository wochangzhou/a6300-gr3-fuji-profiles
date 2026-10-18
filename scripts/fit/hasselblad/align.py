import sys,numpy as np
A=np.load(sys.argv[1],mmap_mode='r'); X=np.load(sys.argv[2],mmap_mode='r'); O=sys.argv[3]
D=2  # work grid = A full /2
def box(a,f):  # block mean downsample by integer f
    h,w=a.shape[0]//f*f,a.shape[1]//f*f; return np.asarray(a[:h,:w],dtype=np.float32).reshape(h//f,f,w//f,f,3).mean((1,3))
Ad=box(A,D)/65535; Xd=box(X,1)  # X full res kept (float) for bilinear sampling later
Xl=(np.asarray(Xd)/65535)**(563/256)
lumA=np.log(Ad@np.array([0.3,0.6,0.1])+1e-4); lumX=np.log(Xl@np.array([0.3,0.6,0.1])+1e-4)
# initial affine from 4 manual correspondences (full-res coords A -> X)
PA=np.array([[2543,628],[3473,1177],[4010,731],[1998,3276]],float); PX=np.array([[3428,971],[4853,1811],[5679,1129],[2628,5094]],float)
M=np.linalg.lstsq(np.c_[PA,np.ones(4)],PX,rcond=None)[0]; print("affine A->X\n",M.T, "resid",np.abs(np.c_[PA,np.ones(4)]@M-PX).max())
def bil(img,x,y):
    x=np.clip(x,0,img.shape[1]-2); y=np.clip(y,0,img.shape[0]-2); x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); fx=(x-x0)[...,None] if img.ndim==3 else x-x0; fy=(y-y0)[...,None] if img.ndim==3 else y-y0
    return img[y0,x0]*(1-fx)*(1-fy)+img[y0,x0+1]*fx*(1-fy)+img[y0+1,x0]*(1-fx)*fy+img[y0+1,x0+1]*fx*fy
h,w=lumA.shape; yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
def mapc(xx,yy,off=None):
    fx=xx*D; fy=yy*D; q=np.stack([fx,fy,np.ones_like(fx)],-1)@M
    if off is not None: q=q+off
    return q[...,0],q[...,1]
# refine: per-tile translation by FFT cross-correlation of gradient magnitude
def grad(l): gy,gx=np.gradient(l); return np.hypot(gx,gy)
gA=grad(lumA); T=64; R=16; offs=[]
for ty in range(T,h-T,T):
    for tx in range(T,w-T,T):
        a=gA[ty-T//2:ty+T//2,tx-T//2:tx+T//2]
        sx,sy=mapc(xx[ty-T//2-R:ty+T//2+R,tx-T//2-R:tx+T//2+R],yy[ty-T//2-R:ty+T//2+R,tx-T//2-R:tx+T//2+R])
        b=grad(bil(lumX,sx,sy))
        if a.std()<0.02: continue
        best=(-1,0,0)
        for dy in range(-R,R+1,1):
            for dx in range(-R,R+1,1):
                c=b[R+dy:R+dy+T,R+dx:R+dx+T]; v=np.corrcoef(a.ravel(),c.ravel())[0,1]
                if v>best[0]: best=(v,dx,dy)
        offs.append((tx,ty,*best))
offs=np.array(offs); good=offs[offs[:,2]>0.5]; print("tiles",len(offs),"good",len(good),"median shift (work px)",np.median(good[:,3]),np.median(good[:,4]))
np.save(O+'/offs.npy',offs); np.save(O+'/M.npy',M); np.save(O+'/Ad.npy',Ad.astype(np.float32))
