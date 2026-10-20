# Build chart-aligned GR III / GR IV profiles from the RAW-fitted A6300 -> GR base correction:
# rotate each LookTable node's input (exposure-scaled Adobe Standard base) by the fitted hue shift and
# scale its saturation, then look up the ported GR style. Brightness is left alone (the value ratio
# between dpreview batches is mostly a batch/lighting difference, so it is not applied).
# Usage: rawmatch.py <scripts> <LR_PROFILES> <model.json> <ported_dir> <out_dir> <"GR III"|"GR IV">
import sys,struct,json,math,os
S=sys.argv[1]; LRP=sys.argv[2]; MJSON=sys.argv[3]; SRC_DIR=sys.argv[4]; DST_DIR=sys.argv[5]; CAM=sys.argv[6]
sys.argv=[sys.argv[0],S,LRP,'.','/dev/null',CAM]
exec(open(S+'/port.py').read().split('HD,SD,VD=90,16,16')[0])
M=json.load(open(MJSON)); TR=M["train"]; PR={int(k):v for k,v in M["params"].items()}
def pred(h,s,k):
    sh,ss,lam=PR[k]; num=0;wt=lam
    for p in TR:
        d=((h-p[1])+180)%360-180; w=math.exp(-0.5*(d/sh)**2)*math.exp(-0.5*((s-p[2])/ss)**2); num+=w*p[k]; wt+=w
    return num/wt
def corr(hdeg,s):
    fade=min(1.0,s/0.15)   # leave neutrals alone
    return pred(hdeg,s,3)*fade, math.exp(pred(hdeg,s,4)*fade), 1.0
# Both cameras reach the GR look tables at the same exposure-scaled base (renders normalised
# to the same scene white), so the GR BaselineExposureOffset is kept as is.
os.makedirs(DST_DIR,exist_ok=True)
for style in ["Standard","Positive Film","Negative Film","Vivid","Monotone","Soft Monotone","Hard Monotone"]:
    t=read(f"{SRC_DIR}/Sony ILCE-6300 {CAM} {style}.dcp"); H,Sd,V=tag(t,50981); E=2**tag(t,51109)[0]; P=Table((H,Sd,V),list(tag(t,50982)),1); d=list(tag(t,50982))
    for vi in range(V):
        v=dec(vi/(V-1)) if vi else 1e-4
        for hi in range(H):
            for si in range(1,Sd):
                # node X is exposure-scaled A6300 base (E*base); correct in base space, re-expose, look up
                X=hsv2rgb(hi*6/H,si/(Sd-1),v); h0,s0,v0=rgb2hsv(*X)
                dh,ks,kv=corr(h0*60,s0)
                X2=hsv2rgb((h0+dh*6/360)%6,min(s0*ks,1.0),dec(min(enc(v0/E)*kv,1.0)))
                T=P.apply([E*x for x in X2]); hT,sT,vT=rgb2hsv(*T); o=3*(vi*H*Sd+hi*Sd+si)
                d[o]=((hT-h0+3)%6-3)*60 if sT>1e-4 else 0.0; d[o+1]=min(sT,1)/s0; d[o+2]=enc(vT)/enc(v0) if v0>1e-7 else 1
    nt={k:(v[0],v[1],v[3]) for k,v in t.items()}; nt[50982]=(11,len(d),struct.pack('<%df'%len(d),*d))
    beo=tag(t,51109)[0]; nt[51109]=(10,1,struct.pack('<ii',int(round(beo*10000)),10000))
    write(f"{DST_DIR}/Sony ILCE-6300 {CAM} {style}.dcp",nt); print("built",style)
