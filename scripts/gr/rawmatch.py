# Build aligned GR III / GR IV profiles from the A6300 -> GR base-colour alignment model (data/gr/model_*.json,
# fitted by scripts/fit/gr/): rotate each LookTable node's input (exposure-scaled Adobe Standard base) by the
# modelled hue shift, scale its saturation and value, then look up the ported GR style. Model points carry a
# weight (7th field, kernel weight = its square root). Optional monotone file (data/gr/monotone_*.json): the
# saturation entries that scripts/fit/hasselblad/paired/monotone.py raised, applied as stored.
# Usage: rawmatch.py <scripts> <LR_PROFILES> <model.json> <ported_dir> <out_dir> <"GR III"|"GR IV"> [monotone.json]
import sys,struct,json,math,os
S=sys.argv[1]; LRP=sys.argv[2]; MJSON=sys.argv[3]; SRC_DIR=sys.argv[4]; DST_DIR=sys.argv[5]; CAM=sys.argv[6]
MONO=json.load(open(sys.argv[7])) if len(sys.argv)>7 else {}
sys.argv=[sys.argv[0],S,LRP,'.','/dev/null',CAM]
exec(open(S+'/port.py').read().split('HD,SD,VD=90,32,16')[0])
M=json.load(open(MJSON)); TR=M["train"]; PR={int(k):v for k,v in M["params"].items()}
def pred(h,s,k):
    sh,ss,lam=PR[k]; num=0;wt=lam
    for p in TR:
        d=((h-p[1])+180)%360-180; w=math.exp(-0.5*(d/sh)**2)*math.exp(-0.5*((s-p[2])/ss)**2)*(math.sqrt(p[6]) if len(p)>6 else 1.0); num+=w*p[k]; wt+=w
    return num/wt
def corr(hdeg,s):
    fade=min(1.0,s/0.15)   # leave neutrals alone
    return pred(hdeg,s,3)*fade, math.exp(pred(hdeg,s,4)*fade), math.exp(pred(hdeg,s,5)*fade)
# Both cameras reach the GR look tables at the same exposure-scaled base (renders normalised
# to the same scene white), so the GR BaselineExposureOffset is kept as is.
# Lightroom compresses highlights before the LookTable (hue-preserving shoulder s, measured by
# scripts/fit/checks/lr_validate.py into data/lr_shoulder.json), so a node X is s(E*base): undo s, align the base
# colour, re-apply s. The alignment was learned on base colours, before any shoulder.
SH=json.load(open(os.path.join(S,'..','data','lr_shoulder.json')))[CAM]; SX,SY=SH['x'],SH['y']
def _lin(x,xs,ys):
    if x<=xs[0]: return ys[0]
    for i in range(1,len(xs)):
        if x<=xs[i]: return ys[i-1]+(ys[i]-ys[i-1])*(x-xs[i-1])/(xs[i]-xs[i-1])
    return ys[-1]+(ys[-1]-ys[-2])*(x-xs[-1])/(xs[-1]-xs[-2])   # beyond the measured ramp: last slope
def _hp(rgb,fn):
    o=sorted(range(3),key=lambda k:rgb[k]); lo,mi,hi=[max(rgb[k],0.0) for k in o]; L_,H_=fn(lo),fn(hi)
    M_=L_+(H_-L_)*((mi-lo)/(hi-lo) if hi>lo else 0); out=[0.0]*3; out[o[0]],out[o[1]],out[o[2]]=L_,M_,H_; return out
s_fwd=lambda rgb:_hp(rgb,lambda x:_lin(x,SX,SY))
def s_inv(rgb):   # above the measured ramp (beyond the raw white point) hold the top: scale down, no extrapolation
    m=max(rgb); top=SY[-1]; rgb=[x*top/m for x in rgb] if m>top else rgb
    return _hp(rgb,lambda y:_lin(y,SY,SX))
# sRGB value encoding without the clip at 1 (a base colour can exceed 1 once the shoulder is undone)
encu=lambda x: 12.92*x if x<=0.0031308 else 1.055*x**(1/2.4)-0.055
decu=lambda y: y/12.92 if y<=0.04045 else ((y+0.055)/1.055)**2.4
os.makedirs(DST_DIR,exist_ok=True)
for style in ["Standard","Positive Film","Negative Film","Vivid","Monotone","Soft Monotone","Hard Monotone"]:
    t=read(f"{SRC_DIR}/Sony ILCE-6300 {CAM} {style}.dcp"); H,Sd,V=tag(t,50981); E=2**tag(t,51109)[0]; P=Table((H,Sd,V),list(tag(t,50982)),1); d=list(tag(t,50982))
    for vi in range(V):
        v=dec(vi/(V-1)) if vi else 1e-4
        for hi in range(H):
            for si in range(1,Sd):
                # node X = s(E*base) of the A6300; correct the base, re-expose and re-shoulder, look up
                X=hsv2rgb(hi*6/H,si/(Sd-1),v); h0,s0,v0=rgb2hsv(*X)
                hb,sb,vb=rgb2hsv(*[x/E for x in s_inv(X)])
                dh,ks,kv=corr(hb*60,sb)
                X2=hsv2rgb((hb+dh*6/360)%6,min(sb*ks,1.0),decu(encu(vb)*kv))
                T=P.apply(s_fwd([E*x for x in X2])); hT,sT,vT=rgb2hsv(*T); o=3*(vi*H*Sd+hi*Sd+si)
                d[o]=((hT-h0+3)%6-3)*60 if sT>1e-4 else 0.0; d[o+1]=min(sT,1)/s0; d[o+2]=enc(vT)/enc(v0) if v0>1e-7 else 1
    for i,v in MONO.get(style,{}).items(): d[int(i)]=v
    nt={k:(v[0],v[1],v[3]) for k,v in t.items()}; nt[50982]=(11,len(d),struct.pack('<%df'%len(d),*d))
    beo=tag(t,51109)[0]; nt[51109]=(10,1,struct.pack('<ii',int(round(beo*10000)),10000))
    write(f"{DST_DIR}/Sony ILCE-6300 {CAM} {style}.dcp",nt); print("built",style)
