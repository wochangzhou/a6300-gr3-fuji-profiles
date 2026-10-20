import numpy as np,json
NAMES=["brown","skin","bluesky","foliage","blueflower","bluishgreen","orange","purplishblue","modred","purple","yellowgreen","orangeyellow","blue","green","red","yellow","magenta","cyan","white","n8","n6.5","n5","n3.5","black"]
# tag: crop origin in linear px, grid corners (first/last patch centre) in crop px
G={"a6300":((2409,501),(134,127,1064,676)),"gr3":((2357,451),(176,153,1117,706)),"gr4":((2515,492),(130,150,1090,710))}
out={}
for tag,((ox,oy),(x0,y0,x1,y1)) in G.items():
    d=np.load(f"{tag}_lin.npy",mmap_mode='r'); res={}
    for j in range(4):
        for i in range(6):
            cx=int(ox+x0+(x1-x0)*i/5); cy=int(oy+y0+(y1-y0)*j/3); hw=30
            b=np.asarray(d[cy-hw:cy+hw,cx-hw:cx+hw]).reshape(-1,3).astype(np.float64)
            m=b.mean(0); sd=(b.std(0)/np.maximum(m,1)).max()
            res[NAMES[j*6+i]]=[float(x) for x in m]
            if sd>0.05: print(f"  WARN {tag} {NAMES[j*6+i]} rel sd {sd:.3f}")
    out[tag]=res
    w=res["white"]; print(tag,"white",[round(x) for x in w],"(max 65535)","| black",[round(x) for x in res["black"]], "| n5/white", [round(res['n5'][k]/w[k],3) for k in range(3)])
json.dump(out,open("patches_raw.json","w"),indent=0)
