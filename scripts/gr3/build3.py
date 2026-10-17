import sys,struct,math; LRP=sys.argv[2]; SD_=sys.argv[1]
exec(open(SD_+'/fit.py').read().split('if __name__')[0])
WARM=[p for p in PTS if p[0] in ("brown","skin","orange","modred","red","orangeyellow","yellow")]
KV=math.exp(sum(math.log(p[4])*p[5] for p in PTS)/sum(p[5] for p in PTS))
def satcurve(s):
    K=[(0.41,5.1),(0.56,3.1),(0.84,1.1)]
    if s<=K[0][0]: return K[0][1]
    for (s0,a),(s1,b) in zip(K,K[1:]):
        if s<=s1: return a+(b-a)*(s-s0)/(s1-s0)
    return K[-1][1]
def band(h):
    if 15<=h<=35: return 1.0
    if h<15:
        d=15-h; return 0.5*(1+math.cos(math.pi*d/5)) if d<5 else 0.0
    d=h-35; return 0.5*(1+math.cos(math.pi*d/10)) if d<10 else 0.0
def corr(hpp,s):
    d=((hpp-25)+180)%360-180; fade=0.5*(1+math.cos(math.pi*min(abs(d),60)/60))
    b=band(hpp%360)
    dh=(1-b)*fit(hpp,WARM)[0]*fade+b*satcurve(s); w=min(1,s/0.3)
    return dh*w, 1-(1-KV)*w
# LOO on warm cluster
e0=[];e1=[]
for i,p in enumerate(WARM):
    others=WARM[:i]+WARM[i+1:]; d=((p[1]-25)+180)%360-180; fade=0.5*(1+math.cos(math.pi*min(abs(d),60)/60))
    e1.append(abs(fit(p[1],others)[0]*fade-p[2])); e0.append(abs(p[2]))
#print(f"warm hue LOO err {sum(e1)/len(e1):.2f}° vs uncorrected {sum(e0)/len(e0):.2f}°; KV={KV:.3f}")
print("warm patch: measured vs applied correction (old hue-only -> new)")
for p in WARM:
    hA,sA,_=pphsv(P[p[0]][1]); old=fit(p[1],WARM)[0]*0.5*(1+math.cos(math.pi*min(abs(((p[1]-25)+180)%360-180),60)/60))*min(1,sA/0.3)
    print(f"  {p[0]:13s} meas {p[2]:+.1f}  old {old:+.1f}  new {corr(p[1],sA)[0]:+.1f}")
HD,SD,VD=90,16,16
for style in ["Standard","Positive Film","Negative Film","Vivid","Monotone","Soft Monotone","Hard Monotone"]:
    t=read(f"../ported/Sony ILCE-6300 GR III {style}.dcp"); d0=list(tag(t,50982)); PT=Table((HD,SD,VD),d0,1); d=list(d0)
    for vi in range(VD):
        v=dec(vi/(VD-1)) if vi else 1e-4
        for hi in range(HD):
            for si in range(1,SD):
                X=hsv2rgb(hi*6/HD,si/(SD-1),v); h0,s0,v0=rgb2hsv(*X)
                dh,kv=corr(h0*60,s0)
                X2=hsv2rgb((h0+dh*6/360)%6,s0,dec(enc(v0)*kv))
                T=PT.apply(X2); hT,sT,vT=rgb2hsv(*T); o=3*(vi*HD*SD+hi*SD+si)
                d[o]=((hT-h0+3)%6-3)*60 if sT>1e-4 else 0.0; d[o+1]=min(sT,1)/s0; d[o+2]=enc(vT)/enc(v0) if v0>1e-7 else 1
    nt={k:(v[0],v[1],v[3]) for k,v in t.items()}
    nm=f"GR III {style}".encode()+b'\0'; nt[50936]=(2,len(nm),nm); nt[50982]=(11,len(d),struct.pack('<%df'%len(d),*d))
    write(f"../ported/Sony ILCE-6300 GR III {style} Matched.dcp",nt) if False else write(f"../final/Sony ILCE-6300 GR III {style}.dcp",nt)
    # check: A6300 chart patches through Matched vs GR chart patches through original port (both in GR-equivalent terms)
    M=Table((HD,SD,VD),d,1); errs=[];errs0=[]
    for n,(g,s) in P.items():
        Xa=mv(S2PP,[dec(x/255) for x in s]); Xg=mv(S2PP,[dec(x/255) for x in g])
        if rgb2hsv(*Xg)[1]<0.08: continue
        a=rgb2hsv(*M.apply(Xa)); b=rgb2hsv(*PT.apply(Xg)); c=rgb2hsv(*PT.apply(Xa))
        if b[1]<0.05: continue
        errs.append(abs(((a[0]-b[0]+3)%6-3)*60)); errs0.append(abs(((c[0]-b[0]+3)%6-3)*60))
    print(f"{style:14s} chart hue err vs GR-on-GR: Matched {sum(errs)/max(len(errs),1):.2f}° (old port {sum(errs0)/max(len(errs0),1):.2f}°)")
