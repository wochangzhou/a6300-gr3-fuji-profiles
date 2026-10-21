# Pure paired LookTable: start from an identity LookTable (no cross-camera base) on CUR's matrices/HueSatMap/tone curve,
# then fit the kernel-regression layer toward the synthetic target (synth.py); checkerboard train/test split, no saturation fade.
# Usage: pure_correct.py <samples_dir> <scripts> <ref_dir> <CUR.dcp> <de2000.py> <profile name> <note> <dh> <sat lo> <sat hi> <val lo> <val hi>
# (limits used: 25 0.6 1.6 0.85 1.15). Report rows: "AS+tone only" = identity table, "INSTALLED" = CUR's own LookTable.
import sys,json,math,numpy as np
O,GS,H,CUR,DE,NAME,NOTE=sys.argv[1:8]; CH,CS0,CS1,CV0,CV1=map(float,sys.argv[8:13]); sys.path.insert(0,GS); from dcp import read
exec(open(DE).read())
d=np.load(O+'/samples6.npz'); K=float(__import__("os").environ.get("KMODEL","0.66"))  # model exposure; 0.5033 matches the A6300 Adobe Standard greys (lens correction off) under the ACR3 curve
base=d['base']; tgt=np.clip(d['tgt'],1e-6,None); tgt1=np.clip(d['tgt1'],1e-6,None); xy=d['xy']; wh=d['wheel']>0
ok=base.max(1)<0.985; base,tgt,tgt1,xy,wh=base[ok],tgt[ok],tgt1[ok],xy[ok],wh[ok]
X=K*base
PP2X=np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]); W50=np.array([0.9642,1,0.8249])
def lab(p):
    t=np.clip(p,1e-7,None)@PP2X.T/W50; f=np.where(t>216/24389,np.cbrt(t),(24389/27*t+16)/116); return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def de(a,b): A=lab(a);B=lab(b); return np.array([de2000(A[i],B[i]) for i in range(len(A))])
def hsv(p):
    mx=p.max(-1); mn=p.min(-1); g=mx-mn; s=np.where(mx>0,g/np.maximum(mx,1e-12),0); r,gg,b=p[...,0],p[...,1],p[...,2]; gs=np.maximum(g,1e-12)
    h=np.where(mx==r,((gg-b)/gs)%6,np.where(mx==gg,2+(b-r)/gs,4+(r-gg)/gs)); return np.where(g>0,h*60,0),s,mx
def hsv2rgb(h,s,v):
    h=(h/60)%6; i=np.floor(h).astype(int)%6; f=h-np.floor(h); p=v*(1-s); q=v*(1-s*f); t=v*(1-s*(1-f))
    return np.stack([np.choose(i,[v,q,p,p,t,v]),np.choose(i,[t,v,v,q,p,p]),np.choose(i,[p,p,t,v,v,q])],-1)
