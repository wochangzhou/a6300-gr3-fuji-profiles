# Chart patches through: GR RAW + Adobe RICOH GR Camera <style> (the original) vs A6300 RAW + each A6300 profile.
# DNG reference steps (base: WB -> FM -> HueSatMap with exposure on chart white; BaselineExposureOffset; LookTable; RGB tone).
# Usage: chart_eval.py <scripts> <LR CameraProfiles> <patches_raw.json> <de2000.py> <"GR III"|"GR IV"> <style> <label=dcp> ...
import sys,json,math
S,LRP,PATCHES,DE,MODEL,STYLE=sys.argv[1:7]; PROFS=[a.split('=',1) for a in sys.argv[7:]]
MODEL0=MODEL
sys.argv=[sys.argv[0],S,LRP,'.','/dev/null']; sys.path.insert(0,S)
from dcp import read
src=open(S+'/port.py').read(); exec(src[:src.index('grAS=read(')])
rb=open(S+'/rawbase.py').read(); exec(rb[rb.index('ILL_T='):rb.index('P=json.load')])
exec(open(DE).read())
def tone(rgb,c):
    cx,cy=c[0::2],c[1::2]
    def f(x):
        x=min(max(x,0),1)
        for i in range(1,len(cx)):
            if x<=cx[i]: return cy[i-1]+(cy[i]-cy[i-1])*(x-cx[i-1])/(cx[i]-cx[i-1])
        return cy[-1]
    o=sorted(range(3),key=lambda k:rgb[k]); lo,mi,hi=[min(max(rgb[k],0),1) for k in o]
    L,H=f(lo),f(hi); M=L+(H-L)*((mi-lo)/(hi-lo) if hi>lo else 0); out=[0]*3; out[o[0]],out[o[1]],out[o[2]]=L,M,H; return out
def lab(p):
    X=[sum(PP2XYZ[r][k]*p[k] for k in range(3)) for r in range(3)]; Wt=[0.9642,1,0.8249]
    f=[(x/w)**(1/3) if x/w>216/24389 else (24389/27*x/w+16)/116 for x,w in zip(X,Wt)]; return [116*f[1]-16,500*(f[0]-f[1]),200*(f[1]-f[2])]
def render(t,pat):
    if 50938 not in t:
        t=dict(t); t[50937]=(4,3,[1,1,1],b''); t[50938]=(11,3,[0.0,1.0,1.0],b''); t[50939]=t[50938]
    n=[(pat['n8'][k]+pat['n6.5'][k]+pat['n5'][k]) for k in range(3)]; s=n[1]; n=[x/s for x in n]
    f,T,w=base_fn(t)(n); sc=0.9/(pat['white'][1]/n[1]); E=2**tag(t,51109)[0] if 51109 in t else 1
    LT=table(t,50981,50982,51108); c=tag(t,50940)
    return {k:lab(tone(LT.apply([E*x for x in f([x*sc for x in v])]),c)) for k,v in pat.items()}
MODEL=MODEL0; P=json.load(open(PATCHES)); cam={'GR IV':'gr4','GR III':'gr3'}[MODEL]
ref=render(read(f"{LRP}/Camera/Ricoh {MODEL}/RICOH {MODEL} Camera {STYLE}.dcp"),P[cam])
cols=["brown","skin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan"]
res={lbl:render(read(p),P['a6300']) for lbl,p in PROFS}
lch=lambda l:(l[0],math.hypot(l[1],l[2]),math.degrees(math.atan2(l[2],l[1]))%360)
print(f"{MODEL} {STYLE}: dE00 per patch (dL / dC / dh vs the GR original)")
print(f"{'patch':13s}"+"".join(f"{lbl:>26s}" for lbl,_ in PROFS))
for n in ["skin","brown","orange","orangeyellow","yellow","red","modred","blue","green","n5"]:
    r=lch(ref[n]); row=f"{n:13s}"
    for lbl,_ in PROFS:
        a=lch(res[lbl][n]); row+=f"   {de2000(res[lbl][n],ref[n]):4.2f} ({a[0]-r[0]:+4.1f}/{a[1]-r[1]:+4.1f}/{((a[2]-r[2]+180)%360)-180:+4.1f})"
    print(row)
for lbl,_ in PROFS:
    e=[de2000(res[lbl][n],ref[n]) for n in cols]; dl=[abs(res[lbl][n][0]-ref[n][0]) for n in cols]
    print(f"  {lbl:10s} 18 colours: mean dE00 {sum(e)/len(e):.2f}  max {max(e):.2f} ({cols[e.index(max(e))]})  | mean |dL| {sum(dl)/len(dl):.2f}")
