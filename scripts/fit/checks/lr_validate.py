# Check (not part of the build): does Lightroom render our DCPs the way our offline model (DNG SDK reference steps:
# WB -> ForwardMatrix -> HueSatMap -> exposure (BaselineExposureOffset, clip at 1) -> LookTable -> hue-preserving RGB
# tone) predicts? A synthetic linear DNG ("Sony ILCE-6300", known white-balanced camera RGB per patch) goes through
# Lightroom with each profile; the exports are compared with the offline prediction.
# Patches (white-balanced camera RGB, 1 = DNG white level): 48-step grey ramp 2^-11..1, a 6x6x6 cube (levels 0..1
# x 0.6), and the 24 A6300 chart patches (dpreview RAW means, white patch -> 0.9, same as chart_eval.py), on a
# 0.18 grey background.
# Usage:
#   lr_validate.py make    <scripts> <LR CameraProfiles> <patches_raw.json> <out.dng> <layout.json>
#   lr_validate.py predict <scripts> <LR CameraProfiles> <acr3.txt> <layout.json> <pred.json> <label=dcp | label=as:dcp> ...
#   lr_validate.py compare <scripts> <de2000.py> <layout.json> <pred.json> <label=export.tif> ...
#   lr_validate.py shoulder <scripts> <layout.json> <export.tif> <profile.dcp> <key> <data/lr_shoulder.json>
#     Lightroom's highlight shoulder in front of the LookTable (hue-preserving: max and min channel through one curve,
#     middle channel keeps its ratio), measured on the grey ramp of a profile with DefaultBlackRender None: LookTable
#     input x = exposure-scaled base -> s(x). Stored per BaselineExposureOffset under <key>.
# Lightroom: import the DNG, one virtual copy per profile (all other settings default), export 16-bit TIFF,
# ProPhoto RGB, original size, no output sharpening.
import sys,json,math,os
CMD,S=sys.argv[1],sys.argv[2]; ARGS=sys.argv[3:]
sys.path.insert(0,S); from dcp import read
_argv=sys.argv; sys.argv=[_argv[0],S,'.','.','/dev/null']
src=open(S+'/port.py').read(); exec(src[:src.index('grAS=read(')])
rb=open(S+'/rawbase.py').read(); exec(rb[rb.index('ILL_T='):rb.index('P=json.load')])
sys.argv=_argv
PATCH,PITCH,COLS,MARGIN=48,56,18,32
CHART=["darkskin","lightskin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan","white","n8","n6.5","n5","n3.5","black"]

def neutral_of(pat):
    n=[pat['n8'][k]+pat['n6.5'][k]+pat['n5'][k] for k in range(3)]; m=max(n); return [x/m for x in n]

