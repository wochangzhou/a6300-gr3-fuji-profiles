# Gradual saturation compression for ported GR III colour styles.
# For each LookTable node, find the PP saturation at which the fully rendered
# colour (look -> BaselineExposureOffset -> ToneCurve, hue-preserving RGB tone
# per DNG SDK) leaves sRGB, then soft-knee the node's output saturation.
import sys,struct,math,bisect,os
S=sys.argv[1]; LRP=sys.argv[2]; SRC_DIR=sys.argv[3]; DST_DIR=sys.argv[4]
sys.argv=[sys.argv[0],S,LRP,'.','/dev/null']
exec(open(S+'/port.py').read().split('HD,SD,VD=90,16,16')[0])
SRGB2XYZ=[[0.4360,0.3851,0.1431],[0.2225,0.7169,0.0606],[0.0139,0.0971,0.7141]]; PP2S=mm(inv(SRGB2XYZ),PP2XYZ)
KNEE=0.75
def curve(pts):
    xs=pts[0::2]; ys=pts[1::2]
    def f(x):
        x=min(max(x,0),1); i=min(max(bisect.bisect_right(xs,x)-1,0),len(xs)-2); return ys[i]+(ys[i+1]-ys[i])*(x-xs[i])/(xs[i+1]-xs[i])
    return f
def rgbtone(rgb,f):
    r=[min(max(x,0),1) for x in rgb]; lo,mid,hi=sorted(range(3),key=lambda k:r[k]); out=[0,0,0]
    out[hi]=f(r[hi]); out[lo]=f(r[lo]); out[mid]=out[lo]+(out[hi]-out[lo])*((r[mid]-r[lo])/(r[hi]-r[lo]) if r[hi]>r[lo] else 0); return out
def soft(x): return x if x<=KNEE else KNEE+(1-KNEE)*math.tanh((x-KNEE)/(1-KNEE))
def compress(t,tc,E,h,s,v):
    def ok(ss): return min(mv(PP2S,rgbtone([E*c for c in hsv2rgb(h,ss,v)],tc)))>=0
    if ok(1.0): lim=1.0
    else:
        a,b=0.0,1.0
        for _ in range(22):
            m=(a+b)/2; a,b=(m,b) if ok(m) else (a,m)
        lim=max(a,1e-4)
    return lim*soft(s/lim)
os.makedirs(DST_DIR,exist_ok=True)
for style in ["Standard","Positive Film","Negative Film","Vivid"]:
    p=f"{SRC_DIR}/Sony ILCE-6300 GR III {style}.dcp"; t=read(p); H,Sd,V=tag(t,50981); d0=list(tag(t,50982)); P=Table((H,Sd,V),d0,1); d=list(d0)
    tc=curve(tag(t,50940)); E=2**tag(t,51109)[0]; n=0; mx=0
    for vi in range(V):
        v=dec(vi/(V-1)) if vi else 1e-4
        for hi in range(H):
            for si in range(1,Sd):
                X=hsv2rgb(hi*6/H,si/(Sd-1),v); h0,s0,v0=rgb2hsv(*X)
                T=P.apply(X); hT,sT,vT=rgb2hsv(*T)
                if sT<1e-4: continue
                s2=compress(None,tc,E,hT,sT,vT)
                if s2<sT-1e-6:
                    o=3*(vi*H*Sd+hi*Sd+si); d[o+1]=s2/s0; n+=1; mx=max(mx,1-s2/sT)
    nt={k:(v[0],v[1],v[3]) for k,v in t.items()}; nt[50982]=(11,len(d),struct.pack('<%df'%len(d),*d))
    write(f"{DST_DIR}/Sony ILCE-6300 GR III {style}.dcp",nt)
    print(f"{style:14s} compressed nodes {n}/{V*H*(Sd-1)}, max sat reduction {100*mx:.1f}%")
