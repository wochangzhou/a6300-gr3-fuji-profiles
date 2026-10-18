# Save the parts of a fitted DCP that this project computed itself (LookTable, tone curve,
# exposure offset, names) to data/, so build.sh can rebuild the profile from the user's own
# Adobe / upstream profiles without redistributing their matrices and HueSatMaps.
# Usage: python3 export_tables.py <fitted.dcp> <reference.dcp> <id> <data_dir>
import sys,json,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from dcp import read
SRC,REF,ID,DATA=sys.argv[1:5]
t=read(SRC); r=read(REF); own={}
for k,(typ,cnt,val,raw) in sorted(t.items()):
    if k in r and r[k][3]==raw: continue
    if len(raw)>64:
        fn=f"tables/{ID}_{k}.bin"; open(os.path.join(DATA,fn),'wb').write(raw); own[str(k)]=[typ,cnt,{"file":fn}]
    else: own[str(k)]=[typ,cnt,raw.hex()]
P=os.path.join(DATA,'profiles.json'); J=json.load(open(P)) if os.path.exists(P) else {}
J.setdefault(ID,{})["own"]=own; json.dump(J,open(P,'w'),indent=1,sort_keys=True); print(ID,"own tags:",sorted(own))
