import os
import glob
import zipfile

publishPath = './FortnitePorting/bin/Publish/'

try:
    os.mkdir('Release')
except FileExistsError:
    pass

for file in glob.glob(publishPath + "**"):
    os.remove(file)

#os.system(f'dotnet publish -c Release -r win-x64 -o "{publishPath}" -p:PublishSingleFile=true -p:IncludeAllContentForSelfExtract=true -p:DebugType=None -p:DebugSymbols=false --self-contained true')
os.system(f'dotnet publish -r win-x64 -o "{publishPath}" /p:PublishSingleFile=true /p:IncludeNativeLibrariesForSelfExtract=true /p:DebugType=None /p:DebugSymbols=false --self-contained true')

with zipfile.ZipFile('Release/FortnitePorting.zip', 'w', zipfile.ZIP_DEFLATED) as mainZip:
    for file in glob.glob(publishPath + "**"):
        if not file.endswith('.pdb'):
            mainZip.write(file, os.path.basename(file))
    mainZip.write('FPData.blend')
    mainZip.write('config.json')
    mainZip.write('FortnitePortingAddon.py')


