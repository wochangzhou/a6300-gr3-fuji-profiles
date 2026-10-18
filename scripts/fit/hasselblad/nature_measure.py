import os
import sys,json,math,numpy as np,tifffile
H,OUT=sys.argv[1],sys.argv[2]; R=os.environ.get('REF_DIR','reference')+'/'
exec(open(sys.argv[3]).read().split('NAMES=')[0].split("D='/Users")[0].replace("L=sys.argv[1];",""))  # reuse slab/de2000 from m.py
exec(open(sys.argv[3]).read().split('def de2000')[1].join(['def de2000','']) if False else '')
NAMES=["brown","skin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan","white","n8","n6.5","n5","n3.5","black"]
A2X=np.array([[0.5767309,0.1855540,0.1881852],[0.2973769,0.6273491,0.0752741],[0.0270343,0.0706872,0.9911085]])
BR=np.array([[1.0478112,0.0228866,-0.0501270],[0.0295424,0.9904844,-0.0170491],[-0.0092345,0.0150436,0.7521316]])
PP2X=np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]); M=np.linalg.inv(PP2X)@BR@A2X
W50=np.array([0.9642,1,0.8249])
def pp(v): return M@((v/65535.0)**(563/256))
def lab(p):
    t=PP2X@p/W50; f=np.where(t>216/24389,np.cbrt(t),(24389/27*t+16)/116); return np.array([116*f[1]-16,500*(f[0]-f[1]),200*(f[1]-f[2])])
def samp(a):
    out={};ox,oy=3205,723;x0,y0,x1,y1=223,248,1648,1088
    for j in range(4):
        for i in range(6):
            cx=int(ox+x0+(x1-x0)*i/5);cy=int(oy+y0+(y1-y0)*j/3);out[NAMES[j*6+i]]=pp(a[cy-40:cy+40,cx-40:cx+40].reshape(-1,3).astype(float).mean(0))
    SECT=range(12);ox,oy=5273,723;f=793/400
    for si in SECT:
        an=math.radians(-105+30*si+9)
        for rn,r in {"outer":165,"tint":134,"mid":102,"inner":65}.items():
            px=int((205+r*math.cos(an))*f);py=int((205+r*math.sin(an))*f);out[f"w{si}/{rn}"]=pp(a[oy+py-12:oy+py+12,ox+px-12:ox+px+12].reshape(-1,3).astype(float).mean(0))
    return out
S=samp(np.load(H+'/std.npy',mmap_mode='r')); N=samp(tifffile.imread(R+'x1d_nature.tif'))
print('std.npy==standard.tif check skipped')
for n in ["white","n8","n6.5","n5","n3.5","black"]:
    s,nn=S[n],N[n]; print(f"{n:6s} Y std {PP2X[1]@s:.4f} nat {PP2X[1]@nn:.4f}  Lab std {np.round(lab(s),2)} nat {np.round(lab(nn),2)}  rgb ratio nat/std {np.round(nn/s,3)}")
json.dump({'std':{k:v.tolist() for k,v in S.items()},'nat':{k:v.tolist() for k,v in N.items()}},open(OUT,'w'))
