import sys,json,math,struct,os
S,G,LRP,DSTDIR,BEO=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],float(sys.argv[5])
sys.argv=[sys.argv[0],G,LRP,'.','/dev/null']
exec(open(G+'/port.py').read().split('HD,SD,VD=90,16,16')[0])
M=json.load(open(S+'/hbmodel.json')); TR=M['train']; PR={int(k):v for k,v in M['params'].items()}
def pred(h,s,k):
    sh,ss,lam=PR[k]; num=0;wt=lam
    for p in TR:
        d=((h-p[1])+180)%360-180; w=math.exp(-0.5*(d/sh)**2)*math.exp(-0.5*((s-p[2])/ss)**2); num+=w*p[k]; wt+=w
    return num/wt
HD,SD,VD=90,16,16; row=[]
for hi in range(HD):
    for si in range(SD):
        s=si/(SD-1); h=hi*360/HD
        if si==0: row+=[0.0,1.0,1.0]; continue
        fade=min(1,s/0.12); row+=[pred(h,s,3)*fade, math.exp(pred(h,s,4)*fade), math.exp(pred(h,s,5)*fade)]
look=row*VD
src=read(LRP+"/Adobe Standard/Sony ILCE-6300 Adobe Standard.dcp")
t={k:(v[0],v[1],v[3]) for k,v in src.items() if k in (50708,50721,50722,50778,50779,50932,50937,50938,50939,50941,50964,50965)}
nm=b"Hasselblad X1D Standard\0"; t[50936]=(2,len(nm),nm)
cp=b"Fitted to Hasselblad Phocus output (dpreview studio scene)\0"; t[50942]=(2,len(cp),cp)
t[50940]=(11,len(M['curve']),struct.pack('<%df'%len(M['curve']),*M['curve']))
t[50981]=(4,3,struct.pack('<3I',HD,SD,VD)); t[50982]=(11,len(look),struct.pack('<%df'%len(look),*look)); t[51108]=(4,1,struct.pack('<I',1))
t[51109]=(10,1,struct.pack('<ii',int(round(BEO*10000)),10000)); t[51110]=(4,1,struct.pack('<I',1))
os.makedirs(DSTDIR,exist_ok=True); p=f"{DSTDIR}/Sony ILCE-6300 Hasselblad X1D Standard.dcp"; write(p,t)
r=read(p); print("written",r[50936][2],"look",r[50981][2],"curve pts",r[50940][1]//2,"BEO",r[51109][2])
