# Store the monotone.py result as project data: for each GR colour style, the LookTable saturation entries that
# monotone.py raised (flat index -> new float32 value). build.sh's rawmatch.py applies them, so the build does not need
# numpy and still reproduces the fitted profiles byte for byte.
# Usage: monotone_export.py <dir before monotone> <dir after monotone> <"GR III"|"GR IV"> <out.json>
import sys,struct,json,os
A,B,CAM,OUT=sys.argv[1:5]
def lt(p):
    d=open(p,'rb').read(); n=struct.unpack('<H',d[8:10])[0]
    for i in range(n):
        tag,typ,cnt,off=struct.unpack('<HHII',d[10+12*i:22+12*i])
        if tag==50982: return struct.unpack('<%df'%cnt,d[off:off+4*cnt])
out={}
for style in ["Standard","Positive Film","Negative Film","Vivid","Monotone","Soft Monotone","Hard Monotone"]:
    f=f"Sony ILCE-6300 {CAM} {style}.dcp"; a=lt(os.path.join(A,f)); b=lt(os.path.join(B,f))
    ch={str(i):b[i] for i in range(len(a)) if a[i]!=b[i]}
    assert all(int(i)%3==1 and b[int(i)]>a[int(i)] for i in ch)   # saturation multipliers, only raised
    if ch: out[style]=ch
    print(f"{CAM} {style}: {len(ch)} saturation entries raised")
json.dump(out,open(OUT,'w'),separators=(',',':'))
