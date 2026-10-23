# Usage: cm_pairs.py <dir with lab.py> <Lightroom Adobe Standard.tif> <Lightroom Camera Matching.tif> <out.npy>
# Lightroom Adobe Standard vs Lightroom Camera Matching (Hasselblad X2D "Camera Standard") export of the same X2D RAW
# (same app, same settings: pixel-aligned), flat 6x6 cells at /4. Rows: x, y, Adobe Standard rgb, Camera Matching rgb
# (both Lightroom ProPhoto gamma 1.8 encoding).
import sys,os
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'nature_pairs.py')).read()
LAB=None
exec(src.replace("from lab import *","from lab import *\nLAB=lab_lr",1))
