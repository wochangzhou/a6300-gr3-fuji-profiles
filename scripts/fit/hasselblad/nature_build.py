import sys,json,math,struct,os,numpy as np
NJ,DE,GS,SRC,OUT=sys.argv[1:6]
sys.path.insert(0,GS); from dcp import read
exec(open(DE).read())
D=json.load(open(NJ)); Sd={k:np.array(v) for k,v in D['std'].items()}; Nd={k:np.array(v) for k,v in D['nat'].items()}
PP2X=np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]); W50=np.array([0.9642,1,0.8249])
def lab(p):
    t=PP2X@np.clip(p,1e-7,None)/W50; f=np.where(t>216/24389,np.cbrt(t),(24389/27*t+16)/116); return np.array([116*f[1]-16,500*(f[0]-f[1]),200*(f[1]-f[2])])
Y=lambda p:float(PP2X[1]@p)
G=["black","n3.5","n5","n6.5","n8","white"]
# master luminance curve fY (linear->linear), log-log interp, anchored 0 and 1
lx=[math.log(Y(Sd[g])) for g in G]; ly=[math.log(Y(Nd[g])) for g in G]
def fY(y):
    if y<=0: return 0.0
    l=math.log(y)
    if l<lx[0]: return y*math.exp(ly[0]-lx[0])
    if l>lx[-1]: t=(l-lx[-1])/(0-lx[-1]); return math.exp(ly[-1]+t*(0-ly[-1]))
    return math.exp(np.interp(l,lx,ly))
def master(p): y=Y(p); return p*(fY(y)/y)
# neutral target: map Nature per channel so its greys land on master(Std greys)
T={g:master(Sd[g]) for g in G}
def chmap(p,src,dst):
    out=[]
    for c in range(3):
        xs=[math.log(src[g][c]) for g in G]; ys=[math.log(dst[g][c]) for g in G]; l=math.log(max(p[c],1e-7))
        if l<xs[0]: out.append(math.exp(l+ys[0]-xs[0]))
        elif l>xs[-1]: t=(l-xs[-1])/(0-xs[-1]); out.append(math.exp(ys[-1]+t*(0-ys[-1])))
        else: out.append(math.exp(np.interp(l,xs,ys)))
    return np.array(out)
Nn={k:chmap(Nd[k],Nd,T) for k in Nd}
enc=lambda x:12.92*x if x<=0.0031308 else 1.055*max(x,0)**(1/2.4)-0.055
def hsv(p):
    r,g,b=p; mx=max(p);mn=min(p);gap=mx-mn
    if gap<=0 or mx<=0: return 0,0,mx
    h=((g-b)/gap)%6 if r==mx else (2+(b-r)/gap if g==mx else 4+(r-g)/gap)
    return h*60,gap/mx,mx
P=[]
for k in Sd:
    if k in G: continue
    hs,ss,vs=hsv(Sd[k]); hb,sb,vb=hsv(master(Sd[k])); hn,sn,vn=hsv(Nn[k])
    if ss<0.08 or sn<0.05: continue
    P.append((hs,ss,((hn-hb)+180)%360-180,math.log(sn/sb),math.log(enc(vn)/enc(vb)),k))
def kp(h,s,pts,sh,ss,lam,k):
    num=0;wt=lam
    for p in pts:
        d=((h-p[0])+180)%360-180; w=math.exp(-0.5*(d/sh)**2)*math.exp(-0.5*((s-p[1])/ss)**2); num+=w*p[k]; wt+=w
    return num/wt
GRID=[(sh,ss,lam) for sh in (10,15,25,40) for ss in (0.15,0.3,1.0) for lam in (0.1,0.5,1,3)]
best={k:min((sum(abs(kp(p[0],p[1],P[:i]+P[i+1:],*g,k)-p[k]) for i,p in enumerate(P))/len(P),g) for g in GRID)[1] for k in (2,3,4)}
print("kernel params",best)
def hsv2rgb(h,s,v):
    h=(h/60)%6; i=int(h); f=h-i; p=v*(1-s);q=v*(1-s*f);t=v*(1-s*(1-f))
    return np.array([(v,t,p),(q,v,p),(p,v,t),(p,q,v),(t,p,v),(v,p,q)][i])
