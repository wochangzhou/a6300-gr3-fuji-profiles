# End-to-end check on independent samples: GR III RAW through Adobe's GR III
# camera-matching style vs A6300 RAW through a ported profile. Both rendered
# with the style's BaselineExposureOffset + hue-preserving tone curve, compared as
# CIE dE76 / dE2000 in Lab D50.
import sys,json,math,bisect
S,LRP,RAWP,BASEJ,RAWS,BASES=sys.argv[1:7]; CANDS=sys.argv[7:]
sys.argv=[sys.argv[0],S,LRP,'.','/dev/null']
exec(open(S+'/port.py').read().split('HD,SD,VD=90,16,16')[0])
def curve(pts):
    xs=pts[0::2]; ys=pts[1::2]
    def f(x):
        x=min(max(x,0),1); i=min(max(bisect.bisect_right(xs,x)-1,0),len(xs)-2); return ys[i]+(ys[i+1]-ys[i])*(x-xs[i])/(xs[i+1]-xs[i])
    return f
def rgbtone(rgb,f):
    r=[min(max(x,0),1) for x in rgb]; lo,mid,hi=sorted(range(3),key=lambda k:r[k]); out=[0,0,0]
    out[hi]=f(r[hi]); out[lo]=f(r[lo]); out[mid]=out[lo]+(out[hi]-out[lo])*((r[mid]-r[lo])/(r[hi]-r[lo]) if r[hi]>r[lo] else 0); return out
WD50=[0.9642,1.0,0.8249]
def lab(pp):
    X=mv(PP2XYZ,pp); fx=[ (t/w)**(1/3) if t/w>216/24389 else (24389/27*t/w+16)/116 for t,w in zip(X,WD50)]
    return [116*fx[1]-16,500*(fx[0]-fx[1]),200*(fx[1]-fx[2])]
def de2000(a,b):
    L1,a1,b1=a;L2,a2,b2=b; C1=math.hypot(a1,b1);C2=math.hypot(a2,b2);Cb=(C1+C2)/2
    G=0.5*(1-math.sqrt(Cb**7/(Cb**7+25**7))); a1p=(1+G)*a1;a2p=(1+G)*a2; C1p=math.hypot(a1p,b1);C2p=math.hypot(a2p,b2)
    h1=math.degrees(math.atan2(b1,a1p))%360; h2=math.degrees(math.atan2(b2,a2p))%360
    dL=L2-L1; dC=C2p-C1p; dh=h2-h1
    if C1p*C2p==0: dh=0
    elif dh>180: dh-=360
    elif dh<-180: dh+=360
    dH=2*math.sqrt(C1p*C2p)*math.sin(math.radians(dh/2)); Lb=(L1+L2)/2; Cbp=(C1p+C2p)/2
    hb=h1+h2 if C1p*C2p==0 else ((h1+h2)/2 if abs(h1-h2)<=180 else ((h1+h2+360)/2 if h1+h2<360 else (h1+h2-360)/2))
    T=1-0.17*math.cos(math.radians(hb-30))+0.24*math.cos(math.radians(2*hb))+0.32*math.cos(math.radians(3*hb+6))-0.20*math.cos(math.radians(4*hb-63))
    SL=1+0.015*(Lb-50)**2/math.sqrt(20+(Lb-50)**2); SC=1+0.045*Cbp; SH=1+0.015*Cbp*T
    RT=-2*math.sqrt(Cbp**7/(Cbp**7+25**7))*math.sin(math.radians(60*math.exp(-((hb-275)/25)**2)))
    return math.sqrt((dL/SL)**2+(dC/SC)**2+(dH/SH)**2+RT*(dC/SC)*(dH/SH))
RAWC=json.load(open(RAWP)); BASEC=json.load(open(BASEJ)); RS=json.load(open(RAWS))['gr3']; BS=json.load(open(BASES))['a6300']
gp=RAWC['gr3']; neutral=[gp['n8'][k]+gp['n6.5'][k]+gp['n5'][k] for k in range(3)]; neutral=[x/neutral[1] for x in neutral]; sc=0.9/(gp['white'][1]/neutral[1])
print(f"{'style':14s} " + "  ".join(f"{c.split('|')[0]:>22s}" for c in CANDS))
for style in ["Standard","Positive Film","Negative Film","Vivid"]:
    g=read(f"{LRP}/Camera/Ricoh GR III/RICOH GR III Camera {style}.dcp"); LK=table(g,50981,50982,51108); c2p=mm(XYZ2PP,m3(tag(g,50965)))
    E=2**tag(g,51109)[0]; tc=curve(tag(g,50940))
    tgt={n:lab(rgbtone([E*c for c in LK.apply(mv(c2p,[v[k]*sc/neutral[k] for k in range(3)]))],tc)) for n,v in RS.items()}
    row=[]
    for cand in CANDS:
        lbl,d=cand.split('|'); t=read(f"{d}/Sony ILCE-6300 GR III {style}.dcp"); T=table(t,50981,50982,51108)
        es=sorted(de2000(lab(rgbtone([E*c for c in T.apply(BS[n])],tc)),tgt[n]) for n in RS)
        row.append(f"{sum(es)/len(es):5.2f} (p90 {es[int(.9*(len(es)-1))]:5.2f})")
    print(f"{style:14s} "+"  ".join(f"{r:>22s}" for r in row))
