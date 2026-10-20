# Map linear camera RGB patch means into each camera's Adobe Standard "base colour"
# (white balance -> ForwardMatrix -> XYZ D50 -> ProPhoto -> HueSatMap), following
# the DNG SDK's illuminant interpolation. This is the input space of a LookTable.
import sys,json,math
S=sys.argv[1]; LRP=sys.argv[2]; PATCHES=sys.argv[3]; OUTJ=sys.argv[4]
EXTRA=sys.argv[5:7]   # optional: extra samples json in, base json out (same WB/exposure as the chart)
sys.argv=[sys.argv[0],S,LRP,'.','/dev/null']; sys.path.insert(0,S)
from dcp import read
src=open(S+'/port.py').read(); exec(src[:src.index('grAS=read(')])
ILL_T={17:2856.0,21:6504.0,23:5003.0,20:5503.0,22:7504.0}
def xy_to_cct(x,y):   # McCamy
    n=(x-0.3320)/(0.1858-y); return 449*n**3+3525*n**2+6823.3*n+5520.33
def interp_w(T,T1,T2):
    if T<=T1: return 1.0
    if T>=T2: return 0.0
    return (1/T-1/T2)/(1/T1-1/T2)
def blend(a,b,w): return [w*a[i]+(1-w)*b[i] for i in range(len(a))]
def base_fn(t):
    T1=ILL_T[tag(t,50778)[0]]; T2=ILL_T[tag(t,50779)[0]]
    CM1,CM2=tag(t,50721),tag(t,50722); FM1,FM2=tag(t,50964),tag(t,50965)
    H1,H2=tag(t,50938),tag(t,50939); dims=tag(t,50937)
    def setup(neutral):
        xy=(0.3457,0.3585)
        for _ in range(30):
            w=interp_w(xy_to_cct(*xy),T1,T2); CM=m3(blend(CM1,CM2,w))
            XYZ=mv(inv(CM),neutral); s=sum(XYZ); nxy=(XYZ[0]/s,XYZ[1]/s)
            if abs(nxy[0]-xy[0])+abs(nxy[1]-xy[1])<1e-7: break
            xy=nxy
        T=xy_to_cct(*xy); w=interp_w(T,T1,T2)
        FM=m3(blend(FM1,FM2,w)); HSM=Table(dims,blend(H1,H2,w),0)
        M=mm(XYZ2PP,FM)
        def f(cam): return HSM.apply(mv(M,[cam[k]/neutral[k] for k in range(3)]))
        return f,T,w
    return setup
P=json.load(open(PATCHES))
PROF={"a6300":"Sony ILCE-6300"}
out={}; extra_out={}
EX=json.load(open(EXTRA[0])) if EXTRA else None
for cam,pat in P.items():
    t=read(f"{LRP}/Adobe Standard/{PROF[cam]} Adobe Standard.dcp")
    neutral=[ (pat['n8'][k]+pat['n6.5'][k]+pat['n5'][k]) for k in range(3)]; s=neutral[1]; neutral=[x/s for x in neutral]
    f,T,w=base_fn(t)(neutral)
    # normalise exposure on the camera values (before HueSatMap, which clips V at 1): white patch green -> 0.9
    sc=0.9/(pat['white'][1]/neutral[1])
    out[cam]={n:f([x*sc for x in v]) for n,v in pat.items()}
    if EX: extra_out[cam]={n:f([x*sc for x in v]) for n,v in EX[cam].items()}
    print(f"{cam:6s} estimated CCT {T:6.0f}K  (illuminant-1 weight {w:.3f})  white base {[round(x,3) for x in out[cam]['white']]}")
json.dump(out,open(OUTJ,"w"))
if EX: json.dump(extra_out,open(EXTRA[1],"w"))
