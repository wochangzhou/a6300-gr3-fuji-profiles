import sys,numpy as np
O=sys.argv[1]; X=np.load(sys.argv[2],mmap_mode='r'); C=np.load(O+'/C3.npy'); Ad=np.load(O+'/Ad.npy'); D=2
h,w,_=Ad.shape; yy,xx=np.mgrid[0:h,0:w].astype(np.float64)
x=(xx*D+D/2-3000)/3000; y=(yy*D+D/2-2000)/3000
F=np.stack([np.ones_like(x),x,y,x*x,x*y,y*y,x**3,x*x*y,x*y*y,y**3],-1); q=F@C
qx=np.clip(q[...,0],0,X.shape[1]-2); qy=np.clip(q[...,1],0,X.shape[0]-2)
# box-average X over ~ the footprint of one work pixel (3x3 X px) then bilinear
Xf=np.asarray(X,dtype=np.float32)
x0=np.floor(qx).astype(int); y0=np.floor(qy).astype(int); fx=(qx-x0)[...,None]; fy=(qy-y0)[...,None]
acc=0
for dy in (-1,0,1):
    for dx in (-1,0,1):
        X0=np.clip(x0+dx,0,X.shape[1]-2); Y0=np.clip(y0+dy,0,X.shape[0]-2)
        acc=acc+Xf[Y0,X0]*(1-fx)*(1-fy)+Xf[Y0,X0+1]*fx*(1-fy)+Xf[Y0+1,X0]*(1-fx)*fy+Xf[Y0+1,X0+1]*fx*fy
Xw=(acc/9).astype(np.float32); np.save(O+'/Xw.npy',Xw)
inside=(q[...,0]>2)&(q[...,0]<X.shape[1]-3)&(q[...,1]>2)&(q[...,1]<X.shape[0]-3); np.save(O+'/inside.npy',inside)
# checkerboard check image
a=np.clip(Ad/np.percentile(Ad,60)*0.25,0,1)**(1/2.2); b=Xw/65535
cb=((yy//60+xx//60)%2==0)[...,None]; img=np.where(cb,a,b)[::2,::2]
img=(np.clip(img,0,1)*255).astype(np.uint8); open(O+'/check.ppm','wb').write(b"P6 %d %d 255\n"%(img.shape[1],img.shape[0])+img.tobytes()); print(Xw.shape,inside.mean())
