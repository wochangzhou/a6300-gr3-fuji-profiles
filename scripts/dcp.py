import struct,sys
TYPES={1:1,2:1,3:2,4:4,5:8,7:1,9:4,10:8,11:4,12:8}
FMT={1:'B',2:'c',3:'H',4:'I',5:'II',7:'B',9:'i',10:'ii',11:'f',12:'d'}
NAMES={50708:'UniqueCameraModel',50721:'ColorMatrix1',50722:'ColorMatrix2',50778:'Illum1',50779:'Illum2',50932:'CalSig',50936:'ProfileName',50937:'HSMDims',50938:'HSMData1',50939:'HSMData2',50940:'ToneCurve',50941:'EmbedPolicy',50942:'Copyright',50964:'FwdMatrix1',50965:'FwdMatrix2',50981:'LookDims',50982:'LookData',51107:'HSMEncoding',51108:'LookEncoding',51109:'BaselineExpOffset',51110:'DefaultBlackRender',50727:'AnalogBalance',50723:'CameraCal1',50724:'CameraCal2'}
def read(p):
    d=open(p,'rb').read(); assert d[:4]==b'IIRC',d[:4]
    off=struct.unpack('<I',d[4:8])[0]; n=struct.unpack('<H',d[off:off+2])[0]; tags={}
    for i in range(n):
        e=d[off+2+12*i:off+14+12*i]; tag,typ,cnt=struct.unpack('<HHI',e[:8])
        size=TYPES[typ]*cnt; vo=e[8:12] if size<=4 else d[struct.unpack('<I',e[8:12])[0]:][:size]
        raw=bytes(vo[:size])
        if typ==2: v=raw.rstrip(b'\0').decode('latin1')
        else:
            f=FMT[typ]; v=list(struct.unpack('<'+f*cnt,raw))
            if typ in (5,10): v=[v[i]/v[i+1] for i in range(0,len(v),2)]
        tags[tag]=(typ,cnt,v,raw)
    return tags
if __name__=='__main__':
    for p in sys.argv[1:]:
        print('==',p.split('/')[-1]); t=read(p)
        for k,(typ,cnt,v,raw) in sorted(t.items()):
            s=v if isinstance(v,str) or cnt<=10 else f'[{cnt} vals] head={v[:6]}'
            print(f'  {k} {NAMES.get(k,"?")} t{typ} n{cnt}: {s}')
