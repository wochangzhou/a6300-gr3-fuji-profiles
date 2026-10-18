# Refine the A6300 "Hasselblad X1D Standard" profile from REAL Lightroom output:
# residual = Phocus target vs LR export of A6300 with the current profile, both taken
# back through our tone curve to look-table output space; correct chromatic nodes only.
import sys,json,math,bisect,struct,numpy as np
H,L,G,LRP,DSTDIR=sys.argv[1:6]
sys.argv=[sys.argv[0],G,LRP,'.','/dev/null']
exec(open(G+'/port.py').read().split('HD,SD,VD=90,16,16')[0])
src=open(G+'/gr3/e2e.py').read(); exec(src[src.index('def de2000'):src.index('RAWC=json.load')])
M=json.load(open(H+'/hbmodel.json')); K=M['K']; cx=M['curve'][0::2]; cy=M['curve'][1::2]
def tc(x): x=min(max(x,0),1); i=min(max(bisect.bisect_right(cx,x)-1,0),len(cx)-2); return cy[i]+(cy[i+1]-cy[i])*(x-cx[i])/(cx[i+1]-cx[i])
def finv(y): y=min(max(y,0),0.99999); i=min(max(bisect.bisect_right(cy,y)-1,0),len(cy)-2); return cx[i]+(cx[i+1]-cx[i])*(y-cy[i])/(cy[i+1]-cy[i])
def tone_inv(t):
    t=[min(max(x,0),0.99999) for x in t]; lo,mid,hi=sorted(range(3),key=lambda k:t[k]); o=[0,0,0]; o[hi]=finv(t[hi]); o[lo]=finv(t[lo])
    o[mid]=o[lo]+(o[hi]-o[lo])*((t[mid]-t[lo])/(t[hi]-t[lo]) if t[hi]>t[lo] else 0); return o
def rgbtone(rgb):
    r=[min(max(x,0),1) for x in rgb]; lo,mid,hi=sorted(range(3),key=lambda k:r[k]); o=[0,0,0]; o[hi]=tc(r[hi]); o[lo]=tc(r[lo])
    o[mid]=o[lo]+(o[hi]-o[lo])*((r[mid]-r[lo])/(r[hi]-r[lo]) if r[hi]>r[lo] else 0); return o
BR=[[1.0478112,0.0228866,-0.0501270],[0.0295424,0.9904844,-0.0170491],[-0.0092345,0.0150436,0.7521316]]
S2X=[[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]]; S2PP=mm(XYZ2PP,mm(BR,S2X))
WD50=[0.9642,1.0,0.8249]
def lab(pp):
    X=mv(PP2XYZ,pp); fx=[(t/w)**(1/3) if t/w>216/24389 else (24389/27*t/w+16)/116 for t,w in zip(X,WD50)]; return [116*fx[1]-16,500*(fx[0]-fx[1]),200*(fx[1]-fx[2])]
a=np.load(L+'/sony_hb.npy',mmap_mode='r')
def lrpp(x,y,hw): b=np.asarray(a[y-hw:y+hw,x-hw:x+hw]).reshape(-1,3).astype(float).mean(0)/65535; return mv(S2PP,[dec(v) for v in b])
NAMES=["brown","skin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan","white","n8","n6.5","n5","n3.5","black"]
LRc={NAMES[j*6+i]:lrpp(int(2350+182+928*i/5),int(450+162+551*j/3),30) for j in range(4) for i in range(6)}
SECT=["red","red-orange","orange","yellow-orange","yellow","yellow-green","green","blue-green","blue","blue-violet","violet","red-violet"]
RINGS={"outer":160,"tint":131,"mid":99,"inner":63}
LRw={f"{s}/{rn}":lrpp(int(3710+(212+r*math.cos(math.radians(-105+30*si+9)))*1.375),int(460+(188+r*math.sin(math.radians(-105+30*si+9)))*1.375),10) for si,s in enumerate(SECT) for rn,r in RINGS.items()}
A=json.load(open(H+'/base.json'))['a6300']; AW=json.load(open(H+'/wheel_base.json'))['a6300']
T=json.load(open(H+'/x1d_std_chart.json')); TW=json.load(open(H+'/x1d_std_wheel.json'))
def pairs(Ab,LRo,Tg):
    P=[]
    for n in LRo:
        X=[K*c for c in Ab[n]]; hx,sx,vx=rgb2hsv(*X); cur=tone_inv(LRo[n]); tgt=tone_inv(Tg[n])
        hc,sc_,vc=rgb2hsv(*cur); ht,st,vt=rgb2hsv(*tgt)
        if sx<0.06 or sc_<0.03 or st<0.03: continue
        P.append((hx*60,sx,((ht-hc+3)%6-3)*60,math.log(st/sc_),math.log(enc(vt)/enc(vc)),cur,LRo[n],Tg[n]))
    return P
TR=pairs(A,LRc,T); TE=pairs(AW,LRw,TW)

def lab2pp(L):
    fy=(L[0]+16)/116; fx=fy+L[1]/500; fz=fy-L[2]/200
    inv=lambda f:f**3 if f**3>216/24389 else (116*f-16)/(24389/27)
    X=[inv(fx)*WD50[0],inv(fy)*WD50[1],inv(fz)*WD50[2]]; return mv(XYZ2PP,X)
