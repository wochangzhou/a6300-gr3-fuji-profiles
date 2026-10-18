# Calibrate the A6300 "Adobe Standard Linear" base used by the Fuji LUT pack against
# real Lightroom output: X-S20/X-S10 + Adobe "Camera PROVIA" (target) vs A6300 + Provia LUT (current).
import sys,json,math,struct,numpy as np
L,E,G,LRP,REPO,DST=sys.argv[1:7]
sys.argv=[sys.argv[0],G,LRP,'.','/dev/null']
exec(open(G+'/port.py').read().split('HD,SD,VD=90,16,16')[0])
src=open(G+'/gr3/e2e.py').read(); exec(src[src.index('def de2000'):src.index('RAWC=json.load')])
WD65=np.array([0.95047,1.0,1.08883]); S2X=np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]])
def slab(rgb16):
    a=np.asarray(rgb16)/65535; lin=np.where(a<=0.04045,a/12.92,((a+0.055)/1.055)**2.4); X=S2X@lin; t=X/WD65
    f=np.where(t>216/24389,np.cbrt(t),(24389/27*t+16)/116); return [116*f[1]-16,500*(f[0]-f[1]),200*(f[1]-f[2])]
NAMES=["brown","skin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan","white","n8","n6.5","n5","n3.5","black"]
SECT=["red","red-orange","orange","yellow-orange","yellow","yellow-green","green","blue-green","blue","blue-violet","violet","red-violet"]
def chart(a,ox,oy,x0,y0,x1,y1): return {NAMES[j*6+i]:slab(np.asarray(a[int(oy+y0+(y1-y0)*j/3)-30:int(oy+y0+(y1-y0)*j/3)+30,int(ox+x0+(x1-x0)*i/5)-30:int(ox+x0+(x1-x0)*i/5)+30]).reshape(-1,3).astype(float).mean(0)) for j in range(4) for i in range(6)}
def wheel(a,ox,oy,cx,cy,f,rings):
    r={}
    for si,s in enumerate(SECT):
        an=math.radians(-105+30*si+9)
        for rn,rr in rings.items():
            x=int(ox+(cx+rr*math.cos(an))*f); y=int(oy+(cy+rr*math.sin(an))*f); r[f"{s}/{rn}"]=slab(np.asarray(a[y-10:y+10,x-10:x+10]).reshape(-1,3).astype(float).mean(0))
    return r
F=np.load(L+'/xs20.npy',mmap_mode='r'); A=np.load(L+'/sony_fj.npy',mmap_mode='r')
FC=chart(F,2444,468,195,166,1161,736); AC=chart(A,2350,450,182,162,1110,713)
FW=wheel(F,3848,457,213,190,598/400,{"outer":155,"tint":127,"mid":96,"inner":61}); AW=wheel(A,3700,440,210,192,575/400,{"outer":150,"tint":123,"mid":93,"inner":59})
B=json.load(open(E+'/base.json'))['a6300']; BW=json.load(open(E+'/wheel_base.json'))['a6300']
lumY=lambda c:0.2880*c[0]+0.7119*c[1]+0.0001*c[2]
# ---- exposure from grey ramp: A6300 base level -> output L (monotone), find base level giving Fuji L ----
G6=["black","n3.5","n5","n6.5","n8","white"]; ys=[lumY(B[n]) for n in G6]; ls=[AC[n][0] for n in G6]
def base_for_L(Lt):
    for i in range(len(ls)-1):
        if ls[i]<=Lt<=ls[i+1]: t=(Lt-ls[i])/(ls[i+1]-ls[i]); return math.exp(math.log(ys[i])+t*(math.log(ys[i+1])-math.log(ys[i])))
    return None
evs=[]
for n in ("n6.5","n5","n8"):
    y=base_for_L(FC[n][0]); evs.append(math.log2(y/lumY(B[n]))); print(f"  {n}: A6300 L {AC[n][0]:.1f} Fuji L {FC[n][0]:.1f} -> exposure {evs[-1]:+.3f} EV")
