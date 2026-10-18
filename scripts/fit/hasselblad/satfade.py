import sys,struct;sys.path.insert(0,sys.argv[1]);from dcp import read
S0,S1=0.74,0.92
for src,dst in zip(sys.argv[2::2],sys.argv[3::2]):
    t=read(src); tags={k:(v[0],v[1],v[3]) for k,v in t.items()}; H,Sd,Vd=t[50981][2]; d=list(t[50982][2])
    for vi in range(Vd):
        for hi in range(H):
            for si in range(Sd):
                s=si/(Sd-1); w=min(1,max(0,(s-S0)/(S1-S0)))
                if w==0: continue
                o=3*(vi*H*Sd+hi*Sd+si); d[o]=d[o]*(1-w); d[o+1]=d[o+1]*(1-w)+w
    tags[50982]=(11,len(d),struct.pack('<%df'%len(d),*d))
    ents=sorted(tags.items()); n=len(ents); off=8+2+12*n+4; ifd=b''; data=b''
    for k,(typ,cnt,raw) in ents:
        if len(raw)<=4: ifd+=struct.pack('<HHI',k,typ,cnt)+raw.ljust(4,b'\0')
        else:
            if (off+len(data))%2: data+=b'\0'
            ifd+=struct.pack('<HHII',k,typ,cnt,off+len(data)); data+=raw
    open(dst,'wb').write(b'IIRC'+struct.pack('<I',8)+struct.pack('<H',n)+ifd+b'\0\0\0\0'+data); print("wrote",dst.split('/')[-1])
