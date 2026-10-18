import sys,numpy as np
# crop a region (in thumb coords of 1200-wide thumbnail) from linear data, apply simple WB + gamma for viewing, draw grid
tag,x0,y0,x1,y1=sys.argv[1],*map(float,sys.argv[2:6]); grid=sys.argv[6] if len(sys.argv)>6 else None
d=np.load(f"{tag}_lin.npy",mmap_mode='r'); H,W,_=d.shape; k=W/1200
X0,Y0,X1,Y1=[int(v*k) for v in (x0,y0,x1,y1)]
c=np.asarray(d[Y0:Y1,X0:X1]).astype(np.float32)
g=c.reshape(-1,3); wb=np.percentile(g,50,axis=0); c=c/wb*0.18
c=np.clip(c,0,1)**(1/2.2); img=(c*255).astype(np.uint8).copy()
if grid:   # grid="cols,rows,ax0,ay0,ax1,ay1" in crop-pixel coords of patch centres corners
    cols,rows,ax0,ay0,ax1,ay1=map(float,grid.split(','))
    for j in range(int(rows)):
        for i in range(int(cols)):
            cx=int(ax0+(ax1-ax0)*i/(cols-1)); cy=int(ay0+(ay1-ay0)*j/(rows-1))
            img[max(cy-6,0):cy+6,max(cx-6,0):cx+6]=[255,0,255]
with open(f"crop_{tag}.ppm","wb") as f: f.write(b"P6 %d %d 255\n"%(img.shape[1],img.shape[0])); f.write(img.tobytes())
print(tag,"crop lin px",X0,Y0,X1,Y1,"size",img.shape[1],img.shape[0],"k",round(k,3))
