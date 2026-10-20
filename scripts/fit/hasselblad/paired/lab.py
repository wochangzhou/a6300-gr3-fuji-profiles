import numpy as np
A2X=np.array([[0.6097559,0.2052401,0.1492240],[0.3111242,0.6256560,0.0632197],[0.0194811,0.0608902,0.7448387]])  # Adobe RGB D50
PP2X=np.array([[0.7977,0.1352,0.0313],[0.2880,0.7119,0.0001],[0.0,0.0,0.8249]]); W50=np.array([0.9642,1,0.8249])
def lab_xyz(t):
    t=np.clip(t,1e-7,None)/W50; f=np.where(t>216/24389,np.cbrt(t),(24389/27*t+16)/116); return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def lab_phocus(v): return lab_xyz(((v/65535)**(563/256))@A2X.T)
def lab_lr(v): return lab_xyz(((v/65535)**1.8)@PP2X.T)
