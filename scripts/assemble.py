# Rebuild the Hasselblad DCPs: matrices/HueSatMap from the A6300 Adobe Standard profile on this
# machine, plus the tags this project fitted (data/profiles.json + data/tables/).
# Usage: assemble.py <LR_PROFILES> <data_dir> <out_dir>
import sys,os,json,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from dcp import read
LRP,DATA,OUT=sys.argv[1:4]
REFS={"adobe_standard":f"{LRP}/Adobe Standard/Sony ILCE-6300 Adobe Standard.dcp"}
def write(path,tags):   # same layout as port.write
    ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
    for k,(typ,cnt,raw) in ents:
        if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
        else:
            if (off+len(data))%2: data+=b'\0'
            ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
    open(path,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data)
os.makedirs(OUT,exist_ok=True)
for pid,spec in json.load(open(f"{DATA}/profiles.json")).items():
    ref=read(REFS[spec["ref"]]); tags={k:(v[0],v[1],v[3]) for k,v in ref.items()}
    for k,(typ,cnt,val) in spec["own"].items():
        raw=open(f"{DATA}/{val['file']}",'rb').read() if isinstance(val,dict) else bytes.fromhex(val)
        tags[int(k)]=(typ,cnt,raw)
    write(f"{OUT}/{spec['out']}",tags); print("assembled",spec["out"])
