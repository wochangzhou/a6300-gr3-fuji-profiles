def de2000(l1,l2):
    L1,a1,b1=l1;L2,a2,b2=l2;C1=math.hypot(a1,b1);C2=math.hypot(a2,b2);Cb=(C1+C2)/2
    G=0.5*(1-math.sqrt(Cb**7/(Cb**7+25**7)));a1p=(1+G)*a1;a2p=(1+G)*a2
    C1p=math.hypot(a1p,b1);C2p=math.hypot(a2p,b2);h1=math.degrees(math.atan2(b1,a1p))%360;h2=math.degrees(math.atan2(b2,a2p))%360
    dL=L2-L1;dC=C2p-C1p;dh=h2-h1
    if C1p*C2p==0: dh=0
    elif dh>180: dh-=360
    elif dh<-180: dh+=360
    dH=2*math.sqrt(C1p*C2p)*math.sin(math.radians(dh/2));Lb=(L1+L2)/2;Cbp=(C1p+C2p)/2
    hb=h1+h2
    if C1p*C2p!=0:
        hb=(h1+h2)/2 if abs(h1-h2)<=180 else ((h1+h2+360)/2 if h1+h2<360 else (h1+h2-360)/2)
    T=1-0.17*math.cos(math.radians(hb-30))+0.24*math.cos(math.radians(2*hb))+0.32*math.cos(math.radians(3*hb+6))-0.20*math.cos(math.radians(4*hb-63))
    SL=1+0.015*(Lb-50)**2/math.sqrt(20+(Lb-50)**2);SC=1+0.045*Cbp;SH=1+0.015*Cbp*T
    RT=-2*math.sin(math.radians(60*math.exp(-((hb-275)/25)**2)))*math.sqrt(Cbp**7/(Cbp**7+25**7))
    return math.sqrt((dL/SL)**2+(dC/SC)**2+(dH/SH)**2+RT*(dC/SC)*(dH/SH))
