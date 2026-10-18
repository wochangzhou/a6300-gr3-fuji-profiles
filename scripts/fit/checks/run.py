import os
import sys,glob,numpy as np
sys.path.insert(0,sys.argv[1]); from dcp import read
D=np.load(sys.argv[2]); CP=os.path.expanduser('~/Library/Application Support/Adobe/CameraRaw/CameraProfiles/')
AS='/Applications/Adobe Lightroom Classic/Adobe Lightroom Classic.app/Contents/Resources/CameraProfiles/Adobe Standard/Sony ILCE-6300 Adobe Standard.dcp'
PPX=np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]); X2PP=np.linalg.inv(PPX)
X2S=np.array([[3.1338561,-1.6168667,-0.4906146],[-0.9787684,1.9161415,0.0334540],[0.0719453,-0.2289914,1.4052427]])
enc=lambda x:np.where(x<=0.0031308,12.92*x,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
dec=lambda y:np.where(y<=0.04045,y/12.92,((np.clip(y,0,None)+0.055)/1.055)**2.4)
def hsv(p):
    mx=p.max(-1); mn=p.min(-1); g=mx-mn; s=np.where(mx>0,g/np.maximum(mx,1e-12),0); r,gg,b=p[...,0],p[...,1],p[...,2]; gs=np.maximum(g,1e-12)
    h=np.where(mx==r,((gg-b)/gs)%6,np.where(mx==gg,2+(b-r)/gs,4+(r-gg)/gs)); return np.where(g>0,h*60,0),s,mx
def hsv2rgb(h,s,v):
    h=(h/60)%6; i=np.floor(h).astype(int)%6; f=h-np.floor(h); p=v*(1-s); q=v*(1-s*f); t=v*(1-s*(1-f))
    return np.stack([np.choose(i,[v,q,p,p,t,v]),np.choose(i,[t,v,v,q,p,p]),np.choose(i,[p,p,t,v,v,q])],-1)
def table(p,dims,data,encd):
    Hh,Ss,Vv=dims; T=np.array(data).reshape(Vv,Hh,Ss,3); h,s,v=hsv(p); ve=enc(v) if (encd and Vv>1) else v
    hs=h/360*Hh; h0=np.floor(hs).astype(int)%Hh; h1=(h0+1)%Hh; hf=hs-np.floor(hs)
    ss=np.clip(s,0,1)*(Ss-1); s0=np.minimum(ss.astype(int),Ss-2); sf=ss-s0
    if Vv>1: vs=np.clip(ve,0,1)*(Vv-1); v0=np.minimum(vs.astype(int),Vv-2); vf=vs-v0; VL=((v0,1-vf),(v0+1,vf))
    else: VL=((np.zeros_like(h0),np.ones_like(hf)),)
    acc=0
    for vi,wv in VL:
        for hi,wh in ((h0,1-hf),(h1,hf)):
            for si,ws in ((s0,1-sf),(s0+1,sf)): acc=acc+T[vi,hi,si]*(wv*wh*ws)[:,None]
    nv=dec(np.minimum(ve*acc[:,2],1)) if (encd and Vv>1) else np.minimum(v*acc[:,2],1)
    return hsv2rgb(h+acc[:,0],np.minimum(s*acc[:,1],1),nv)
HBc=np.array(read(CP+'Sony ILCE-6300 Hasselblad X1D Standard.dcp')[50940][2])
def tone(p,c):
    cx,cy=c[0::2],c[1::2]; p=np.clip(p,0,1); o=np.argsort(p,-1); lo=np.take_along_axis(p,o[:,:1],-1); mi=np.take_along_axis(p,o[:,1:2],-1); hi=np.take_along_axis(p,o[:,2:],-1)
    L=np.interp(lo,cx,cy); H=np.interp(hi,cx,cy); M=L+(H-L)*np.where(hi>lo,(mi-lo)/np.maximum(hi-lo,1e-12),0)
    out=np.empty_like(p); np.put_along_axis(out,o[:,:1],L,-1); np.put_along_axis(out,o[:,1:2],M,-1); np.put_along_axis(out,o[:,2:],H,-1); return out
def render(t,cam,use_look=True):
    FM=np.array(t[50965][2]).reshape(3,3); p=np.clip(cam@(X2PP@FM).T,0,None)
    if 50937 in t: p=table(p,t[50937][2],t[50939][2],False)
    ev=t[51109][2][0] if 51109 in t else 0; p=np.clip(p*2**ev,0,1)
    if 50981 in t and use_look: p=table(p,t[50981][2],t[50982][2],(t[51108][2][0] if 51108 in t else 0)==1)
    return tone(p,np.array(t[50940][2]) if 50940 in t else HBc)
def outside(p):
    s=(p@PPX.T)@X2S.T; return (s.min(1)<-0.002), (s.min(1)<-0.05)
profs=[('Adobe Standard (reference)',AS)]+[(p.split('6300 ')[1][:-4],p) for p in sorted(glob.glob(CP+'Sony ILCE-6300 *.dcp')) if 'Monotone' not in p]
print("%-28s %s"%("profile","outside sRGB: mean over 18 photos | worst photo | strongly outside (mean) | share added by colour table"))
for nm,p in profs:
    t=read(p); o1=[];o2=[];add=[]; worst=(0,'')
    for k in D.files:
        cam=D[k][::3]; a,b=outside(render(t,cam)); o1.append(a.mean()); o2.append(b.mean())
        if a.mean()>worst[0]: worst=(a.mean(),k)
        if 50981 in t: a0,_=outside(render(t,cam,False)); add.append(a.mean()-a0.mean())
    print(f"{nm:28s} {100*np.mean(o1):5.2f}% | {100*worst[0]:5.2f}% ({worst[1]}) | {100*np.mean(o2):5.2f}% | "+(f"{100*np.mean(add):+5.2f} pts (max {100*max(add):+.2f})" if add else "n/a"))
