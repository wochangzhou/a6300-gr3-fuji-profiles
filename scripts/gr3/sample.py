import sys,struct,colorsys,json
def load(p):
    d=open(p,'rb').read(); off=struct.unpack('<I',d[10:14])[0]; w,h=struct.unpack('<ii',d[18:26]); bpp=struct.unpack('<H',d[28:30])[0]//8
    row=(w*bpp+3)//4*4; fl=h>0; h=abs(h)
    def px(x,y):
        yy=h-1-y if fl else y; o=off+yy*row+x*bpp; b,g,r=d[o:o+3]; return r,g,b
    return px
B={ # img: [(name, leftbox(GR), rightbox(Sony))]
3:[("brown",(60,30,350,310),(1040,40,1340,340)),("skin",(430,30,730,320),(1410,40,1710,340)),("orange",(60,400,350,640),(1040,410,1340,640)),("purplishblue",(430,400,730,640),(1410,410,1710,640))],
4:[("bluesky",(50,30,350,320),(1030,50,1330,340)),("foliage",(420,30,730,320),(1400,50,1700,340)),("modred",(50,390,350,640),(1030,410,1330,640)),("purple",(430,390,730,640),(1400,410,1700,640))],
5:[("blueflower",(215,20,520,300),(1185,25,1490,320)),("bluishgreen",(590,20,900,300),(1560,25,1860,320)),("yellowgreen",(215,375,520,640),(1185,395,1490,640)),("orangeyellow",(590,375,900,640),(1560,395,1860,640))],
6:[("blue",(50,20,340,320),(1030,40,1330,340)),("green",(420,20,720,320),(1400,40,1700,340)),("white",(50,390,340,630),(1030,410,1330,630)),("n8",(420,390,720,630),(1400,410,1700,630))],
7:[("red",(80,30,380,310),(1055,30,1355,330)),("yellow",(450,30,760,310),(1425,30,1730,330)),("n6.5",(80,380,380,650),(1055,400,1355,650)),("n5",(450,380,760,650),(1425,400,1730,650))],
8:[("magenta",(230,30,540,310),(1200,30,1500,330)),("cyan",(605,30,900,310),(1575,30,1870,330)),("n3.5",(230,380,540,650),(1200,400,1500,650))],
}
def avg(px,b):
    x0,y0,x1,y1=b; dx=(x1-x0)*0.15; dy=(y1-y0)*0.15; x0,x1,y0,y1=int(x0+dx),int(x1-dx),int(y0+dy),int(y1-dy)
    P=[px(x,y) for y in range(y0,y1,4) for x in range(x0,x1,4)]; n=len(P)
    m=[sum(p[k] for p in P)/n for k in range(3)]; sd=max((sum((p[k]-m[k])**2 for p in P)/n)**.5 for k in range(3)); return m,sd
out={}
for i,L in B.items():
    px=load(f"{sys.argv[1]}/c{i}.bmp")
    for n,gb,sb in L:
        g,gs=avg(px,gb); s,ss=avg(px,sb); out[n]=(g,s)
        hg=colorsys.rgb_to_hsv(*[x/255 for x in g]); hs=colorsys.rgb_to_hsv(*[x/255 for x in s])
        dh=((hs[0]-hg[0])*360+180)%360-180
        print(f"{n:13s} GR {[round(x) for x in g]} sd{gs:4.1f} | A6300 {[round(x) for x in s]} sd{ss:4.1f} | hueGR {hg[0]*360:5.1f} dHue(A-G) {dh:+5.1f}  satRatio {hs[1]/max(hg[1],1e-3):.2f}  V {hs[2]/hg[2]:.2f}")
json.dump(out,open(sys.argv[1]+"/patches.json","w"))