def chroma_w(pp): l=lab(pp); return min(1.0,math.hypot(l[1],l[2])/15.0)   # 0 at neutral, full from C*=15
def shift(Tpre,da,db):
    out=rgbtone(Tpre); l=lab(out); w=chroma_w(out); l2=[l[0],l[1]+da*w,l[2]+db*w]; return tone_inv(lab2pp(l2))
def casts(P):
    return np.mean([lab(p[6])[1]-lab(p[7])[1] for p in P]), np.mean([lab(p[6])[2]-lab(p[7])[2] for p in P])
def stats(P,da,db):
    de=[];a_=[];b_=[]
    for p in P:
        la=lab(rgbtone(shift(p[5],da,db))); lt=lab(p[7]); de.append(de2000(la,lt)); a_.append(la[1]-lt[1]); b_.append(la[2]-lt[2])
    de.sort(); return f"ΔE {np.mean(de):4.2f} (p90 {de[int(.9*(len(de)-1))]:4.2f}, max {de[-1]:4.1f})  cast Δa {np.mean(a_):+5.2f} Δb {np.mean(b_):+5.2f}"

def labhue(pp): l=lab(pp); return math.degrees(math.atan2(l[2],l[1]))%360
D=[(labhue(p[6]),lab(p[6])[1]-lab(p[7])[1],lab(p[6])[2]-lab(p[7])[2]) for p in TR]   # residual by Lab hue of current output
def kp(h,pts,sh,lam,k):
    num=0;wt=lam
    for p in pts:
        d=((h-p[0])+180)%360-180; w=math.exp(-0.5*(d/sh)**2) if sh<1e6 else 1.0; num+=w*p[k]; wt+=w
    return num/wt
def shift_h(Tpre,pts,sh,lam,useb):
    out=rgbtone(Tpre); l=lab(out); w=chroma_w(out); h=labhue(out)
    da=-kp(h,pts,sh,lam,1)*w; db=-kp(h,pts,sh,lam,2)*w if useb else 0.0
    return tone_inv(lab2pp([l[0],l[1]+da,l[2]+db]))
def ev(P,pts,sh,lam,useb):
    de=[];a_=[];b_=[]
    for p in P:
        la=lab(rgbtone(shift_h(p[5],pts,sh,lam,useb))); lt=lab(p[7]); de.append(de2000(la,lt)); a_.append(la[1]-lt[1]); b_.append(la[2]-lt[2])
    return np.mean(de),np.mean(a_),np.mean(b_),sorted(de)
def loo(sh,lam,useb):
    de=[];a_=[]
    for i,p in enumerate(TR):
        rest=D[:i]+D[i+1:]; la=lab(rgbtone(shift_h(p[5],rest,sh,lam,useb))); lt=lab(p[7]); de.append(de2000(la,lt)); a_.append(la[1]-lt[1])
    return np.mean(de),np.mean(a_)
res=[]
for useb in (False,True):
    for sh in (30,60,90,1e9):
        for lam in (0.1,1,3,10):
            e,a_=loo(sh,lam,useb); res.append((e,sh,lam,useb,a_))
res.sort(); print("best by chart LOO ΔE:"); 
for r in res[:5]: print(f"   σh={'global' if r[1]>1e6 else r[1]} λ={r[2]} fix b*={r[3]}  LOO ΔE {r[0]:.3f}  LOO cast Δa {r[4]:+.2f}")
e,sh,lam,useb,_=res[0]
m,a_,b_,ds=ev(TE,D,sh,lam,useb); m0,a0,b0,ds0=ev(TE,D,1e9,1e9,False)
print(f"WHEEL now: ΔE {m0:.2f} p90 {ds0[int(.9*(len(ds0)-1))]:.2f} cast Δa {a0:+.2f} Δb {b0:+.2f}")
print(f"WHEEL chosen model: ΔE {m:.2f} p90 {ds[int(.9*(len(ds)-1))]:.2f} cast Δa {a_:+.2f} Δb {b_:+.2f}")
json.dump({"pts":D,"sh":sh,"lam":lam,"useb":useb},open(H+"/hbshift_model.json","w"))
if DSTDIR!='-':
    import os
    t=read(os.path.expanduser("~/Library/Application Support/Adobe/CameraRaw/CameraProfiles/Sony ILCE-6300 Hasselblad X1D Standard.dcp")); Hh,Sd,Vd=tag(t,50981); T0=Table((Hh,Sd,Vd),list(tag(t,50982)),1); d=list(tag(t,50982))
    for vi in range(Vd):
        v=dec(vi/(Vd-1)) if vi else 1e-4
        for hi in range(Hh):
            for si in range(1,Sd):
                X=hsv2rgb(hi*6/Hh,si/(Sd-1),v); h0,s0,v0=rgb2hsv(*X); Tn=shift_h(T0.apply(X),D,sh,lam,useb); hT,sT,vT=rgb2hsv(*Tn); o=3*(vi*Hh*Sd+hi*Sd+si)
                d[o]=((hT-h0+3)%6-3)*60 if sT>1e-4 else 0.0; d[o+1]=min(sT,1)/s0; d[o+2]=enc(vT)/enc(v0) if v0>1e-7 else 1
    nt={k:(v[0],v[1],v[3]) for k,v in t.items()}; nt[50982]=(11,len(d),struct.pack('<%df'%len(d),*d))
    os.makedirs(DSTDIR,exist_ok=True); write(DSTDIR+"/Sony ILCE-6300 Hasselblad X1D Standard.dcp",nt); print("built")
