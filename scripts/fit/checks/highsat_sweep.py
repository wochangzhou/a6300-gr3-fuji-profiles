import os
import sys,math,numpy as np,rawpy
GS=sys.argv[1]; sys.path.insert(0,GS); from dcp import read
src=open(GS+'/port.py').read(); exec(src[src.index('def enc(x)'):src.index('grAS=read')])
r=rawpy.imread(os.environ['TEST_ARW'])
a=r.postprocess(output_color=rawpy.ColorSpace.raw,gamma=(1,1),no_auto_bright=True,use_camera_wb=True,output_bps=16,half_size=True).astype(float)/65535
# glasses area (half-size coords)
reg=a[1270:1400,690:1010].reshape(-1,3)
b=reg[:,2]/np.maximum(reg.mean(1),1e-4); o=np.argsort(-b); sel=reg[o[:600]]; sel=sel[sel.max(1)>0.005]
print("glasses blue pixels",len(sel),"camera rgb p50",np.round(np.median(sel,0),4),"p95 max",np.round(np.percentile(sel.max(1),95),4))
PP=np.linalg.inv(np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]))
HB=read(os.path.expanduser('~/Library/Application Support/Adobe/CameraRaw/CameraProfiles/')+'Sony ILCE-6300 Hasselblad X1D Standard.dcp')[50940][2]
X2S=np.array([[3.1338561,-1.6168667,-0.4906146],[-0.9787684,1.9161415,0.0334540],[0.0719453,-0.2289914,1.4052427]])  # XYZ D50 -> linear sRGB
PPX=np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]])
def tone(p,c):
    f=lambda x:float(np.interp(x,c[0::2],c[1::2])); o=np.argsort(p); lo,mi,hi=p[o]
    if hi-lo<1e-9: return np.array([f(x) for x in p])
    L,Hh=f(lo),f(hi); q=np.empty(3); q[o[0]]=L; q[o[2]]=Hh; q[o[1]]=L+(Hh-L)*(mi-lo)/(hi-lo); return q
def run(path,label="",use_look=True):
    t=read(path); FM=np.array(t[50965][2]).reshape(3,3); hsm=Table(t[50937][2],t[50939][2],0) if 50937 in t else None
    lk=Table(t[50981][2],t[50982][2],t[51108][2][0] if 51108 in t else 0) if (50981 in t and use_look) else None
    ev=(t[51109][2][0] if 51109 in t else 0); stats=[]
    for px in sel[::2]:
        p=np.clip(PP@(FM@px),0,None)
        if hsm: p=np.array(hsm.apply(list(p)))
        p=np.clip(p*2**ev,0,1)
        if lk: p=np.array(lk.apply(list(p)))
        p=tone(p,t[50940][2] if 50940 in t else HB); s=X2S@(PPX@p); stats.append((rgb2hsv(*p)[1], s.min()<-0.002, -s.min()/max(s.max(),1e-6)))
    st=np.array(stats); print(f"{label:34s} ProPhoto sat p50 {np.median(st[:,0]):.2f}  outside sRGB {100*st[:,1].mean():5.1f}%  how far outside (p50) {np.median(st[:,2]):.2f}")

import glob
CP=os.path.expanduser('~/Library/Application Support/Adobe/CameraRaw/CameraProfiles/')
# synthetic sweep at LookTable input: hue 0-354, s 0.55-0.95, v 0.2-0.9
SW=[hsv2rgb(h/60,s,v) for h in range(0,360,6) for s in (0.55,0.65,0.75,0.85,0.95) for v in (0.2,0.45,0.7,0.9)]
def sweep(t,use):
    lk=Table(t[50981][2],t[50982][2],t[51108][2][0] if 51108 in t else 0) if (50981 in t and use) else None
    c=t[50940][2] if 50940 in t else HB; bad={}
    for p0 in SW:
        p=np.array(lk.apply(list(p0))) if lk else np.array(p0); p=tone(p,c); s=X2S@(PPX@p)
        h=int(rgb2hsv(*p0)[0]*60)//60*60; bad.setdefault(h,[]).append(s.min()<-0.002)
    return {h:np.mean(v) for h,v in bad.items()}

SW=[(h,sat,hsv2rgb(h/60,sat,v)) for h in range(0,360,6) for sat in (0.85,0.95) for v in (0.2,0.45,0.7,0.9)]
print("only colours MORE saturated than any calibration sample (s 0.85-0.95): outside sRGB without table -> with table")
for p in sorted(glob.glob(CP+'Sony ILCE-6300 *.dcp')):
    t=read(p)
    if 50981 not in t or 'Monotone' in p: continue
    lk=Table(t[50981][2],t[50982][2],t[51108][2][0] if 51108 in t else 0); c=t[50940][2] if 50940 in t else HB; r={}
    for h,sat,p0 in SW:
        for use in (0,1):
            q=np.array(lk.apply(list(p0))) if use else np.array(p0); q=tone(q,c); o=X2S@(PPX@q); r.setdefault((h//60*60,use),[]).append(o.min()<-0.002)
    print(f"  {p.split('6300 ')[1][:-4]:24s}",' '.join(f"{h:3d}°:{100*np.mean(r[(h,0)]):3.0f}→{100*np.mean(r[(h,1)]):3.0f}" for h in range(0,360,60)))
