import sys,json,math,struct,numpy as np
GS,LRP,V2,DE,H,LOW,DAY,RW,OUTD=sys.argv[1:10]
sys.path.insert(0,GS); from dcp import read
exec(open(DE).read())
# --- scalar helpers from rawbase (CCT / weight / FM), captured before defining vector versions ---
S=GS; _a=sys.argv; sys.argv=[sys.argv[0],GS,LRP,'.','/dev/null']
src=open(GS+'/rawbase.py').read(); exec(src[src.index('from dcp import read'):src.index('P=json.load(open(PATCHES))')]); sys.argv=_a
_xy2cct,_iw,_blend,_m3,_inv,_mv,_mm,_XYZ2PP,_ILL=xy_to_cct,interp_w,blend,m3,inv,mv,mm,XYZ2PP,ILL_T
PPX=np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]); W50=np.array([0.9642,1,0.8249])
def lab(p):
    t=np.clip(p,1e-7,None)@PPX.T/W50; f=np.where(t>216/24389,np.cbrt(t),(24389/27*t+16)/116); return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def de(a,b): A=lab(a);B=lab(b); return np.array([de2000(A[i],B[i]) for i in range(len(A))])
enc=lambda x:np.where(x<=0.0031308,12.92*x,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
dec=lambda y:np.where(y<=0.04045,y/12.92,((np.clip(y,0,None)+0.055)/1.055)**2.4)
def hsv(p):
    mx=p.max(-1); mn=p.min(-1); g=mx-mn; s=np.where(mx>0,g/np.maximum(mx,1e-12),0); r,gg,b=p[...,0],p[...,1],p[...,2]; gs=np.maximum(g,1e-12)
    h=np.where(mx==r,((gg-b)/gs)%6,np.where(mx==gg,2+(b-r)/gs,4+(r-gg)/gs)); return np.where(g>0,h*60,0),s,mx
def hsv2rgb(h,s,v):
    h=(h/60)%6; i=np.floor(h).astype(int)%6; f=h-np.floor(h); p=v*(1-s); q=v*(1-s*f); t=v*(1-s*(1-f))
    return np.stack([np.choose(i,[v,q,p,p,t,v]),np.choose(i,[t,v,v,q,p,p]),np.choose(i,[p,p,t,v,v,q])],-1)
def table(p,dims,T,encd):
    Hh,Ss,Vv=dims; T=np.asarray(T).reshape(Vv,Hh,Ss,3); h,s,v=hsv(p); ve=enc(v) if (encd and Vv>1) else v
    hs=h/360*Hh; h0=np.floor(hs).astype(int)%Hh; h1=(h0+1)%Hh; hf=hs-np.floor(hs); ss=np.clip(s,0,1)*(Ss-1); s0=np.minimum(ss.astype(int),Ss-2); sf=ss-s0
    VL=(((np.minimum((np.clip(ve,0,1)*(Vv-1)).astype(int),Vv-2)),None),) if Vv>1 else ((np.zeros_like(h0),None),)
    if Vv>1:
        vs=np.clip(ve,0,1)*(Vv-1); v0=np.minimum(vs.astype(int),Vv-2); vf=vs-v0; VL=((v0,1-vf),(v0+1,vf))
    else: VL=((np.zeros_like(h0),np.ones_like(hf)),)
    acc=0
    for vi,wv in VL:
        for hi,wh in ((h0,1-hf),(h1,hf)):
            for si,ws in ((s0,1-sf),(s0+1,sf)): acc=acc+T[vi,hi,si]*(wv*wh*ws)[:,None]
    nv=dec(np.minimum(ve*acc[:,2],1)) if (encd and Vv>1) else np.minimum(v*acc[:,2],1)
    return hsv2rgb(h+acc[:,0],np.minimum(s*acc[:,1],1),nv)
def tone(p,c):
    cx,cy=c[0::2],c[1::2]; p=np.clip(p,0,1); o=np.argsort(p,-1); lo=np.take_along_axis(p,o[:,:1],-1); mi=np.take_along_axis(p,o[:,1:2],-1); hi=np.take_along_axis(p,o[:,2:],-1)
    L=np.interp(lo,cx,cy); Hh=np.interp(hi,cx,cy); M=L+(Hh-L)*np.where(hi>lo,(mi-lo)/np.maximum(hi-lo,1e-12),0)
    out=np.empty_like(p); np.put_along_axis(out,o[:,:1],L,-1); np.put_along_axis(out,o[:,1:2],M,-1); np.put_along_axis(out,o[:,2:],Hh,-1); return out

t=read(V2); tags={k:(v[0],v[1],v[3]) for k,v in t.items()}
HD=t[50937][2]; H1=np.array(t[50938][2]).reshape(HD[2],HD[0],HD[1],3); H2=np.array(t[50939][2]).reshape(HD[2],HD[0],HD[1],3)
LD=t[50981][2]; LTB=np.array(t[50982][2]); CV=np.array(t[50940][2]); K=0.66
FM1=np.array(t[50964][2]).reshape(3,3); FM2=np.array(t[50965][2]).reshape(3,3)
T1=_ILL[t[50778][2][0]]; T2=_ILL[t[50779][2][0]]
def wfor(neutral):
    xy=(0.3457,0.3585)
    for _ in range(30):
        w=_iw(_xy2cct(*xy),T1,T2); CM=_m3(_blend(t[50721][2],t[50722][2],w)); X=_mv(_inv(CM),list(neutral)); s_=sum(X); n=(X[0]/s_,X[1]/s_)
        if abs(n[0]-xy[0])+abs(n[1]-xy[1])<1e-7: break
        xy=n
    return _iw(_xy2cct(*xy),T1,T2)
X2PP=np.array(_XYZ2PP); W50=np.array([0.9642,1,0.8249])
class DS:
    def __init__(s,cam,tgt,pat):
        n=np.array([pat['n8'][k]+pat['n6.5'][k]+pat['n5'][k] for k in range(3)]); n=n/n[1]; s.w=wfor(list(n)); sc=0.9/(pat['white'][1]/n[1]); s.c=cam/n*sc; s.tgt=tgt
    def out(s,F1,F2,g):
        FM=s.w*F1+(1-s.w)*F2; p=np.clip(s.c@(X2PP@FM).T,0,None); b=table(p,HD,s.w*H1+(1-s.w)*H2,False); return tone(table(np.clip(K*g*b,0,1),LD,LTB,True),CV)
NAMES=["brown","skin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan","white","n8","n6.5","n5","n3.5","black"]
Pl=json.load(open(LOW+'/patches_low.json'))['a6300']; cTl=np.load(LOW+'/cT_low.npy'); dl=np.load(LOW+'/d/samples_low.npz')
Lc=DS(np.array([Pl[n] for n in NAMES]),cTl,Pl); Ld=DS(dl['cam'],dl['tgt'],Pl)
Pd=json.load(open(RW+'/patches_raw.json'))['a6300']; Tj=json.load(open(H+'/x1d_std_chart.json')); dd=np.load(DAY+'/samples6.npz')
Dc=DS(np.array([Pd[n] for n in NAMES]),np.array([Tj[n] for n in NAMES]),Pd); Dd=DS(dd['cam'],dd['tgt'],Pd)
print(f"StdA weight: low {Lc.w:.3f}, day {Dc.w:.3f}")
GI=[NAMES.index(n) for n in ("white","n8","n6.5","n5","n3.5","black")]; N5=NAMES.index("n5")
g=min((abs(lab(Lc.out(FM1,FM2,g)[[N5]])[0,0]-lab(cTl[[N5]])[0,0]),g) for g in np.exp(np.linspace(-2.5,0.5,601)))[1]
xy=dl['xy']; wh=dl['wheel']>0; ok=(Ld.c.max(1)<0.98*Ld.c.max())
chk=((xy[:,0]//250+xy[:,1]//250)%2==0)
LTg=lab(Ld.tgt); hT=np.degrees(np.arctan2(LTg[:,2],LTg[:,1]))%360; CT=np.hypot(LTg[:,1],LTg[:,2])
skin=ok&~wh&(hT>20)&(hT<75)&(CT>8)&(CT<40)&(LTg[:,0]>25)&(LTg[:,0]<85)
col=ok&~wh&(CT>8)
tr=col&chk; te=col&~chk; sk_tr=skin&chk; sk_te=skin&~chk
print("cells: train colour",tr.sum(),"test colour",te.sum(),"skin train",sk_tr.sum(),"skin test",sk_te.sum(),"wheel",(ok&wh).sum())
cc=np.arange(24)<18
def metrics(F1,F2,tag):
    oc=Lc.out(F1,F2,g); od=Ld.out(F1,F2,g)
    r=dict(chart=de(oc[cc],cTl[cc]).mean(),skinpatch=de(oc[[1]],cTl[[1]])[0],test=de(od[te][::3],Ld.tgt[te][::3]).mean(),skin=de(od[sk_te],Ld.tgt[sk_te]).mean(),wheel=de(od[ok&wh],Ld.tgt[ok&wh]).mean(),grey=de(oc[GI],cTl[GI]).mean())
    dc=Dc.out(F1,F2,1.0); r['day_chart']=de(dc[cc],Dc.tgt[cc]).mean()
    print(f"{tag:12s} "+" | ".join(f"{k} {v:.2f}" for k,v in r.items())); return r
base=metrics(FM1,FM2,"current")
# --- correction C in XYZ (D50) space applied to FM1: FM1' = C @ FM1, with C @ W50 = W50 (neutrals stay neutral)
def Cmat(q):   # 6 free off-diagonal terms; diagonal chosen so that C @ W50 = W50 (neutrals stay neutral)
    C=np.zeros((3,3)); off=[(0,1),(0,2),(1,0),(1,2),(2,0),(2,1)]
    for (i,j),v in zip(off,q): C[i,j]=v
    for i in range(3): C[i,i]=(W50[i]-sum(C[i,j]*W50[j] for j in range(3) if j!=i))/W50[i]
    return C
idx_tr=np.where(tr)[0][::4]; sk_i=np.where(sk_tr)[0]
def loss(q):
    F1=Cmat(q)@FM1; F2=FM2+Lc_wd/(1-Lc_wd)*(FM1-F1)
    oc=Lc.out(F1,F2,g); od=Ld.out(F1,F2,g)
    a=np.r_[de(od[idx_tr],Ld.tgt[idx_tr]),np.repeat(de(oc[cc],cTl[cc]),40)].mean()
    sk=de(od[sk_i],Ld.tgt[sk_i]).mean(); pen=20*max(0,sk-skin0)**2
    return a+pen+LAM*float(np.sum((Cmat(q)-np.eye(3))**2))
import os; LAM=float(os.environ['LAM']); Lc_wd=Dc.w; skin0=de(Ld.out(FM1,FM2,g)[sk_i],Ld.tgt[sk_i]).mean()
x=np.zeros(6); st=np.full(6,0.05); b=loss(x); print("start loss %.3f, skin(train) %.2f"%(b,skin0))
for it in range(300):
    imp=False
    for i in range(6):
        for sg in (1,-1):
            y=x.copy(); y[i]+=sg*st[i]; v=loss(y)
            if v<b: x,b,imp=y,v,True
    if not imp: st/=2
    if st.max()<2e-4: break
C=Cmat(x); print("C =\n",np.round(C,4)); F1n=C@FM1; F2n=FM2+Lc_wd/(1-Lc_wd)*(FM1-F1n)
new=metrics(F1n,F2n,"3x3 fitted")
print("daylight blended FM unchanged:",np.abs((Dc.w*F1n+(1-Dc.w)*F2n)-(Dc.w*FM1+(1-Dc.w)*FM2)).max())
np.save(OUTD+f'/FM1n_{LAM}.npy',F1n); np.save(OUTD+f'/FM2n_{LAM}.npy',F2n); print('|C-I| =',round(float(np.sqrt(np.sum((C-np.eye(3))**2))),3))
