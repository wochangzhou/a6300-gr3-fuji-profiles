import sys,json,math; LRP=sys.argv[2]; sys.argv=[sys.argv[0],sys.argv[1],LRP,'.','/dev/null']
exec(open(sys.argv[1]+'/port.py').read().split('HD,SD,VD=90,16,16')[0])
SRGB2XYZ=[[0.4360,0.3851,0.1431],[0.2225,0.7169,0.0606],[0.0139,0.0971,0.7141]]; S2PP=mm(XYZ2PP,SRGB2XYZ)
P=json.load(open(sys.argv[1]+"/patches.json"))
def pphsv(rgb): return rgb2hsv(*mv(S2PP,[dec(x/255) for x in rgb]))
PTS=[]
for n,(g,s) in P.items():
    hg,sg,vg=pphsv(g); ha,sa,va=pphsv(s)
    if sg<0.08: continue
    w=0.3 if n in ("blue","cyan") else 1.0
    PTS.append((n,ha*60,((hg-ha+3)%6-3)*60,sg/sa,enc(vg)/enc(va),w*min(1,sa/0.3)))
SIG=25.0
def fit(h,pts):
    ws=[];acc=[0,0,0]
    for n,hp,dh,ks,kv,w in pts:
        d=((h-hp)+180)%360-180; k=w*math.exp(-0.5*(d/SIG)**2); ws.append(k)
        acc=[acc[0]+k*dh,acc[1]+k*math.log(ks),acc[2]+k*math.log(kv)]
    W=sum(ws)+0.05   # shrink to identity where no data
    return acc[0]/W, math.exp(acc[1]/W), math.exp(acc[2]/W)
if __name__=="__main__":
    print(f"{'patch':13s} PPhue  meas(dh,ks,kv)        in-fit              leave-one-out")
    E=[];E2=[]
    for i,(n,hp,dh,ks,kv,w) in enumerate(PTS):
        f=fit(hp,PTS); l=fit(hp,PTS[:i]+PTS[i+1:])
        E.append(abs(f[0]-dh)); E2.append(abs(l[0]-dh))
        print(f"{n:13s} {hp:5.1f}  {dh:+5.1f} {ks:.2f} {kv:.2f}   {f[0]:+5.1f} {f[1]:.2f} {f[2]:.2f}   {l[0]:+5.1f} {l[1]:.2f} {l[2]:.2f}")
    print(f"hue err mean: in-fit {sum(E)/len(E):.2f}°, leave-one-out {sum(E2)/len(E2):.2f}° (uncorrected mean |dh| {sum(abs(p[2]) for p in PTS)/len(PTS):.2f}°)")
