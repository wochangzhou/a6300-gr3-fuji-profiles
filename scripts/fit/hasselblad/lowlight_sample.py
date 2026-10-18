import sys,json,math,numpy as np
O,R,GS,LRP=sys.argv[1:5]
sys.argv=[sys.argv[0],GS,LRP,'.','/dev/null']; sys.path.insert(0,GS)
src=open(GS+'/rawbase.py').read(); S=GS; exec(src[src.index('from dcp import read'):src.index('P=json.load(open(PATCHES))')])
Ad=np.load(O+'/Ad.npy'); Xw=np.load(O+'/Xw.npy'); inside=np.load(O+'/inside.npy')
P=json.load(open(R+'/patches_raw.json'))['a6300']
t=read(f"{LRP}/Adobe Standard/Sony ILCE-6300 Adobe Standard.dcp")
neutral=[P['n8'][k]+P['n6.5'][k]+P['n5'][k] for k in range(3)]; s=neutral[1]; neutral=[x/s for x in neutral]
f,T,w=base_fn(t)(neutral); sc=0.9/(P['white'][1]/neutral[1])
print("CCT",round(T),"sc",sc)
A2X=np.array([[0.5767309,0.1855540,0.1881852],[0.2973769,0.6273491,0.0752741],[0.0270343,0.0706872,0.9911085]])
BR=np.array([[1.0478112,0.0228866,-0.0501270],[0.0295424,0.9904844,-0.0170491],[-0.0092345,0.0150436,0.7521316]])
PP2X=np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]); MX=np.linalg.inv(PP2X)@BR@A2X
Xlin=((Xw/65535.0)**(563/256))@MX.T          # PP linear per work pixel
Acam=Ad*65535.0                              # camera linear in raw units (same as patches_raw)
h,w_,_=Ad.shape; C=6; rows=[]
# regions (work px = A full/2): wheels excluded from training
def wheel_mask(cx,cy,r): return lambda x,y:(x-cx)**2+(y-cy)**2<r*r
wheels=[wheel_mask((3724+207*553/400)/2,(461+195*553/400)/2,170/2*553/400*2), wheel_mask(1998/2,3276/2,240)]
for y in range(0,h-C,C):
    for x in range(0,w_-C,C):
        if not inside[y:y+C,x:x+C].all(): continue
        a=Acam[y:y+C,x:x+C].reshape(-1,3); b=Xlin[y:y+C,x:x+C].reshape(-1,3)
        la=a@[0.3,0.6,0.1]; lb=b@[0.288,0.712,0]
        if la.mean()<=0 or lb.mean()<=0: continue
        ra=la.std()/la.mean(); rb=lb.std()/lb.mean()
        ca=(a.std(0)/np.maximum(a.mean(0),1)).max(); cbb=(b.std(0)/np.maximum(b.mean(0),1e-6)).max()
        if max(ra,rb)>0.08 or max(ca,cbb)>0.12: continue
        if a.max()>60000 or (Xw[y:y+C,x:x+C]>64000).any(): continue
        cx,cy=x+C/2,y+C/2; isw=any(m(cx,cy) for m in wheels)
        rows.append((cx,cy,int(isw),*a.mean(0),*b.mean(0)))
rows=np.array(rows); print("flat cells",len(rows),"in wheels",int(rows[:,2].sum()))
base=np.array([f([v*sc for v in r[3:6]]) for r in rows])
np.savez(O+'/samples_low.npz',xy=rows[:,:2],wheel=rows[:,2],base=base,tgt=rows[:,6:9],cam=rows[:,3:6])
print("base max",base.max(0).round(3),"tgt Y range",np.percentile(rows[:,6:9]@[0.288,0.712,0],[1,50,99]).round(4))