def make(LRP,PATCHES,OUT,LAYOUT):
    import numpy as np,tifffile
    pat=json.load(open(PATCHES))['a6300']; neu=neutral_of(pat)
    P=[]
    for i,e in enumerate(np.linspace(-11,0,48)): v=float(2**e); P.append(("grey",f"g{i:02d}",[v,v,v]))
    lv=[0,0.2,0.4,0.6,0.8,1.0]
    for r in lv:
        for g in lv:
            for b in lv: P.append(("cube",f"c{r:.1f}{g:.1f}{b:.1f}",[0.6*r,0.6*g,0.6*b]))
    sc=0.9/(pat['white'][1]/neu[1])
    for n in pat:
        P.append(("chart",n,[pat[n][k]/neu[k]*sc for k in range(3)]))
    rows=(len(P)+COLS-1)//COLS; W=2*MARGIN+COLS*PITCH; H=2*MARGIN+rows*PITCH
    img=np.empty((H,W,3),np.float64); img[:]=[0.18*neu[k] for k in range(3)]
    lay=[]
    for i,(grp,name,w) in enumerate(P):
        y=MARGIN+(i//COLS)*PITCH; x=MARGIN+(i%COLS)*PITCH
        img[y:y+PATCH,x:x+PATCH]=[min(w[k]*neu[k],1.0) for k in range(3)]
        lay.append(dict(group=grp,name=name,wb=w,x=x+PATCH//2,y=y+PATCH//2))
    raw=np.round(img*65535).astype(np.uint16)
    t=read(f"{LRP}/Adobe Standard/Sony ILCE-6300 Adobe Standard.dcp")
    def srat(v): return [x for f in v for x in (int(round(f*10000)),10000)]
    ext=[(50706,'B',4,(1,4,0,0),True),(50707,'B',4,(1,1,0,0),True),(50708,'s',0,"Sony ILCE-6300",True),
         (271,'s',0,"SONY",True),(272,'s',0,"ILCE-6300",True),
         (50721,'2i',9,srat(tag(t,50721)),True),(50722,'2i',9,srat(tag(t,50722)),True),
         (50778,'H',1,(tag(t,50778)[0],),True),(50779,'H',1,(tag(t,50779)[0],),True),
         (50728,'2I',3,[x for f in neu for x in (int(round(f*1000000)),1000000)],True),
         (50730,'2i',1,(0,1),True),(50714,'H',1,(0,),True),(50717,'H',1,(65535,),True)]
    # written as RGB (tifffile would add ExtraSamples for an unknown photometric), then PhotometricInterpretation -> LinearRaw
    tifffile.imwrite(OUT,raw,photometric='rgb',planarconfig='contig',subfiletype=0,extratags=ext,metadata=None,software=False)
    with tifffile.TiffFile(OUT) as tf: off=tf.pages[0].tags[262].valueoffset
    with open(OUT,'r+b') as fh: fh.seek(off); fh.write((34892).to_bytes(2,'little'))
    json.dump(dict(neutral=neu,patch=PATCH,items=lay),open(LAYOUT,"w"),indent=0)
    print(f"wrote {OUT} ({W}x{H}, {len(P)} patches; neutral {[round(x,4) for x in neu]})")

def tone(rgb,cx,cy):
    def f(x):
        x=min(max(x,0),1)
        for i in range(1,len(cx)):
            if x<=cx[i]: return cy[i-1]+(cy[i]-cy[i-1])*(x-cx[i-1])/(cx[i]-cx[i-1])
        return cy[-1]
    o=sorted(range(3),key=lambda k:rgb[k]); lo,mi,hi=[min(max(rgb[k],0),1) for k in o]
    L,H=f(lo),f(hi); M=L+(H-L)*((mi-lo)/(hi-lo) if hi>lo else 0); out=[0]*3; out[o[0]],out[o[1]],out[o[2]]=L,M,H; return out
def lab(p):
    X=[sum(PP2XYZ[r][k]*p[k] for k in range(3)) for r in range(3)]; Wt=[0.9642,1,0.8249]
    f=[(x/w)**(1/3) if x/w>216/24389 else (24389/27*x/w+16)/116 for x,w in zip(X,Wt)]; return [116*f[1]-16,500*(f[0]-f[1]),200*(f[1]-f[2])]

def predict(LRP,ACR3,LAYOUT,OUT,profs):
    L=json.load(open(LAYOUT)); neu=L['neutral']; a=[float(x) for x in open(ACR3).read().split()]; ax=[i/(len(a)-1) for i in range(len(a))]
    res={}
    for lbl,p in profs:
        isas=p.startswith("as:"); t=read(p[3:] if isas else p)
        if 50938 not in t:
            t=dict(t); t[50937]=(4,3,[1,1,1],b''); t[50938]=(11,3,[0.0,1.0,1.0],b''); t[50939]=t[50938]
        f,T,w=base_fn(t)(neu); E=2**tag(t,51109)[0] if 51109 in t else 1
        LT=table(t,50981,50982,51108) if 50981 in t else None
        if 50940 in t and not isas: c=tag(t,50940); cx,cy=c[0::2],c[1::2]
        else: cx,cy=ax,a
        out={}
        for it in L['items']:
            x=[E*v for v in f([it['wb'][k]*neu[k] for k in range(3)])]; x=[min(max(v,0),1) for v in x]
            if LT: x=LT.apply(x)
            out[it['name']]=lab(tone(x,cx,cy))
        res[lbl]=out; print(f"{lbl}: CCT {T:.0f}K, exposure x{E:.3f}")
    json.dump(res,open(OUT,"w"))

def compare(DE,LAYOUT,PRED,exps):
    import numpy as np,tifffile
    exec(open(DE).read(),globals())
    L=json.load(open(LAYOUT)); PR=json.load(open(PRED)); h=L['patch']//3
    for lbl,f in exps:
        im=tifffile.imread(f).astype(np.float64); im=im[...,:3]/(65535 if im.max()>255 else 255)
        pr=PR[lbl]; rows={}
        for it in L['items']:
            m=im[it['y']-h:it['y']+h,it['x']-h:it['x']+h].reshape(-1,3).mean(0)**1.8
            got=lab(list(m)); want=pr[it['name']]; rows.setdefault(it['group'],[]).append((it['name'],de2000(got,want),got,want))
        print(f"\n=== {lbl}  ({os.path.basename(f)})   dE00 Lightroom vs offline prediction")
        for g,r in rows.items():
            e=np.array([x[1] for x in r]); dL=np.array([x[2][0]-x[3][0] for x in r]); dC=np.array([math.hypot(*x[2][1:])-math.hypot(*x[3][1:]) for x in r])
            w=int(e.argmax()); print(f"  {g:6s} n {len(r):3d}  mean {e.mean():.2f}  p95 {np.percentile(e,95):.2f}  max {e.max():.2f} ({r[w][0]})  | mean dL {dL.mean():+.2f}  mean dC {dC.mean():+.2f}")
        g=rows['grey']; print("  grey ramp L* want -> got:", "  ".join(f"{x[3][0]:.1f}->{x[2][0]:.1f}" for x in g[::6]+[g[-1]]))

def shoulder(LAYOUT,EXP,PROF,KEY,OUT):
    import numpy as np,tifffile
    L=json.load(open(LAYOUT)); h=L['patch']//3; t=read(PROF); E=2**tag(t,51109)[0]; c=tag(t,50940); cx,cy=c[0::2],c[1::2]
    im=tifffile.imread(EXP).astype(np.float64)/65535
    G=[it for it in L['items'] if it['group']=='grey']
    xs=[0.0]+[E*it['wb'][0] for it in G]; ys=[0.0]+[float(np.interp(im[it['y']-h:it['y']+h,it['x']-h:it['x']+h,1].mean()**1.8,cy,cx)) for it in G]
    ys=list(np.maximum.accumulate(ys)); d=json.load(open(OUT)) if os.path.exists(OUT) else {}
    d[KEY]=dict(beo=tag(t,51109)[0],x=[round(v,6) for v in xs],y=[round(v,6) for v in ys]); json.dump(d,open(OUT,"w"),indent=0)
    print(f"{KEY}: BEO {tag(t,51109)[0]:+.3f}  s(0.3)={np.interp(0.3,xs,ys):.3f} s(0.6)={np.interp(0.6,xs,ys):.3f} s(1.0)={np.interp(1.0,xs,ys):.3f} s({xs[-1]:.2f})={ys[-1]:.3f}")

if CMD=="make": make(*ARGS[:4])
elif CMD=="predict": predict(*ARGS[:4],[a.split('=',1) for a in ARGS[4:]])
elif CMD=="shoulder": shoulder(*ARGS[:5])
elif CMD=="compare": compare(ARGS[0],ARGS[1],ARGS[2],[a.split('=',1) for a in ARGS[3:]])
