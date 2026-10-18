import numpy as np,json,math
# crop origin (lin px), display centre (400px view), display->crop factor
W={"a6300":((3724,461),(207,195),553/400),"gr3":((3737,441),(205,197),552/400),"xs20":((3855,479),(207,196),573/400)}
SECT=["red","red-orange","orange","yellow-orange","yellow","yellow-green","green","blue-green","blue","blue-violet","violet","red-violet"]
RINGS={"outer":152,"tint":124,"mid":94,"inner":60}
out={};hw=9
for tag,((ox,oy),(cx,cy),f) in W.items():
    d=np.load(f"{tag}_lin.npy",mmap_mode='r'); res={}
    for si,s in enumerate(SECT):
        ang=math.radians(-105+30*si+9)
        for rn,r in RINGS.items():
            x=int(ox+(cx+r*math.cos(ang))*f); y=int(oy+(cy+r*math.sin(ang))*f)
            b=np.asarray(d[y-hw:y+hw,x-hw:x+hw]).reshape(-1,3).astype(np.float64)
            res[f"{s}/{rn}"]=[float(v) for v in b.mean(0)]
    out[tag]=res
json.dump(out,open("wheel_raw.json","w"))
# marked preview for a6300 to check sample positions
import sys
for tag,((ox,oy),(cx,cy),f) in W.items():
    d=np.load(f"{tag}_lin.npy",mmap_mode='r'); X0,Y0=ox,oy; c=np.asarray(d[Y0:Y0+int(400*f),X0:X0+int(400*f)]).astype(np.float32)
    c=np.clip(c/np.percentile(c.reshape(-1,3),50,axis=0)*0.18,0,1)**(1/2.2); img=(c*255).astype(np.uint8).copy()
    for si in range(12):
        ang=math.radians(-105+30*si+9)
        for r in RINGS.values():
            px=int((cx+r*math.cos(ang))*f); py=int((cy+r*math.sin(ang))*f); img[py-hw:py+hw,px-hw:px+hw]=[255,0,255]
    open(f"wheelmark_{tag}.ppm","wb").write(b"P6 %d %d 255\n"%(img.shape[1],img.shape[0])+img.tobytes())
print("samples per camera:",len(out["a6300"]))
