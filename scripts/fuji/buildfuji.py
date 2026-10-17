import sys,math,struct,json; SD_=sys.argv[1]
exec(open(SD_+'/fit2d.py').read().split('base={3')[0])
B=json.load(open(SD_+'/best.json')); Bh=B['3']; Bv=B['5']
HD,SDv=90,16
out=[]
for hi in range(HD):
    for si in range(SDv):
        s=si/(SDv-1); h=hi*360/HD
        if si==0: out+= [0.0,1.0,1.0]; continue
        fade=min(1,s/0.15)
        dh=pred(h,s,D,Bh[0],Bh[1],Bh[2],3)*fade; kv=math.exp(pred(h,s,D,Bv[0],Bv[1],Bv[2],5)*fade)
        out+=[dh,1.0,kv]
T=Table((HD,SDv,1),out,1)
e0=[];e1=[];v0=[];v1=[]
for n,(f,a) in P.items():
    Xf=mv(S2PP,[dec(x/255) for x in f]); Xa=mv(S2PP,[dec(x/255) for x in a]); hf,sf,vf=rgb2hsv(*Xf)
    if sf<0.08: continue
    ha,_,va=rgb2hsv(*Xa); hc,_,vc=rgb2hsv(*T.apply(Xa))
    e0.append(abs(((ha-hf+3)%6-3)*60)); e1.append(abs(((hc-hf+3)%6-3)*60)); v0.append(abs(enc(va)-enc(vf))); v1.append(abs(enc(vc)-enc(vf)))
print(f"chart (in-sample): hue err {sum(e0)/len(e0):.2f}° -> {sum(e1)/len(e1):.2f}°, value err {sum(v0)/len(v0):.4f} -> {sum(v1)/len(v1):.4f}")
print("max |hue shift| in table:", round(max(abs(out[i]) for i in range(0,len(out),3)),2), " value scale range:", round(min(out[2::3]),3), round(max(out[2::3]),3))
sony=read("Adobe Standard Linear Profile/Sony ILCE-6300 Adobe Standard Linear.dcp")
t={k:(v[0],v[1],v[3]) for k,v in sony.items()}
t[50981]=(4,3,struct.pack('<3I',HD,SDv,1)); t[50982]=(11,len(out),struct.pack('<%df'%len(out),*out)); t[51108]=(4,1,struct.pack('<I',1))
import os; os.makedirs('../final_fuji',exist_ok=True)
write('../final_fuji/Sony ILCE-6300 Adobe Standard Linear.dcp',t)
r=read('../final_fuji/Sony ILCE-6300 Adobe Standard Linear.dcp'); print("written:",r[50936][2],r[50708][2],r[50981][2])
