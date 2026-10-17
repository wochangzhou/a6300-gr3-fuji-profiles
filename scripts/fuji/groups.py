import os,re,uuid,glob,sys
ROOT=sys.argv[1]; EXP=ROOT+'/export'
GR='A6300 理光模拟'; FJ='A6300 富士模拟'
def alt(tag,val): 
    li=f'<rdf:li xml:lang="x-default">{val}</rdf:li>' if val else '<rdf:li xml:lang="x-default"/>'
    return f'   <crs:{tag}>\n    <rdf:Alt>\n     {li}\n    </rdf:Alt>\n   </crs:{tag}>\n'
HEAD='<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000, 0000/00/00-00:00:00        ">\n <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n  <rdf:Description rdf:about=""\n    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"\n'
TAIL='  </rdf:Description>\n </rdf:RDF>\n</x:xmpmeta>\n'
def attrs(d): return ''.join(f'   crs:{k}="{v}"\n' for k,v in d)
grdir=f'{EXP}/A6300 GR III Profiles/Settings/A6300 Ricoh GR III'; os.makedirs(grdir,exist_ok=True)
for style in ["Standard","Positive Film","Negative Film","Vivid","Monotone","Soft Monotone","Hard Monotone"]:
    mono='Monotone' in style; name=f'GR III {style}'; pu=uuid.uuid4().hex.upper()
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
