# A6300 base colour -> Hasselblad X1D Phocus "Standard" (same dpreview scene).
# DNG order: HueSatMap -> exposure (x*gain, clip 1) -> LookTable -> ToneCurve(RGB hue-preserving)
import sys,json,math,bisect
S=sys.argv[1]; G=sys.argv[2]; sys.argv=[sys.argv[0],G,'x','.','/dev/null']
src=open(G+'/port.py').read(); exec("import math\n"+src[src.index('PP2XYZ='):src.index('def tag(t,k)')])
K=0.66                                   # design gain: A6300 white patch (base ~0.91) -> ~0.60 look input
A=json.load(open(S+'/base.json'))['a6300']; AW=json.load(open(S+'/wheel_base.json'))['a6300']
T=json.load(open(S+'/x1d_std_chart.json')); TW=json.load(open(S+'/x1d_std_wheel.json'))
lum=lambda c:0.2880*c[0]+0.7119*c[1]+0.0001*c[2]
GREYS=["black","n3.5","n5","n6.5","n8","white"]
xs=[0.0]+[K*lum(A[n]) for n in GREYS]+[1.0]; ys=[0.0]+[lum(T[n]) for n in GREYS]+[1.0]
# monotone cubic (Fritsch-Carlson)
def pchip(xs,ys):
    n=len(xs); d=[(ys[i+1]-ys[i])/(xs[i+1]-xs[i]) for i in range(n-1)]
    m=[d[0]]+[0 if d[i-1]*d[i]<=0 else 2/((1/d[i-1])+(1/d[i])) for i in range(1,n-1)]+[d[-1]]
    def f(x):
        if x<=0: return 0.0
        if x>=1: return 1.0
        i=min(max(bisect.bisect_right(xs,x)-1,0),n-2); h=xs[i+1]-xs[i]; t=(x-xs[i])/h
        h00=2*t**3-3*t**2+1; h10=t**3-2*t**2+t; h01=-2*t**3+3*t**2; h11=t**3-t**2
        return h00*ys[i]+h10*h*m[i]+h01*ys[i+1]+h11*h*m[i+1]
    return f
tc=pchip(xs,ys)
CURVE=[]; 
for i in range(256): x=(i/255)**2.2; CURVE+= [x, tc(x)]           # denser samples in the shadows
def finv(y):
    lo,hi=0.0,1.0
    for _ in range(50):
        mid=(lo+hi)/2; lo,hi=(mid,hi) if tc(mid)<y else (lo,mid)
    return (lo+hi)/2
def rgbtone(rgb):
    r=[min(max(x,0),1) for x in rgb]; lo,mid,hi=sorted(range(3),key=lambda k:r[k]); out=[0,0,0]
    out[hi]=tc(r[hi]); out[lo]=tc(r[lo]); out[mid]=out[lo]+(out[hi]-out[lo])*((r[mid]-r[lo])/(r[hi]-r[lo]) if r[hi]>r[lo] else 0); return out
def tone_inv(t):
    t=[min(max(x,0),0.9999) for x in t]; lo,mid,hi=sorted(range(3),key=lambda k:t[k]); out=[0,0,0]
    out[hi]=finv(t[hi]); out[lo]=finv(t[lo]); out[mid]=out[lo]+(out[hi]-out[lo])*((t[mid]-t[lo])/(t[hi]-t[lo]) if t[hi]>t[lo] else 0); return out
print("tone curve points (look-input -> Phocus PP Y):", [(round(a,3),round(b,3)) for a,b in zip(xs,ys)])
def pairs(Ad,Td):
    P=[]
    for n in Ad:
        X=[K*c for c in Ad[n]]; Tpre=tone_inv(Td[n]); hx,sx,vx=rgb2hsv(*X); ht,st,vt=rgb2hsv(*Tpre)
        if sx<0.06: continue
        P.append((n,hx*60,sx,((ht-hx+3)%6-3)*60,math.log(max(st,1e-4)/sx),math.log(enc(vt)/enc(vx)),X,Td[n]))
    return P
TR=pairs(A,T); TE=pairs(AW,TW)
def pred(h,s,pts,sh,ss,lam,k):
    num=0;wt=lam
    for p in pts:
        d=((h-p[1])+180)%360-180; w=math.exp(-0.5*(d/sh)**2)*math.exp(-0.5*((s-p[2])/ss)**2); num+=w*p[k]; wt+=w
    return num/wt
def loo(g,k): return sum(abs(pred(p[1],p[2],TR[:i]+TR[i+1:],*g,k)-p[k]) for i,p in enumerate(TR))/len(TR)
GRID=[(sh,ss,lam) for sh in (10,15,20,30,45) for ss in (0.1,0.2,0.35,1.0) for lam in (0.02,0.1,0.3,1)]
BEST={}
for k,nm in ((3,"hue"),(4,"sat"),(5,"val")):
    R=sorted((loo(g,k),g) for g in GRID); BEST[k]=R[0][1]; print(f"{nm}: chart mean|target| {sum(abs(p[k]) for p in TR)/len(TR):.3f}  LOO {R[0][0]:.3f}  params {R[0][1]}")
WD50=[0.9642,1.0,0.8249]
def lab(pp):
    X=mv(PP2XYZ,pp); fx=[(t/w)**(1/3) if t/w>216/24389 else (24389/27*t/w+16)/116 for t,w in zip(X,WD50)]
    return [116*fx[1]-16,500*(fx[0]-fx[1]),200*(fx[1]-fx[2])]
exec(open(G+'/gr3/e2e.py').read().split('def de2000')[1].join(['def de2000','']).split('RAWC=json')[0])
def apply_model(X):
    h,s,v=rgb2hsv(*X); fade=min(1,s/0.12)
    dh=pred(h*60,s,TR,*BEST[3],3)*fade; ks=math.exp(pred(h*60,s,TR,*BEST[4],4)*fade); kv=math.exp(pred(h*60,s,TR,*BEST[5],5)*fade)
    return hsv2rgb((h+dh*6/360)%6,min(s*ks,1),dec(min(enc(v)*kv,1)))
def report(label,P):
    e_tone=sorted(de2000(lab(rgbtone(p[6])),lab(p[7])) for p in P); e_full=sorted(de2000(lab(rgbtone(apply_model(p[6]))),lab(p[7])) for p in P)
    q=lambda e:f"{sum(e)/len(e):5.2f} (p90 {e[int(.9*(len(e)-1))]:5.2f})"
    print(f"{label}: tone curve only {q(e_tone)}   tone + look table {q(e_full)}")
report("CHART (train)",TR); report("WHEEL (independent)",TE)
json.dump({"K":K,"curve":CURVE,"train":[p[:6] for p in TR],"params":{str(k):v for k,v in BEST.items()}},open(S+'/hbmodel.json','w'))
