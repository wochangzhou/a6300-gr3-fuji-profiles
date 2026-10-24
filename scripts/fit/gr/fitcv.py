# Fit the A6300 -> GR base-colour alignment (hue shift, log saturation ratio, log value ratio as kernel functions of
# hue x saturation, binned medians weighted by sqrt(count)) on dense cell pairs (dense_pairs.py); kernel widths by
# left/right-half cross-validation, floored at sigma_h 10 deg / sigma_s 0.1 for smoothness. Reports the held-out
# half, the colour wheels (never trained) and the chart; optionally against another model (rawmatch.py format).
# Usage: fitcv.py <pairs.npz> <other model.json | -> <base.json (chart, rawbase.py)> <gr3|gr4> <out model.json>
import sys,json,math,numpy as np
PAIRS,CUR,BASE,CAM,OUT=sys.argv[1:6]
d=np.load(PAIRS)
enc=lambda x:np.where(x<=0.0031308,12.92*x,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
def hsv(p):
    p=np.asarray(p,float); mx=p.max(-1); mn=p.min(-1); g=mx-mn; s=np.where(mx>0,g/np.maximum(mx,1e-12),0); r,gg,b=p[...,0],p[...,1],p[...,2]; gs=np.maximum(g,1e-12)
    h=np.where(mx==r,((gg-b)/gs)%6,np.where(mx==gg,2+(b-r)/gs,4+(r-gg)/gs)); return np.where(g>0,h*60,0),s,mx
def feats(a,b):
    ha,sa,va=hsv(a); hb,sb,vb=hsv(b); return ha,sa,((hb-ha+180)%360)-180,np.log(np.maximum(sb,1e-4)/np.maximum(sa,1e-4)),np.log(np.maximum(enc(vb),1e-4)/np.maximum(enc(va),1e-4)),sa,sb
h,s,dh,ls,lv,sa,sb=feats(d['baseA'],d['baseB']); col=(sa>0.08)&(sb>0.08); wh=d['wheel']>0; x=d['xy'][:,0]
left=x<np.median(x)
Y={3:dh,4:ls,5:lv}
def bins(m):
    k=np.stack([(h[m]//6).astype(int),(s[m]//0.05).astype(int)],1); u,inv=np.unique(k,axis=0,return_inverse=True); inv=inv.ravel(); idx=np.where(m)[0]; out=[]
    for j in range(len(u)):
        sel=idx[inv==j]
        if len(sel)<3: continue
        out.append(("bin",float(np.median(h[sel])),float(np.median(s[sel])),float(np.median(dh[sel])),float(np.median(ls[sel])),float(np.median(lv[sel])),float(min(len(sel),30))))
    return out
def pred(hq,sq,pts,sh,ss,lam,k,weighted=True):
    P=np.array([p[1:] for p in pts],float); dd=((hq[:,None]-P[None,:,0])+180)%360-180
    w=np.exp(-0.5*(dd/sh)**2-0.5*((sq[:,None]-P[None,:,1])/ss)**2)*(np.sqrt(P[None,:,5]) if (weighted and P.shape[1]>5) else 1)
    return (w*P[None,:,k-1]).sum(1)/(w.sum(1)+lam)
def err(m,pts,params,weighted=True):
    return [np.mean(np.abs(pred(h[m],s[m],pts,*params[k],k,weighted)-Y[k][m])) for k in (3,4,5)]
GRID=[(sh,ss,lam) for sh in (10,15,20,30) for ss in (0.1,0.15,0.2,0.35) for lam in (0.1,0.5,2,8)]
trL=bins(col&~wh&left); trR=bins(col&~wh&~left); teL=col&~wh&left; teR=col&~wh&~left
rng=np.random.default_rng(0); sub=lambda m: np.where(m)[0][rng.permutation(m.sum())[:4000]]
iL,iR=sub(teL),sub(teR)
best={}
for k in (3,4,5):
    sc=[]
    for g in GRID:
        e=(np.mean(np.abs(pred(h[iR],s[iR],trL,*g,k)-Y[k][iR]))+np.mean(np.abs(pred(h[iL],s[iL],trR,*g,k)-Y[k][iL])))/2; sc.append((e,g))
    best[k]=min(sc)[1]; print(f"k{k} best {best[k]} cv {min(sc)[0]:.4f}")
ALL=bins(col&~wh); HAVE=CUR!='-'
if HAVE: M=json.load(open(CUR)); TRc=M['train']; Pc={int(k):v for k,v in M['params'].items()}
iW=np.where(col&wh)[0]
def report(lbl,m):
    z=[np.mean(np.abs(Y[k][m])) for k in (3,4,5)]; c=err(m,TRc,Pc,weighted=False) if HAVE else [float('nan')]*3; n=err(m,ALL,best)
    print(f"{lbl:28s} hue deg {z[0]:.2f} -> other {c[0]:.2f} | dense {n[0]:.2f}   log sat {z[1]:.4f} -> {c[1]:.4f} | {n[1]:.4f}   log val {z[2]:.4f} -> {c[2]:.4f} | {n[2]:.4f}")
# held-out halves: dense model trained on the other half
def report_cv(lbl):
    z=[np.mean(np.abs(Y[k][np.r_[iL,iR]])) for k in (3,4,5)]; c=err(np.r_[iL,iR],TRc,Pc,weighted=False) if HAVE else [float('nan')]*3
    n=[(np.mean(np.abs(pred(h[iR],s[iR],trL,*best[k],k)-Y[k][iR]))+np.mean(np.abs(pred(h[iL],s[iL],trR,*best[k],k)-Y[k][iL])))/2 for k in (3,4,5)]
    print(f"{lbl:28s} hue deg {z[0]:.2f} -> other {c[0]:.2f} | dense {n[0]:.2f}   log sat {z[1]:.4f} -> {c[1]:.4f} | {n[1]:.4f}   log val {z[2]:.4f} -> {c[2]:.4f} | {n[2]:.4f}")
print("errors (uncorrected -> other model | dense model):")
report_cv("held-out half (scene)")
report("colour wheels (never trained)",iW)
# chart patches (independent of the dense cells' chart region? the chart is in the scene; shown for reference)
B=json.load(open(BASE)); names=[n for n in B['a6300'] if n not in ('white','n8','n6.5','n5','n3.5','black')]
ca=np.array([B['a6300'][n] for n in names]); cb=np.array([B[CAM][n] for n in names]); hc,sc_,dhc,lsc,lvc,sac,sbc=feats(ca,cb)
for nm,pts,par,wt in ((("chart: other model",TRc,Pc,False),) if HAVE else ())+(("chart: dense model",ALL,best,True),):
    e=[np.mean(np.abs(pred(hc,sc_,pts,*par[k],k,wt)-[dhc,lsc,lvc][k-3])) for k in (3,4,5)]
    print(f"  {nm:34s} hue {e[0]:.2f}  log sat {e[1]:.4f}  log val {e[2]:.4f}   (uncorrected {np.mean(np.abs(dhc)):.2f} / {np.mean(np.abs(lsc)):.4f} / {np.mean(np.abs(lvc)):.4f})")
json.dump({"train":ALL,"params":{str(k):list(v) for k,v in best.items()}},open(OUT,"w"))
print("bins",len(ALL))
