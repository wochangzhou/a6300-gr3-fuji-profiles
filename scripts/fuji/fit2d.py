import sys,math; SD_=sys.argv[1]
exec(open(SD_+'/fit.py').read().split('if __name__')[0])
D=[(n,hp,pphsv(P[n][1])[1],dh,math.log(ks),math.log(kv),w) for n,hp,dh,ks,kv,w in PTS]
def pred(h,s,pts,sh,ss,lam,idx):
    num=0;W=lam
    for p in pts:
        d=((h-p[1])+180)%360-180; k=p[6]*math.exp(-0.5*(d/sh)**2)*(math.exp(-0.5*((s-p[2])/ss)**2) if ss else 1)
        num+=k*p[idx]; W+=k
    return num/W
def loo(sh,ss,lam,idx):
    return sum(abs(pred(p[1],p[2],D[:i]+D[i+1:],sh,ss,lam,idx)-p[idx]) for i,p in enumerate(D))/len(D)
base={3:sum(abs(p[3]) for p in D)/len(D),4:sum(abs(p[4]) for p in D)/len(D),5:sum(abs(p[5]) for p in D)/len(D)}
best={}
for idx,name in ((3,'hue°'),(4,'log sat'),(5,'log val')):
    R=sorted((loo(sh,ss,lam,idx),sh,ss,lam) for sh in (10,15,20,30,45,70) for ss in (0.1,0.2,0.35,None) for lam in (0.02,0.2,0.5,1,2,5))
    best[idx]=R[0]; print(f"{name:8s} uncorrected {base[idx]:.4f}  best LOO {R[0][0]:.4f}  (σh={R[0][1]}, σs={R[0][2]}, λ={R[0][3]})  top3: {[tuple(round(x,3) if isinstance(x,float) else x for x in r) for r in R[1:3]]}")
import json; json.dump({k:v[1:] for k,v in best.items()},open(SD_+'/best.json','w'))
sh,ss,lam=best[3][1:]
print("\nper-patch hue: measured / LOO-predicted with best params")
for i,p in enumerate(sorted(D,key=lambda p:p[1])):
    j=D.index(p); print(f"  {p[0]:13s} {p[3]:+5.1f} / {pred(p[1],p[2],D[:j]+D[j+1:],sh,ss,lam,3):+5.1f}")
