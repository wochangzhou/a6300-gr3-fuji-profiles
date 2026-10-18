import sys,json,numpy as np
S=sys.argv[1]; a=np.load(f"{S}/std.npy",mmap_mode='r')
NAMES=["brown","skin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan","white","n8","n6.5","n5","n3.5","black"]
ox,oy=3205,723; x0,y0,x1,y1=223,248,1648,1088
# Adobe RGB (1998) -> XYZ D65 -> Bradford D50 -> ProPhoto linear
A2X=np.array([[0.5767309,0.1855540,0.1881852],[0.2973769,0.6273491,0.0752741],[0.0270343,0.0706872,0.9911085]])
BR=np.array([[1.0478112,0.0228866,-0.0501270],[0.0295424,0.9904844,-0.0170491],[-0.0092345,0.0150436,0.7521316]])
PP2X=np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]])
M=np.linalg.inv(PP2X)@BR@A2X
def topp(rgb16): return (M@((np.asarray(rgb16)/65535.0)**(563/256))).tolist()
out={};hw=40
for j in range(4):
    for i in range(6):
        cx=int(ox+x0+(x1-x0)*i/5); cy=int(oy+y0+(y1-y0)*j/3)
        b=np.asarray(a[cy-hw:cy+hw,cx-hw:cx+hw]).reshape(-1,3).astype(np.float64)
        out[NAMES[j*6+i]]=topp(b.mean(0))
json.dump(out,open(f"{S}/x1d_std_chart.json","w"))
for n in ("white","n8","n5","black","red","skin"): print(f"{n:6s} PP lin {[round(v,4) for v in out[n]]}")