EV=float(np.mean(evs)); print(f"exposure correction (BaselineExposureOffset): {EV:+.3f} EV")
# ---- colour: output-space residual (Lab hue, chroma ratio) indexed by A6300 base hue/sat ----
def pairs(Bd,Ad,Fd):
    P=[]
    for n in Ad:
        h,s,v=rgb2hsv(*Bd[n]); a=Ad[n]; f=Fd[n]; Ca=math.hypot(a[1],a[2]); Cf=math.hypot(f[1],f[2])
        if s<0.06 or Ca<6 or Cf<6: continue
        dh=((math.degrees(math.atan2(f[2],f[1]))-math.degrees(math.atan2(a[2],a[1])))+180)%360-180
        P.append((h*60,s,dh,math.log(Cf/Ca),a,f,n))
    return P
TR=pairs(B,AC,FC); TE=pairs(BW,AW,FW)
def kp(h,s,pts,sh,ss,lam,k):
    num=0;wt=lam
    for p in pts:
        d=((h-p[0])+180)%360-180; w=math.exp(-0.5*(d/sh)**2)*math.exp(-0.5*((s-p[1])/ss)**2); num+=w*p[k]; wt+=w
    return num/wt
GRID=[(sh,ss,lam) for sh in (15,25,40,70) for ss in (0.15,0.3,1.0) for lam in (0.1,0.5,1,3)]
best={k:min((sum(abs(kp(p[0],p[1],TR[:i]+TR[i+1:],*g,k)-p[k]) for i,p in enumerate(TR))/len(TR),g) for g in GRID)[1] for k in (2,3)}
def predicted_out(p,pts):   # first-order: assume LUT passes small hue/chroma changes through ~1:1
    a=p[4]; h=math.degrees(math.atan2(a[2],a[1])); C=math.hypot(a[1],a[2])
    h2=h+kp(p[0],p[1],pts,*best[2],2); C2=C*math.exp(kp(p[0],p[1],pts,*best[3],3))
    return [p[5][0],C2*math.cos(math.radians(h2)),C2*math.sin(math.radians(h2))]   # L assumed fixed by exposure step
def rep(P,loo):
    d0=[];d1=[];a0=[];a1=[]
    for i,p in enumerate(P):
        pts=(TR[:i]+TR[i+1:]) if loo else TR; o=predicted_out(p,pts); t=p[5]; cur=[t[0],p[4][1],p[4][2]]
        d0.append(de2000(cur,t)); d1.append(de2000(o,t)); a0.append(cur[1]-t[1]); a1.append(o[1]-t[1])
    return f"ΔE(chroma/hue only) {np.mean(d0):.2f} -> {np.mean(d1):.2f}   Δa {np.mean(a0):+.2f} -> {np.mean(a1):+.2f}"
print("params",best); print("CHART LOO :",rep(TR,True)); print("WHEEL pred:",rep(TE,False),"(first-order prediction, verify with export)")
# ---- build base DCP: upstream A6300 Linear + 3D LookTable (hue/sat) + exposure offset ----
HD,SD,VD=90,16,16; row=[]
for hi in range(HD):
    for si in range(SD):
        s=si/(SD-1); h=hi*360/HD
        if si==0: row+=[0.0,1.0,1.0]; continue
        f=min(1,s/0.12); row+=[kp(h,s,TR,*best[2],2)*f, math.exp(kp(h,s,TR,*best[3],3)*f), 1.0]
look=row*VD
up=read(REPO+"/Adobe Standard Linear Profile/Sony ILCE-6300 Adobe Standard Linear.dcp")
t={k:(v[0],v[1],v[3]) for k,v in up.items()}
t[50981]=(4,3,struct.pack('<3I',HD,SD,VD)); t[50982]=(11,len(look),struct.pack('<%df'%len(look),*look)); t[51108]=(4,1,struct.pack('<I',1))
t[51109]=(10,1,struct.pack('<ii',int(round(EV*10000)),10000))
import os; os.makedirs(DST,exist_ok=True); write(DST+"/Sony ILCE-6300 Adobe Standard Linear.dcp",t)
r=read(DST+"/Sony ILCE-6300 Adobe Standard Linear.dcp"); print("built:",r[50936][2],"look",r[50981][2],"BEO",r[51109][2])
