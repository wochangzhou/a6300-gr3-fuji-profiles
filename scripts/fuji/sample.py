import sys,struct,colorsys,json
def load(p):
    d=open(p,'rb').read(); off=struct.unpack('<I',d[10:14])[0]; w,h=struct.unpack('<ii',d[18:26]); bpp=struct.unpack('<H',d[28:30])[0]//8
    row=(w*bpp+3)//4*4; fl=h>0; h=abs(h)
    def px(x,y):
        yy=h-1-y if fl else y; o=off+yy*row+x*bpp; b,g,r=d[o:o+3]; return r,g,b
    return px
B={
9:[("brown",(40,0,360,330),(1010,0,1335,320)),("skin",(410,0,745,330),(1385,0,1705,320)),("orange",(40,385,360,640),(1010,370,1335,640)),("purplishblue",(410,385,745,640),(1385,370,1705,640))],
10:[("bluesky",(50,15,385,345),(1035,20,1358,335)),("foliage",(435,15,770,345),(1408,20,1730,335)),("modred",(50,400,385,655),(1035,385,1358,655)),("purple",(435,400,770,655),(1408,385,1730,655))],
11:[("blueflower",(180,5,518,330),(1160,5,1485,325)),("bluishgreen",(565,5,903,330),(1533,5,1860,325)),("yellowgreen",(180,385,518,645),(1160,375,1485,645)),("orangeyellow",(565,385,903,645),(1533,375,1860,645))],
12:[("blue",(40,0,375,320),(1025,0,1348,312)),("green",(425,0,760,320),(1397,0,1720,312)),("white",(40,375,375,635),(1025,362,1348,635)),("n8",(425,375,760,635),(1397,362,1720,635))],
13:[("red",(40,5,370,335),(1020,10,1345,325)),("yellow",(420,5,755,335),(1393,10,1717,325)),("n6.5",(40,390,370,645),(1020,378,1345,645)),("n5",(420,390,755,645),(1393,378,1717,645))],
14:[("magenta",(182,0,516,308),(1162,0,1486,303)),("cyan",(567,0,903,308),(1536,0,1860,303)),("n3.5",(182,362,516,635),(1162,354,1486,635)),("black",(567,362,903,635),(1536,354,1860,635))],
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
        print(f"{n:13s} XS20 {[round(x) for x in g]} sd{gs:4.1f} | A6300 {[round(x) for x in s]} sd{ss:4.1f} | hueXS20 {hg[0]*360:5.1f} dHue(A-F) {dh:+5.1f}  satRatio {hs[1]/max(hg[1],1e-3):.2f}  V {hs[2]/hg[2]:.2f}")
json.dump(out,open(sys.argv[1]+"/patches.json","w"))
