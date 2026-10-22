# Check (not part of the build): stress test of profiles on a dense synthetic grid of LookTable inputs (exposure-scaled base colours, ProPhoto linear):
# hue 0..359 (1 deg) x HSV sat 0..1 (0.02) x value (linear, 24 log steps 0.01..1). Each profile renders with the DNG
# reference steps (LookTable + hue-preserving RGB tone curve). "as:<dcp>:<acr3>" = Adobe Standard itself (reference).
import sys,os,math,numpy as np
LABDIR,G=sys.argv[1:3]; PROF=sys.argv[3:]   # usage: stress.py <lab dir> <scripts> "as:<Adobe Standard.dcp>:<acr3.txt>" <profile.dcp> ...
sys.path.insert(0,G); from dcp import read
sys.path.insert(0,LABDIR); from lab import *
src=open(os.path.dirname(os.path.abspath(sys.argv[0]))+'/analytic.py').read(); a=src.index("W50=np.array"); b=src.index("def tbl(t)"); exec(src[a:b])
def tbl(t): d=t[50981][2]; return np.array(t[50982][2]).reshape(d[2],d[0],d[1],3),tuple(d),(t[51108][2][0] if 51108 in t else 0)
H=np.arange(360.0); Sg=np.arange(0,1.0001,0.02); V=np.exp(np.linspace(np.log(0.01),0,24))
hh,ss,vv=np.meshgrid(H,Sg,V,indexing='ij'); X=hsv2rgb(hh.ravel(),ss.ravel(),vv.ravel())
shape=hh.shape
P2S=np.linalg.inv(np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]]))@np.array([[0.9555766,-0.0230393,0.0631636],[-0.0282895,1.0099416,0.0210077],[0.0122982,-0.0204830,1.3299098]])@PP2X  # ProPhoto(D50) -> linear sRGB(D65), Bradford
def render(spec):
    if spec.startswith("as:"):
        _,dcp,acr3=spec.split(":"); t=read(dcp); LT,d,e=tbl(t); a=np.loadtxt(acr3); cx,cy=np.linspace(0,1,len(a)),a; name="Adobe Standard"
    else:
        t=read(spec); LT,d,e=tbl(t); c=np.array(t[50940][2]); cx,cy=c[0::2],c[1::2]; name=os.path.basename(spec).replace("Sony ILCE-6300 ","").replace(".dcp","")
    Y=rgbtone(look(X,LT,d,e),cx,cy); return name,Y
def de76(a,b): return np.sqrt(((a-b)**2).sum(-1))
res={}
for spec in PROF:
    name,Y=render(spec); L=labpp(Y).reshape(*shape,3); C=np.hypot(L[...,1],L[...,2]); hue=np.degrees(np.arctan2(L[...,2],L[...,1]))%360
    m=C[:,1:,:]>3   # ignore near-neutral for hue metrics
    # 1 chroma reversal along input saturation (fixed hue, value)
    dC=np.diff(C,axis=1); crev=(dC<-0.5); 
    # 2 lightness reversal along value
    dL=np.diff(L[...,0],axis=2); lrev=(dL<-0.3)
    # 3 hue order along input hue (fixed sat>=0.2, value>=0.05)
    sel=(Sg>=0.2)[None,:,None]&(V>=0.05)[None,None,:]
    dh=((np.roll(hue,-1,axis=0)-hue+180)%360-180); hrev=(dh<-0.5)&sel&(C>8)
    # 4 smoothness: adjacent-step DeltaE76 along hue and sat (95th pct and max)
    eh=de76(np.roll(L,-1,axis=0),L)[:, (Sg>=0.1), :][..., V>=0.05]; es=de76(L[:,1:],L[:,:-1])[..., V>=0.05]
    # 5 gamut: linear sRGB outside [0,1] (after ProPhoto->sRGB), for value <= 0.9 inputs
    srgb=Y@P2S.T; oog=((srgb<-0.001)|(srgb>1.001)).any(-1).reshape(shape)
    res[name]=dict(L=L,crev=crev.mean()*100,crev_max=-dC.min(),lrev=lrev.mean()*100,lrev_max=-dL.min(),hrev=hrev.sum()/sel.sum()/360*100,
                   eh95=np.percentile(eh,95),ehmax=eh.max(),es95=np.percentile(es,95),esmax=es.max(),oog=oog.mean()*100,oog_hi=oog[:,Sg>=0.8].mean()*100)
ref=res.get("Adobe Standard")
print(f"{'profile':24s} {'C-rev%':>7s} {'maxdrop':>7s} {'L-rev%':>7s} {'maxdrop':>7s} {'hue-rev%':>8s} {'hue-step p95/max':>17s} {'sat-step p95/max':>17s} {'outside sRGB% all / s>=0.8':>27s}")
for n,r in res.items():
    print(f"{n:24s} {r['crev']:7.2f} {r['crev_max']:7.2f} {r['lrev']:7.2f} {r['lrev_max']:7.2f} {r['hrev']:8.3f} {r['eh95']:8.2f}/{r['ehmax']:7.2f} {r['es95']:8.2f}/{r['esmax']:7.2f} {r['oog']:13.1f} / {r['oog_hi']:5.1f}")
if ref is not None:
    print("\nDeviation from Adobe Standard (DeltaE76, value>=0.05):  sat<0.8 mean/p99 | sat>=0.85 (beyond pair data) mean/p99/max")
    vm=V>=0.05
    for n,r in res.items():
        if n=="Adobe Standard": continue
        e=de76(r['L'],ref['L'])[..., vm]; lo=e[:,Sg<0.8].ravel(); hi=e[:,Sg>=0.85].ravel()
        print(f"  {n:24s} {lo.mean():6.2f}/{np.percentile(lo,99):6.2f} | {hi.mean():6.2f}/{np.percentile(hi,99):6.2f}/{hi.max():6.2f}")
