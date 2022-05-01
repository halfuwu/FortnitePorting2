using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Material;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.Engine;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse_Conversion.Meshes;
using Serilog;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Pet
{
    public static ExportFile? Export(string input)
    {
        var path = $"FortniteGame/Content/Athena/Items/Cosmetics/Characters/{input}.{input}";
        if (!input.StartsWith("PetID_")) 
            path = Benbot.GetCosmeticPath(input, "AthenaPet");


        if (Provider.TryLoadObject(path, out var pet))
        {
            var export = new ExportFile();
            export.name = pet.Get<FText>("DisplayName").Text;
            export.baseStyle = new List<ExportPart>();
            
            var exportPart = new ExportPart();
            export.baseStyle.Add(exportPart);
            
            var blueprintClass = pet.Get<UBlueprintGeneratedClass>("PetPrefabClass");
            var components = blueprintClass.ClassDefaultObject.Load();
            var petMeshComponent = components.Get<UObject>("PetMesh");
            
            var mesh = petMeshComponent.Get<USkeletalMesh>("SkeletalMesh");
            AssetHelpers.ExportObject(mesh);
            exportPart.meshPath = mesh.GetPathName();
            
            mesh.TryConvert(out var convertedMesh);
            if (convertedMesh.LODs.Count == 0) return null;
            Mesh.ExportMesh(convertedMesh.LODs[0].Sections, ref exportPart);

            if (pet.TryGetValue<FStructFallback[]>(out var materialOverrides, "MaterialOverrides"))
            {
                foreach (var materialOverride in materialOverrides)
                {
                    var materialPath = materialOverride.Get<FSoftObjectPath>("OverrideMaterial");
                    if (materialPath.TryLoad(out UMaterialInstanceConstant materialInstance))
                    {
                        var material = new ExportMaterial
                        {
                            matPath = materialInstance.GetPathName(),
                            matIdx = materialOverride.Get<int>("MaterialOverrideIndex"),
                            matParameters = AssetHelpers.ExportMaterialParams(materialInstance)
                        };
                        exportPart.materials.Add(material);
                    }
                }
            }
            
           
            return export;
        }

        return null;
    }
}