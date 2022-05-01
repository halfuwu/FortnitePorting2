using CUE4Parse.UE4.Assets.Exports.Material;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Assets.Exports.StaticMesh;
using CUE4Parse_Conversion.Meshes;
using CUE4Parse_Conversion.Meshes.PSK;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public class Mesh
{
    public static ExportFile? Export(string input)
    {
        var path = input.Replace(".uasset", "");
        
        if (Provider.TryLoadObject(path, out var mesh))
        {
            var export = new ExportFile();
            export.name = mesh.Name;
            export.baseStyle = new List<ExportPart>();

            var exportPart = new ExportPart();
            export.baseStyle.Add(exportPart);

            exportPart.meshPath = mesh.GetPathName();
            exportPart.slotType = "Mesh";

            switch (mesh.ExportType)
            {
                case "StaticMesh":
                {
                    var staticMesh = (UStaticMesh) mesh;
                    AssetHelpers.ExportObject(mesh);
                    staticMesh.TryConvert(out var convertedMesh);
                    if (convertedMesh.LODs.Count == 0) return null;
                    ExportMesh(convertedMesh.LODs[0].Sections, ref exportPart);
                    break;
                }
                case "SkeletalMesh":
                {
                    var skeletalMesh = (USkeletalMesh) mesh;
                    AssetHelpers.ExportObject(mesh);
                    skeletalMesh.TryConvert(out var convertedMesh);
                    if (convertedMesh.LODs.Count == 0) return null;
                    ExportMesh(convertedMesh.LODs[0].Sections, ref exportPart);
                    break;
                }
            }

            return export;
        }

        return null;
    }

    public static void ExportMesh(Lazy<CMeshSection[]> sections, ref ExportPart part)
    {
        part.materials = new List<ExportMaterial>();
        foreach (var (section, matIdx) in sections.Value.Enumerate())
        {
            if (section.Material == null) continue;
            if (section.Material.TryLoad(out var sectionMaterial))
            {
                if (sectionMaterial is UMaterialInstanceConstant materialInstance)
                {
                    var material = new ExportMaterial
                    {
                        matPath = materialInstance.GetPathName(),
                        matIdx = matIdx,
                        matParameters = AssetHelpers.ExportMaterialParams(materialInstance)
                    };
                    part.materials.Add(material);
                }
                else
                {
                    var material = new ExportMaterial
                    {
                        matPath = sectionMaterial.GetPathName(),
                        matIdx = matIdx,
                        matParameters = new ExportMaterialParameters()
                    };
                    part.materials.Add(material);
                }
            }
        }
    }
}