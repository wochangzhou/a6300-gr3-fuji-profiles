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
HD=t[50937][2]; H1=np.array(t[50938][2]).reshape(HD[1-1] if False else HD[2],HD[0],HD[1],3).copy(); H2=np.array(t[50939][2]).reshape(HD[2],HD[0],HD[1],3)
LD=t[50981][2]; LT=np.array(t[50982][2]); CV=np.array(t[50940][2]); K=0.66
T1=_ILL[t[50778][2][0]]; T2=_ILL[t[50779][2][0]]
def setup(neutral):
    xy=(0.3457,0.3585)
    for _ in range(30):
        w=_iw(_xy2cct(*xy),T1,T2); CM=_m3(_blend(t[50721][2],t[50722][2],w)); X=_mv(_inv(CM),neutral); s=sum(X); n=(X[0]/s,X[1]/s)
        if abs(n[0]-xy[0])+abs(n[1]-xy[1])<1e-7: break
        xy=n
    w=_iw(_xy2cct(*xy),T1,T2); FM=_m3(_blend(t[50964][2],t[50965][2],w)); return w,np.array(_mm(_XYZ2PP,FM))
class DS:
    def __init__(s,cam,tgt,pat):
        neutral=np.array([pat['n8'][k]+pat['n6.5'][k]+pat['n5'][k] for k in range(3)]); neutral=neutral/neutral[1]
        s.w,M=setup(list(neutral)); sc=0.9/(pat['white'][1]/neutral[1]); s.p0=np.clip((cam/neutral*sc)@M.T,0,None); s.tgt=tgt
    def out(s,H1_,g):
        HS=s.w*H1_+(1-s.w)*H2; b=table(s.p0,HD,HS,False); return tone(table(np.clip(K*g*b,0,1),LD,LT,True),CV)
