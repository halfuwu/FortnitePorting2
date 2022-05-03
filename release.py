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

os.system(f'dotnet publish -c Release -r win-x64 -o "{publishPath}" --self-contained -p:PublishSingleFile=true -p:IncludeAllContentForSelfExtract=true -p:DebugType=None -p:DebugSymbols=false')

with zipfile.ZipFile('Release/FortnitePortingAddon.zip', 'w') as addonZip:
    addonZip.write('FortnitePortingAddon.py', 'FortnitePorting/FortnitePortingAddon.py')

with zipfile.ZipFile('Release/FortnitePorting.zip', 'w') as mainZip:
    for file in glob.glob(publishPath + "**"):
        mainZip.write(file, os.path.basename(file))
    mainZip.write('FPShader.blend')
    mainZip.write('config.json')
    mainZip.write('Release/FortnitePortingAddon.zip', 'FortnitePortingAddon.zip')

os.remove('Release/FortnitePortingAddon.zip')


