# Chart-anchored alignment: dense scene bins (weight sqrt(n), n<=30) plus the 18 chart patches as anchors with weight CW
# each. Kernel widths from the smooth CV (model_smooth_*.json). Reports chart leave-one-out, colour wheels (never
# trained) and the held-out scene half for several CW; writes one model per CW.
# Used: CW = 200 (data/gr/model_*.json): the chart is matched first, the scene covers the colours it does not reach.
# The portraits and colour wheels never train (dpreview swapped the prints between batches; inks fade), see fitcv.py.
# Usage: fit_anchor.py <pairs.npz> <fitcv.py model.json> <other model.json | -> <base.json> <gr3|gr4> <out prefix>
import sys,json,math,numpy as np,os
PAIRS,SM,CUR,BASE,CAM,OUT=sys.argv[1:7]
exec(open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'fitcv.py')).read().split("GRID=")[0].replace("PAIRS,CUR,BASE,CAM,OUT=sys.argv[1:6]","pass"))
SMM=json.load(open(SM)); best={int(k):tuple(v) for k,v in SMM['params'].items()}
B=json.load(open(BASE)); names=[n for n in B['a6300'] if n not in ('white','n8','n6.5','n5','n3.5','black')]
ca=np.array([B['a6300'][n] for n in names]); cb=np.array([B[CAM][n] for n in names]); hc,sc_,dhc,lsc,lvc,sac,sbc=feats(ca,cb)
Yc={3:dhc,4:lsc,5:lvc}; okc=[i for i in range(len(names)) if sac[i]>0.08]
def chart_pts(cw,skip=None): return [(names[i],float(hc[i]),float(sc_[i]),float(dhc[i]),float(lsc[i]),float(lvc[i]),float(cw*cw)) for i in okc if i!=skip] if cw>0 else []
dense=bins(col&~ex); trL=bins(col&~ex&left); trR=bins(col&~ex&~left)
rng=np.random.default_rng(0); sub=lambda m: np.where(m)[0][rng.permutation(m.sum())[:4000]]; iL,iR=sub(col&~ex&left),sub(col&~ex&~left); iW=np.where(col&wh)[0]
def loo(fn,par,wt=True): return np.mean([[abs(pred(hc[i:i+1],sc_[i:i+1],fn(i),*par[k],k,wt)[0]-Yc[k][i]) for k in (3,4,5)] for i in okc],0)
def insample(pts,par,wt=True): return np.mean([[abs(pred(hc[i:i+1],sc_[i:i+1],pts,*par[k],k,wt)[0]-Yc[k][i]) for k in (3,4,5)] for i in okc],0)
fmt=lambda e: f"{e[0]:6.2f} {e[1]:7.4f} {e[2]:7.4f}"
print(f"{'model':22s} | chart LOO hue/sat/val   | chart fit hue/sat/val   | wheels hue/sat/val      | scene half hue/sat/val")
if CUR!='-':
    M=json.load(open(CUR)); TRc=M['train']; Pc={int(k):v for k,v in M['params'].items()}
    c=loo(lambda i:[p for p in TRc if p[0]!=names[i]],Pc,False); f_=insample(TRc,Pc,False); w_=err(iW,TRc,Pc,False); s_=err(np.r_[iL,iR],TRc,Pc,False)
    print(f"{'other model':22s} | {fmt(c)} | {fmt(f_)} | {fmt(w_)} | {fmt(s_)}")
for cw in (0,60,100,200,400,1000):
    c=loo(lambda i: dense+chart_pts(cw,i),best); allp=dense+chart_pts(cw); f_=insample(allp,best); w_=err(iW,allp,best)
    s_=[(np.mean(np.abs(pred(h[iR],s[iR],trL+chart_pts(cw),*best[k],k)-Y[k][iR]))+np.mean(np.abs(pred(h[iL],s[iL],trR+chart_pts(cw),*best[k],k)-Y[k][iL])))/2 for k in (3,4,5)]
    print(f"{'dense + chart x'+str(cw):22s} | {fmt(c)} | {fmt(f_)} | {fmt(w_)} | {fmt(s_)}")
    json.dump({"train":allp,"params":{str(k):list(v) for k,v in best.items()}},open(f"{OUT}_cw{cw}.json","w"))
