import os,re,uuid,glob,sys
ROOT=sys.argv[1]; EXP=ROOT+'/export'
GR='A6300 理光模拟'; FJ='A6300 富士模拟'
def alt(tag,val): 
    li=f'<rdf:li xml:lang="x-default">{val}</rdf:li>' if val else '<rdf:li xml:lang="x-default"/>'
    return f'   <crs:{tag}>\n    <rdf:Alt>\n     {li}\n    </rdf:Alt>\n   </crs:{tag}>\n'
HEAD='<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000, 0000/00/00-00:00:00        ">\n <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n  <rdf:Description rdf:about=""\n    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"\n'
TAIL='  </rdf:Description>\n </rdf:RDF>\n</x:xmpmeta>\n'
def attrs(d): return ''.join(f'   crs:{k}="{v}"\n' for k,v in d)
grdirs=[]
for MODEL in ("GR III","GR IV"):
  grdir=f'{EXP}/A6300 {MODEL} Profiles/Settings/A6300 Ricoh {MODEL}'; os.makedirs(grdir,exist_ok=True); grdirs.append(grdir)
  for style in ["Standard","Positive Film","Negative Film","Vivid","Monotone","Soft Monotone","Hard Monotone"]:
      mono='Monotone' in style; name=f'{MODEL} {style}'; pu=uuid.uuid4().hex.upper()
      prof=HEAD+attrs([('PresetType','Look'),('Cluster',''),('UUID',pu),('SupportsAmount','False'),('SupportsColor','False' if mono else 'True'),('SupportsMonochrome','True' if mono else 'False'),
          ('SupportsHighDynamicRange','True'),('SupportsNormalDynamicRange','True'),('SupportsSceneReferred','True'),('SupportsOutputReferred','False'),('RequiresRGBTables','False'),
          ('ShowInPresets','True'),('ShowInQuickActions','False'),('CameraModelRestriction','Sony ILCE-6300'),('Copyright',''),('ContactInfo',''),('Version','18.1.1'),('ProcessVersion','15.4'),
          ('ConvertToGrayscale','True' if mono else 'False'),('CameraProfile',name)]).rstrip('\n')+'\n   crs:HasSettings="True">\n'
      prof+=alt('Name',name)+alt('ShortName','')+alt('SortName','')+alt('Group',GR)+alt('Description','')+TAIL
      open(f'{grdir}/{name}.xmp','w').write(prof)
      pre=HEAD+attrs([('PresetType','Normal'),('Cluster',''),('UUID',uuid.uuid4().hex.upper()),('SupportsAmount2','False'),('SupportsAmount','False'),('SupportsColor','True'),('SupportsMonochrome','True'),
          ('SupportsHighDynamicRange','True'),('SupportsNormalDynamicRange','True'),('SupportsSceneReferred','True'),('SupportsOutputReferred','True'),('RequiresRGBTables','False'),
          ('ShowInPresets','True'),('ShowInQuickActions','False'),('CameraModelRestriction','Sony ILCE-6300'),('Copyright',''),('ContactInfo',''),('Version','18.1.1'),('ProcessVersion','15.4')]).rstrip('\n')+'\n   crs:HasSettings="True">\n'
      pre+=alt('Name',name)+alt('ShortName','')+alt('SortName','')+alt('Group',GR)+alt('Description','')
      pre+=f'   <crs:Look\n    crs:Name="{name}"\n    crs:Amount="1"\n    crs:UUID="{pu}"\n    crs:SupportsAmount="false"\n    crs:SupportsMonochrome="{"true" if mono else "false"}"\n    crs:SupportsOutputReferred="false"\n    crs:Stubbed="true"/>\n'+TAIL
      open(f'{grdir}/{name} preset.xmp','w').write(pre)
# Fuji: set group on profiles (empty) and presets
fdir=f'{EXP}/A6300 Fujifilm Simulation/Settings/Fujifilm Simulation LUT'
pat=re.compile(r'(<crs:Group>\s*<rdf:Alt>\s*)(<rdf:li xml:lang="x-default"/>|<rdf:li xml:lang="x-default">[^<]*</rdf:li>)')
n=0
for f in glob.glob(fdir+'/*.xmp'):
    s=open(f).read(); s2,k=pat.subn(lambda m:m.group(1)+f'<rdf:li xml:lang="x-default">{FJ}</rdf:li>',s); n+=k; open(f,'w').write(s2)
print('fuji files updated:',n)
# Presets that only pick a profile still need explicit linear point curves, otherwise the RGB
# curves of "Hasselblad X1D Nature 5500K" stay on the photo after switching to another preset.
def reset_curves(path):
    s=open(path,encoding='utf-8').read()
    if 'PresetType="Normal"' not in s or 'ToneCurvePV2012Red' in s: return 0
    seq=lambda t:f'   <crs:{t}>\n    <rdf:Seq>\n     <rdf:li>0, 0</rdf:li>\n     <rdf:li>255, 255</rdf:li>\n    </rdf:Seq>\n   </crs:{t}>\n'
    s=s.replace('   crs:HasSettings="True">','   crs:ToneCurveName2012="Linear"\n   crs:HasSettings="True">',1)
    s=s.replace('   <crs:Look\n',''.join(seq(t) for t in ('ToneCurvePV2012','ToneCurvePV2012Red','ToneCurvePV2012Green','ToneCurvePV2012Blue'))+'   <crs:Look\n',1)
    open(path,'w',encoding='utf-8').write(s); return 1
print('curve resets added:',sum(reset_curves(f) for d in (*grdirs,fdir) for f in glob.glob(d+'/*.xmp')))
