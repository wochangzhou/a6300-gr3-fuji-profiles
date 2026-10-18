import sys,struct,math,random
sys.path.insert(0,sys.argv[1]); from dcp import read
LR,REPO,OUT=sys.argv[2],sys.argv[3],sys.argv[4]
PP2XYZ=[[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]
def inv(m):
    a,b,c=m[0];d,e,f=m[1];g,h,i=m[2]
    A=e*i-f*h;B=-(d*i-f*g);C=d*h-e*g;det=a*A+b*B+c*C
    return [[A/det,-(b*i-c*h)/det,(b*f-c*e)/det],[B/det,(a*i-c*g)/det,-(a*f-c*d)/det],[C/det,-(a*h-b*g)/det,(a*e-b*d)/det]]
def mv(m,v): return [sum(m[r][k]*v[k] for k in range(3)) for r in range(3)]
def mm(a,b): return [[sum(a[r][k]*b[k][c] for k in range(3)) for c in range(3)] for r in range(3)]
XYZ2PP=inv(PP2XYZ)
def m3(v): return [v[0:3],v[3:6],v[6:9]]
def enc(x):
    x=max(0.0,min(1.0,x)); return 12.92*x if x<=0.0031308 else 1.055*x**(1/2.4)-0.055
def dec(y):
    y=max(0.0,min(1.0,y)); return y/12.92 if y<=0.04045 else ((y+0.055)/1.055)**2.4
def rgb2hsv(r,g,b):
    mx=max(r,g,b);mn=min(r,g,b);gap=mx-mn
    if gap>0 and mx>0:
        if r==mx: h=(g-b)/gap; h+=6 if h<0 else 0
        elif g==mx: h=2+(b-r)/gap
        else: h=4+(r-g)/gap
        return h,gap/mx,mx
    return 0.0,0.0,mx
def hsv2rgb(h,s,v):
    if s<=0: return v,v,v
    h%=6; i=int(h); f=h-i; p=v*(1-s);q=v*(1-s*f);t=v*(1-s*(1-f))
    return [(v,t,p),(q,v,p),(p,v,t),(p,q,v),(t,p,v),(v,p,q)][i]
class Table:
    def __init__(s,dims,data,encoding=0): s.H,s.S,s.V=dims; s.d=data; s.e=encoding
    def entry(s,hi,si,vi):
        o=3*(vi*s.H*s.S+hi*s.S+si); return s.d[o:o+3]
    def apply(s,rgb):
        h,sat,v=rgb2hsv(*rgb)
        # DNG SDK: 2.5D tables (V==1) skip the input encode but still decode the output
        ve=enc(v) if (s.e==1 and s.V>1) else v
        hs=h*s.H/6.0; h0=int(math.floor(hs)); hf=hs-h0; h0%=s.H; h1=(h0+1)%s.H
        ss=min(max(sat,0),1)*(s.S-1); s0=min(int(ss),s.S-2) if s.S>1 else 0; sf=ss-s0 if s.S>1 else 0
        if s.V>1:
            vs=min(max(ve,0),1)*(s.V-1); v0=min(int(vs),s.V-2); vf=vs-v0; vl=[(v0,1-vf),(v0+1,vf)]
        else: vl=[(0,1.0)]
        acc=[0,0,0]
        for vi,wv in vl:
            for hi,wh in ((h0,1-hf),(h1,hf)):
                for si,ws in (((s0,1-sf),(s0+1,sf)) if s.S>1 else ((0,1.0),)):
                    w=wv*wh*ws
                    if w: e=s.entry(hi,si,vi); acc=[acc[k]+w*e[k] for k in range(3)]
        h=(h+acc[0]*6/360.0)%6; sat=min(sat*acc[1],1.0)
        if s.e==1: v=dec(min(ve*acc[2],1.0))
        else: v=min(v*acc[2],1.0)
        return hsv2rgb(h,sat,v)
def tag(t,k): return t[k][2]
def table(t,dk,dd,ek=None): return Table(tag(t,dk),tag(t,dd),tag(t,ek)[0] if ek and ek in t else 0)

grAS=read(f"{LR}/Adobe Standard/RICOH GR III Adobe Standard.dcp")
FM_AS=m3(tag(grAS,50965)); HSM_GR=table(grAS,50937,50939)
camToPP_AS=mm(XYZ2PP,FM_AS); PPToCam_AS=inv(camToPP_AS)
def base(c): return HSM_GR.apply(mv(camToPP_AS,c))
def base_inv(X):
    Y=list(X)
    for _ in range(40):
        Z=base(mv(PPToCam_AS,Y)); err=[X[k]-Z[k] for k in range(3)]; Y=[Y[k]+err[k] for k in range(3)]
        if max(map(abs,err))<1e-6: break
    return mv(PPToCam_AS,Y), max(map(abs,err))
sony=read(f"{REPO}/Adobe Standard Linear Profile/Sony ILCE-6300 Adobe Standard Linear.dcp")

def write(path,tags):
    ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
    for k,(typ,cnt,raw) in ents:
        if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
        else:
            if (off+len(data))%2: data+=b'\0'
            ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
    open(path,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data)
def f32(vals): return (11,len(vals),struct.pack('<%df'%len(vals),*vals))

HD,SD,VD=90,16,16
for style in ["Positive Film","Negative Film","Standard","Vivid","Monotone","Soft Monotone","Hard Monotone"]:
    pf=read(f"{LR}/Camera/Ricoh GR III/RICOH GR III Camera {style}.dcp")
    camToPP_PF=mm(XYZ2PP,m3(tag(pf,50965)))
    LOOK=table(pf,50981,50982,51108) if 50981 in pf else None
    # DNG render order: HueSatMap -> exposure (BaselineExposure + offset) -> LookTable -> ToneCurve.
    # Both cameras are normalised to the same scene white, so both LookTables see E*base.
    E=2**(tag(pf,51109)[0] if 51109 in pf else 0.0)
    def target(c):
        p=[E*x for x in mv(camToPP_PF,c)]; return LOOK.apply(p) if LOOK else [min(x,1.0) for x in p]
    out=[0.0]*(HD*SD*VD*3); worst=0
    for vi in range(VD):
        v=dec(vi/(VD-1)) if vi else 1e-4
        for hi in range(HD):
            for si in range(SD):
                s=max(si/(SD-1),1e-3)
                X=hsv2rgb(hi*6/HD,s,v)
                c,err=base_inv([x/E for x in X]); worst=max(worst,err)
                T=target(c); hT,sT,vT=rgb2hsv(*T); sT=min(sT,1.0); hX,sX,vX=rgb2hsv(*X)
                dh=((hT-hX+3)%6-3)*60 if sT>1e-4 else 0.0
                ss=sT/sX if si>0 else 1.0
                if si==0: dh=0.0
                vs=enc(vT)/enc(vX) if vX>1e-7 else 1.0
                o=3*(vi*HD*SD+hi*SD+si); out[o:o+3]=[dh,ss,vs]
    t={k:(v[0],v[1],v[3]) for k,v in sony.items() if k in (50708,50721,50722,50778,50779,50932,50937,50938,50939,50941,50964,50965)}
    name=f"GR III {style}".encode()+b'\0'; t[50936]=(2,len(name),name)
    cp=b'Ported from Adobe RICOH GR III profiles\0'; t[50942]=(2,len(cp),cp)
    t[50940]=(11,pf[50940][1],pf[50940][3])
    t[50981]=(4,3,struct.pack('<3I',HD,SD,VD)); t[50982]=f32(out)
    t[51108]=(4,1,struct.pack('<I',1))
    t[51109]=(10,1,struct.pack('<ii',int(round(tag(pf,51109)[0]*10000)) if 51109 in pf else 0,10000))
    t[51110]=(4,1,struct.pack('<I',1))
    p=f"{OUT}/Sony ILCE-6300 GR III {style}.dcp"; write(p,t)
    # verify: GR camera colors through ported look vs original GR style
    NEW=Table((HD,SD,VD),out,1); random.seed(1); e=0
    for _ in range(3000):
        c=[random.random()**2*0.9 for _ in range(3)]
        a=NEW.apply([E*x for x in base(c)]); b=target(c); e=max(e,max(abs(enc(a[k])-enc(b[k])) for k in range(3)))
    print(f"{style}: inverse residual {worst:.1e}, max round-trip err (sRGB-encoded) {e:.3f}")
