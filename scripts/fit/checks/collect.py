import os
import sys,glob,numpy as np,rawpy
fs=sorted(glob.glob(os.environ.get('A6300_PHOTOS','photos')+'/*.ARW')); pick=fs[::max(1,len(fs)//16)]
out={}
for f in pick:
    with rawpy.imread(f) as r:
        a=r.postprocess(output_color=rawpy.ColorSpace.raw,gamma=(1,1),no_auto_bright=True,use_camera_wb=True,output_bps=16,half_size=True).astype(np.float32)/65535
    px=a[::4,::4].reshape(-1,3); Y=px@[0.3,0.6,0.1]; norm=0.18/np.median(Y[Y>0])   # expose each photo to mid-grey median
    out[f.split('/')[-1]]=np.clip(px*norm,0,None)
    print(f.split('/')[-1],px.shape[0],"norm",round(float(norm),2))
np.savez(sys.argv[1],**out)
