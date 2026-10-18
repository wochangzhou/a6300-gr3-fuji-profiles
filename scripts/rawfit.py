# Fit A6300 -> target base-colour correction from RAW chart patches (hue shift,
# saturation and value ratios as smooth functions of hue x saturation), choose
# kernel widths by leave-one-out on the chart, then test on independent samples.
import sys,json,math
S=sys.argv[1]; BASE=sys.argv[2]; EXTRA=sys.argv[3]; CAM=sys.argv[4]; OUTJ=sys.argv[5]
src=open(S+'/port.py').read(); exec("import math\n"+src[src.index('def enc'):src.index('class Table')])
B=json.load(open(BASE)); W=json.load(open(EXTRA))
def pairs(D):
    out=[]
    for n in D['a6300']:
        a=D['a6300'][n]; b=D[CAM][n]; ha,sa,va=rgb2hsv(*a); hb,sb,vb=rgb2hsv(*b)
        if sa<0.08 or sb<0.08: continue
        out.append((n,ha*60,sa,((hb-ha+3)%6-3)*60,math.log(sb/sa),math.log(enc(vb)/enc(va))))
    return out
TR=pairs(B); TE=pairs(W)
def pred(h,s,pts,sh,ss,lam,k):
    num=0;wt=lam
    for p in pts:
        d=((h-p[1])+180)%360-180; w=math.exp(-0.5*(d/sh)**2)*math.exp(-0.5*((s-p[2])/ss)**2)
        num+=w*p[k]; wt+=w
    return num/wt
def loo(sh,ss,lam,k): return sum(abs(pred(p[1],p[2],TR[:i]+TR[i+1:],sh,ss,lam,k)-p[k]) for i,p in enumerate(TR))/len(TR)
GRID=[(sh,ss,lam) for sh in (10,15,20,30,45) for ss in (0.1,0.2,0.35,1.0) for lam in (0.05,0.2,0.5,1,2)]
best={}
for k,name,unit in ((3,"hue","°"),(4,"sat","log"),(5,"val","log")):
    R=sorted((loo(*g,k),g) for g in GRID); best[k]=R[0][1]
    base_tr=sum(abs(p[k]) for p in TR)/len(TR); base_te=sum(abs(p[k]) for p in TE)/len(TE)
    te=sum(abs(pred(p[1],p[2],TR,*best[k],k)-p[k]) for p in TE)/len(TE)
    print(f"{CAM} {name}: chart uncorrected {base_tr:.4f}  chart LOO {R[0][0]:.4f} | WHEEL (independent) uncorrected {base_te:.4f} -> corrected {te:.4f}   params σh={best[k][0]} σs={best[k][1]} λ={best[k][2]}")
json.dump({"train":TR,"params":{str(k):v for k,v in best.items()}},open(OUTJ,"w"))