enc=lambda x:np.where(x<=0.0031308,12.92*x,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
dec=lambda y:np.where(y<=0.04045,y/12.92,((np.clip(y,0,None)+0.055)/1.055)**2.4)
def rgbtone(p,cx,cy):
    p=np.clip(p,0,1); o=np.argsort(p,-1); lo=np.take_along_axis(p,o[...,:1],-1); hi=np.take_along_axis(p,o[...,2:],-1); mi=np.take_along_axis(p,o[...,1:2],-1)
    L=np.interp(lo,cx,cy); Hh=np.interp(hi,cx,cy); M=L+(Hh-L)*np.where(hi>lo,(mi-lo)/np.maximum(hi-lo,1e-12),0)
    out=np.empty_like(p); np.put_along_axis(out,o[...,:1],L,-1); np.put_along_axis(out,o[...,1:2],M,-1); np.put_along_axis(out,o[...,2:],Hh,-1); return out
def tone_inv(t,cx,cy):  # inverse of rgbtone for monotone curve
    return rgbtone(t,cy,cx)
def kpred(h,s,v,B,sh,ss,sv,lam,k):
    dhh=((h[:,None]-B[None,:,0])+180)%360-180
    w=np.exp(-0.5*(dhh/sh)**2-0.5*((s[:,None]-B[None,:,1])/ss)**2-0.5*((v[:,None]-B[None,:,2])/sv)**2)*np.sqrt(B[None,:,6])
    return (w*B[None,:,k]).sum(1)/(w.sum(1)+lam)
t=read(CUR); Hh,Ss,Vv=t[50981][2]; LT=np.zeros((Vv,Hh,Ss,3)); LT[...,1:]=1.0; cc=np.array(t[50940][2]); ccx,ccy=cc[0::2],cc[1::2]
def look_apply(Xin,LT,Hh,Ss,Vv):
    h,s,v=hsv(Xin); ve=enc(v); hs=h/360*Hh; h0=np.floor(hs).astype(int)%Hh; h1=(h0+1)%Hh; hf=hs-np.floor(hs)
    ss_=np.clip(s,0,1)*(Ss-1); s0=np.minimum(ss_.astype(int),Ss-2); sf=ss_-s0; vs=np.clip(ve,0,1)*(Vv-1); v0=np.minimum(vs.astype(int),Vv-2); vf=vs-v0
    acc=0
    for vi,wv in ((v0,1-vf),(v0+1,vf)):
        for hi,whh in ((h0,1-hf),(h1,hf)):
            for si,ws in ((s0,1-sf),(s0+1,sf)): acc=acc+LT[vi,hi,si]*(wv*whh*ws)[:,None]
    return hsv2rgb(h+acc[:,0],np.minimum(s*acc[:,1],1),dec(np.minimum(ve*acc[:,2],1)))

cbk=((xy[:,0]//125+xy[:,1]//125)%2==0); train=(~wh)&cbk; test=(~wh)&~cbk
def model_cur(Xin): return rgbtone(look_apply(Xin,LT,Hh,Ss,Vv),ccx,ccy)
B=json.load(open(H+'/base.json'))['a6300']; T=json.load(open(H+'/x1d_std_chart.json')); BW=json.load(open(H+'/wheel_base.json'))['a6300']; TW=json.load(open(H+'/x1d_std_wheel.json'))
cXb=K*np.array([B[n] for n in T]); cT=np.array([T[n] for n in T]); wXb=K*np.array([BW[n] for n in TW]); wT=np.array([TW[n] for n in TW])
def resid(Xi,Ti):
    Y=look_apply(Xi,LT,Hh,Ss,Vv); Tp=tone_inv(Ti,ccx,ccy); hx,sx,vx=hsv(Xi); hy,sy,vy=hsv(Y); ht,st,vt=hsv(Tp)
    return hx,sx,enc(vx),((ht-hy)+180)%360-180,np.log(np.maximum(st,1e-4)/np.maximum(sy,1e-4)),np.log(np.maximum(enc(vt),1e-4)/np.maximum(enc(vy),1e-4)),sx>0.06
hx,sx,vx,dh,ls,lv,c=resid(X,tgt)
def bins(mask):
    k=np.stack([(hx[mask]//6).astype(int),(sx[mask]//0.05).astype(int),(vx[mask]//0.1).astype(int)],1); u,inv=np.unique(k,axis=0,return_inverse=True); inv=inv.ravel(); idx=np.where(mask)[0]; out=[]
    for j in range(len(u)):
        sel=idx[inv==j]
        if len(sel)<3: continue
        out.append((np.median(hx[sel]),np.median(sx[sel]),np.median(vx[sel]),np.median(dh[sel]),np.median(ls[sel]),np.median(lv[sel]),min(len(sel),20)))
    return np.array(out)
TB=bins(train&c&(vx>0.25)); TB[:,6]*=np.clip(TB[:,1]/0.25,0.1,1)**2
ch=resid(cXb,cT); CB=np.stack([ch[0],ch[1],ch[2],ch[3],ch[4],ch[5],np.full(len(cT),20.0)],1)[ch[6]]
ALL=TB; print("train bins",len(TB),"+ chart",len(CB))
rng=np.random.default_rng(1); fold=rng.random(len(ALL))<0.5
GRID=[(sh,ss,sv,lam) for sh in (8,14,24) for ss in (0.08,0.15,0.3) for sv in (0.2,0.5,2.0) for lam in (0.5,2,8)]
BEST={}
for k in (3,4,5):
    sc=[]
    for g in GRID:
        a=ALL[fold];b=ALL[~fold]
        e=np.average(np.abs(kpred(b[:,0],b[:,1],b[:,2],a,*g,k)-b[:,k]),weights=b[:,6])+np.average(np.abs(kpred(a[:,0],a[:,1],a[:,2],b,*g,k)-a[:,k]),weights=a[:,6]); sc.append((e,g))
    base_err=(np.average(np.abs(ALL[:,k]),weights=ALL[:,6]))
    BEST[k]=min(sc)[1]; print("param",k,BEST[k],"cv err",round(min(sc)[0]/2,4),"(zero-model err",round(base_err,4),")")
def corr(Xin):
    h,s,v=hsv(Xin); ve=enc(v); f=np.minimum(1,s/0.12)
    return kpred(h,s,ve,ALL,*BEST[3],3)*f,kpred(h,s,ve,ALL,*BEST[4],4)*f,kpred(h,s,ve,ALL,*BEST[5],5)*f
def model_new(Xin):
    Y=look_apply(Xin,LT,Hh,Ss,Vv); a,b,c_=corr(Xin); h,s,v=hsv(Y)
    return rgbtone(hsv2rgb(h+a,np.minimum(s*np.exp(b),1),dec(np.minimum(enc(v)*np.exp(c_),1))),ccx,ccy)
def rep(name,fn):
    out=[]
    for lbl,Xi,Ti in (("X1D chart24",cXb,cT),("X1D wheel48",wXb,wT),("test colour",X[test&c],tgt[test&c]),("test neutral",X[test&~c],tgt[test&~c]),("wheel cells",X[wh],tgt[wh])):
        e=de(fn(Xi),Ti); A=lab(fn(Xi));Bb=lab(Ti); out.append(f"{lbl} {e.mean():.2f}/p90 {np.percentile(e,90):.1f}(Δa{(A[:,1]-Bb[:,1]).mean():+.1f})")
    print(f"{name:12s}"," | ".join(out))
rep("AS+tone only",model_cur); rep("pure (unclamped)",model_new)
for lbl,m in (("test colour",test&c),("test neutral",test&~c),("all colour",(~wh)&c)):
    e=de(tgt1[m],tgt[m]); A=lab(tgt1[m]);Bb=lab(tgt[m]); print(f"X1D Phocus vs synthetic target {lbl}: dE {e.mean():.2f} p90 {np.percentile(e,90):.1f} dL {(A[:,0]-Bb[:,0]).mean():+.2f} da {(A[:,1]-Bb[:,1]).mean():+.2f} db {(A[:,2]-Bb[:,2]).mean():+.2f} n {m.sum()}")
np.savez(O+'/corr.npz',ALL=ALL,P3=BEST[3],P4=BEST[4],P5=BEST[5])

e0=de(model_cur(wXb),wT); e1=de(model_new(wXb),wT); h,s,v=hsv(wXb); names=list(TW)
o=np.argsort(e1-e0)[::-1][:10]
for i in o: print(f"  {names[i]:22s} s {s[i]:.2f} h {h[i]:5.1f}  {e0[i]:.1f} -> {e1[i]:.1f}")
print("training bin sat max",ALL[:,1].max().round(2),"; wheel48 sat range",s.min().round(2),s.max().round(2))
# coverage: nearest training bin distance for wheel samples
for i in o[:5]:
    d=np.abs(((h[i]-ALL[:,0])+180)%360-180)/10+np.abs(s[i]-ALL[:,1])/0.1; print("   nearest bin for",names[i],ALL[np.argmin(d),:3].round(2),"n",ALL[np.argmin(d),6])
import struct,os
OUTD=O+'/out'; os.makedirs(OUTD,exist_ok=True)
# compose correction into the installed LookTable
hh=np.arange(Hh)*360/Hh; ssv=np.arange(Ss)/(Ss-1); vv=np.arange(Vv)/(Vv-1)
Hg,Sg,Vg=np.meshgrid(hh,ssv,vv,indexing='ij'); Xc=hsv2rgb(Hg.ravel(),Sg.ravel(),dec(Vg.ravel()))
a,b,c_=corr(Xc)
# reds: training data reach HSV s~0.81, so start the fade later there (hue weight 1 within 340..40 deg, 15 deg ramps)
_hd=np.minimum(np.abs(((Hg.ravel()-10)+180)%360-180),180); _r=np.clip((45-_hd)/15,0,1)
w=np.zeros_like(Hg.ravel())  # no high-saturation fade
a,b,c_=np.clip(a,-CH,CH),np.clip(b,np.log(CS0),np.log(CS1)),np.clip(c_,np.log(CV0),np.log(CV1))
a,b,c_=[z.reshape(Hh,Ss,Vv).transpose(2,0,1) for z in (a,b,c_)]   # -> V,H,S
NL=LT.copy(); NL[...,0]+=a; NL[...,1]*=np.exp(b); NL[...,2]*=np.exp(c_); NL[:,:,0,:]=LT[:,:,0,:]
print("correction stats: |dh| mean %.2f max %.1f, sat× range %.3f..%.3f, val× range %.3f..%.3f"%(np.abs(a).mean(),np.abs(a).max(),np.exp(b).min(),np.exp(b).max(),np.exp(c_).min(),np.exp(c_).max()))
LT2=NL
def model_v2(Xin): return rgbtone(look_apply(Xin,LT2,Hh,Ss,Vv),ccx,ccy)
rep("pure paired",model_v2)
LTI=np.array(t[50982][2]).reshape(Vv,Hh,Ss,3)
rep("INSTALLED",lambda Xin: rgbtone(look_apply(Xin,LTI,Hh,Ss,Vv),ccx,ccy))
tags={k:(v[0],v[1],v[3]) for k,v in t.items()}; flat=NL.astype('<f4').ravel()
tags[50982]=(11,len(flat),flat.tobytes()); nm=(NAME+"\0").encode(); tags[50936]=(2,len(nm),nm)
cp=(NOTE+"\0").encode(); tags[50942]=(2,len(cp),cp)
ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
for k,(typ,cnt,raw) in ents:
    if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
    else:
        if (off+len(data))%2: data+=b'\0'
        ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
p=OUTD+f'/Sony ILCE-6300 {NAME}.dcp'; open(p,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data)
r=read(p); print("built",r[50936][2],"BEO",r[51109][2],"look",r[50981][2])