def decv(y): return y/12.92 if y<=0.04045 else ((y+0.055)/1.055)**2.4
def predict(p,pts):
    hs,ss,_=hsv(p); hb,sb,vb=hsv(master(p))
    return hsv2rgb(hb+kp(hs,ss,pts,*best[2],2), min(1,sb*math.exp(kp(hs,ss,pts,*best[3],3))), decv(enc(vb)*math.exp(kp(hs,ss,pts,*best[4],4))))
for lbl,sel in [("chart",lambda k:not k.startswith('w')),("wheel",lambda k:k.startswith('w'))]:
    ks=[k for k in Sd if sel(k)]; a0=[];a1=[];a2=[]
    for k in ks:
        idx=[i for i,p in enumerate(P) if p[5]==k]; pts=[p for p in P if p[5]!=k]
        a0.append(de2000(lab(Sd[k]),lab(Nn[k]))); a1.append(de2000(lab(master(Sd[k])),lab(Nn[k]))); a2.append(de2000(lab(predict(Sd[k],pts) if idx else master(Sd[k])),lab(Nn[k])))
    print(f"{lbl} vs neutralised Nature: Standard {np.mean(a0):.2f} | +curve {np.mean(a1):.2f} | +colour (leave-one-out) {np.mean(a2):.2f} (max {max(a2):.2f})")
# ---- build DCP: Standard + composed LookTable + composed ToneCurve ----
t=read(SRC); tags={k:(v[0],v[1],v[3]) for k,v in t.items()}
H_,S_,V_=t[50981][2]; old=list(t[50982][2]); new=[]
for vi in range(V_):
    for hi in range(H_):
        for si in range(S_):
            o=3*(vi*H_*S_+hi*S_+si); dh,sc,vc=old[o:o+3]
            if si==0: new+=[dh,sc,vc]; continue
            h=(hi*360/H_+dh)%360; s=min(1,si/(S_-1)*sc); fade=min(1,s/0.12)
            new+=[dh+kp(h,s,P,*best[2],2)*fade, sc*math.exp(kp(h,s,P,*best[3],3)*fade), vc*math.exp(kp(h,s,P,*best[4],4)*fade)]
tags[50982]=(11,len(new),struct.pack('<%df'%len(new),*new))
c=list(t[50940][2]); nc=[]
for i in range(0,len(c),2): nc+=[c[i],min(1.0,fY(c[i+1]))]
tags[50940]=(11,len(nc),struct.pack('<%df'%len(nc),*nc))
nm=b"Hasselblad X1D Nature\0"; tags[50936]=(2,len(nm),nm)
cp=b"Hasselblad X1D Standard + Phocus Nature colour/curve (dpreview studio scene)\0"; tags[50942]=(2,len(cp),cp)
ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
for k,(typ,cnt,raw) in ents:
    if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
    else:
        if (off+len(data))%2: data+=b'\0'
        ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
os.makedirs(OUT,exist_ok=True); path=OUT+"/Sony ILCE-6300 Hasselblad X1D Nature.dcp"
open(path,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data)
r=read(path); print("built",r[50936][2],"BEO",r[51109][2],"curve mid",[round(x,4) for x in r[50940][2][256:258]])
# ---- RGB curves for the 5500K/+10 cast (neutral -> Nature), LR curve space: ProPhoto + sRGB TRC, 0-255 ----
curves={}
for c,nmc in enumerate("RGB"):
    pts=[(0,0)]+[(round(enc(T[g][c])*255),round(enc(Nd[g][c])*255)) for g in G]+[(255,255)]
    curves[nmc]=pts
json.dump(curves,open(OUT+"/castcurves.json","w")); print(curves)