NAMES=["brown","skin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan","white","n8","n6.5","n5","n3.5","black"]
GI=[NAMES.index(n) for n in ("white","n8","n6.5","n5","n3.5","black")]
# low light
Pl=json.load(open(LOW+'/patches_low.json'))['a6300']; cTl=np.array([np.load(LOW+'/cT_low.npy')][0])
dl=np.load(LOW+'/d/samples_low.npz'); Lc=DS(np.array([Pl[n] for n in NAMES]),cTl,Pl); Ld=DS(dl['cam'],dl['tgt'],Pl)
Pd=json.load(open(RW+'/patches_raw.json'))['a6300']; Tj=json.load(open(H+'/x1d_std_chart.json'))
dd=np.load(DAY+'/samples6.npz'); Dc=DS(np.array([Pd[n] for n in NAMES]),np.array([Tj[n] for n in NAMES]),Pd); Dd=DS(dd['cam'],dd['tgt'],Pd)
print(f"HSM weight on StdA table: low light {Lc.w:.3f}, daylight {Dc.w:.3f}")
xyl=dl['xy']; whl=dl['wheel']>0; chk=((xyl[:,0]//250+xyl[:,1]//250)%2==0)
_,s0l,_=hsv(Ld.p0); okl=(Ld.p0.max(1)<0.98)
trl=okl&~whl&chk&(s0l>0.08); tel=okl&~whl&~chk
xyd=dd['xy']; whd=dd['wheel']>0; okd=Dd.p0.max(1)<0.98; ted=okd&~whd&(xyd[:,0]>=1506)
def fit_g(H1_):
    best=min((np.mean(np.abs(lab(Lc.out(H1_,g)[GI])[:,0]-lab(cTl[GI])[:,0])),g) for g in np.exp(np.linspace(-1.8,-0.8,101))); return best[1]
def report(tag,H1_):
    g=fit_g(H1_); r=[]
    for lbl,ds,m,gg in (("LOW chart",Lc,slice(None),g),("LOW test colour",Ld,tel&(s0l>0.08),g),("LOW test neutral",Ld,tel&(s0l<=0.08),g),("LOW wheel",Ld,okl&whl,g),
                        ("DAY chart",Dc,slice(None),1.0),("DAY right colour",Dd,ted&(hsv(Dd.p0)[1]>0.08),1.0),("DAY right neutral",Dd,ted&(hsv(Dd.p0)[1]<=0.08),1.0),("DAY wheel",Dd,okd&whd,1.0)):
        o=ds.out(H1_,gg)[m]; r.append(f"{lbl} {de(o,ds.tgt[m]).mean():.2f}")
    print(f"{tag:10s} g {np.log2(g):+.2f}EV | "+" | ".join(r)); return g
H1n=H1.copy(); g=report("v2",H1n)
hh=np.arange(HD[0])*360/HD[0]; ssv=np.arange(HD[1])/(HD[1]-1)
def kp(hq,sq,B,sh,ss,lam,k):
    d=((hq[:,None]-B[None,:,0])+180)%360-180; w=np.exp(-0.5*(d/sh)**2-0.5*((sq[:,None]-B[None,:,1])/ss)**2)*B[None,:,5]; return (w*B[None,:,k]).sum(1)/(w.sum(1)+lam)
for it in range(6):
    def resid(ds,m,g_):
        o=ds.out(H1n,g_)[m]; tg=ds.tgt[m]; ho,so,vo=hsv(o); ht,st,vt=hsv(tg); hp,sp,_=hsv(ds.p0[m])
        return np.stack([hp,sp,((ht-ho)+180)%360-180,np.log(np.maximum(st,1e-4)/np.maximum(so,1e-4)),np.log(np.maximum(vt,1e-5)/np.maximum(vo,1e-5))],1)
    Rc=resid(Lc,np.array([i not in GI for i in range(24)]),g); Rd=resid(Ld,trl,g)
    k=np.stack([(Rd[:,0]//6).astype(int),(Rd[:,1]//0.05).astype(int)],1); u,inv=np.unique(k,axis=0,return_inverse=True); inv=inv.ravel()
    B=[np.r_[np.median(Rd[inv==j],0),min((inv==j).sum(),20)] for j in range(len(u)) if (inv==j).sum()>=3]
    B=np.array(B+[np.r_[r,20.0] for r in Rc]); B=np.c_[B[:,:5],B[:,5]]
    Bk=np.c_[B[:,0],B[:,1],B[:,2],B[:,3],B[:,4],B[:,5]]
    Hg,Sg=np.meshgrid(hh,ssv,indexing='ij'); hq=Hg.ravel(); sq=Sg.ravel(); fade=np.minimum(1,sq/0.12)
    dh=np.clip(kp(hq,sq,Bk,18,0.2,1.0,2),-12,12)*fade*0.7; ls=np.clip(kp(hq,sq,Bk,18,0.2,1.0,3),-0.25,0.25)*fade*0.7; lv=np.clip(kp(hq,sq,Bk,18,0.2,1.0,4),-0.2,0.2)*fade*0.7
    H1n[0,:,:,0]+=dh.reshape(HD[0],HD[1]); H1n[0,:,:,1]*=np.exp(ls.reshape(HD[0],HD[1])); H1n[0,:,:,2]*=np.exp(lv.reshape(HD[0],HD[1]))
    g=report(f"iter {it+1}",H1n)
np.save(OUTD+'/H1_new.npy',H1n)
flat=H1n.astype('<f4').ravel(); tags[50938]=(11,len(flat),flat.tobytes()); nm=b"Hasselblad X1D Standard T\0"; tags[50936]=(2,len(nm),nm)
ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
for k_,(typ,cnt,raw) in ents:
    if len(raw)<=4: ifd+=struct.pack('<HHI',k_,typ,cnt)+raw.ljust(4,b'\0')
    else:
        if (off+len(data))%2: data+=b'\0'
        ifd+=struct.pack('<HHII',k_,typ,cnt,off+len(data)); data+=raw
open(OUTD+'/Sony ILCE-6300 Hasselblad X1D Standard T.dcp','wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data); print("written")
