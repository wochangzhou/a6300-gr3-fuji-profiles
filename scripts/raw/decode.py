import sys,rawpy,numpy as np
src,tag,out=sys.argv[1],sys.argv[2],sys.argv[3]
with rawpy.imread(src) as r:
    print(tag,"pattern" ,r.raw_pattern.shape,"black",r.black_level_per_channel,"white",r.white_level,"camera_wb",[round(x,3) for x in r.camera_whitebalance],"desc",r.color_desc)
    lin=r.postprocess(output_color=rawpy.ColorSpace.raw,gamma=(1,1),no_auto_bright=True,use_camera_wb=False,user_wb=[1,1,1,1],output_bps=16,demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD if r.raw_pattern.shape==(2,2) else None,user_flip=0)
    np.save(f"{out}/{tag}_lin.npy",lin)
    prev=r.postprocess(use_camera_wb=True,half_size=True,user_flip=0,output_bps=8)
h,w,_=prev.shape; s=max(1,w//1600); p=prev[::s,::s]
with open(f"{out}/{tag}_prev.ppm","wb") as f: f.write(b"P6 %d %d 255\n"%(p.shape[1],p.shape[0])); f.write(p.tobytes())
print(tag,"lin",lin.shape,lin.dtype,"max",lin.max(),"| preview",p.shape,"scale (lin px per preview px)",2*s)
