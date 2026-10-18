import sys,json,math,numpy as np
S=sys.argv[1]; a=np.load(f"{S}/std.npy",mmap_mode='r')
exec(open(f"{S}/textract.py").read().split("out={};hw=40")[0].split("S=sys.argv[1]")[1].split("\n",1)[1])
ox,oy=5273,723; cx,cy=205,205; f=793/400
SECT=["red","red-orange","orange","yellow-orange","yellow","yellow-green","green","blue-green","blue","blue-violet","violet","red-violet"]
RINGS={"outer":165,"tint":134,"mid":102,"inner":65}; hw=12; out={}
img=(np.asarray(a[oy:oy+793,ox:ox+793])>>8).astype(np.uint8).copy()
for si,s in enumerate(SECT):
    ang=math.radians(-105+30*si+9)
    for rn,r in RINGS.items():
        px=int((cx+r*math.cos(ang))*f); py=int((cy+r*math.sin(ang))*f)
        b=np.asarray(a[oy+py-hw:oy+py+hw,ox+px-hw:ox+px+hw]).reshape(-1,3).astype(np.float64)
        out[f"{s}/{rn}"]=topp(b.mean(0)); img[py-hw:py+hw,px-hw:px+hw]=[255,0,255]
json.dump(out,open(f"{S}/x1d_std_wheel.json","w"))
open(f"{S}/wheelm.ppm","wb").write(b"P6 793 793 255\n"+img.tobytes()); print(len(out),"wheel samples")
