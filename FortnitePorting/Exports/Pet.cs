using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.Engine;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Pet
{
    public static ExportFile? Export(string input)
    {
        var path = $"FortniteGame/Content/Athena/Items/Cosmetics/Pets/{input}.{input}";
        if (!input.StartsWith("PetID_")) 
            path = Benbot.GetCosmeticPath(input, "AthenaPet");


        if (Provider.TryLoadObject(path, out var pet))
        {
            var export = new ExportFile();
            export.type = "Pet";
            export.name = pet.Get<FText>("QuantityDisplayName").Text;
            export.baseStyle = new List<ExportPart>();
            
            var exportPart = new ExportPart();
            export.baseStyle.Add(exportPart);
            
            var blueprintClass = pet.Get<UBlueprintGeneratedClass>("PetPrefabClass");
            var components = blueprintClass.ClassDefaultObject.Load();
            var petMeshComponent = components.Get<UObject>("PetMesh");
            
            var mesh = petMeshComponent.Get<USkeletalMesh>("SkeletalMesh");
            Mesh.ExportSkeletalMesh(mesh, ref exportPart);

            if (pet.TryGetValue<FStructFallback[]>(out var materialOverrides, "MaterialOverrides"))
            {
                AssetHelpers.ExportOverrideMaterials(materialOverrides, ref exportPart);
            }
            
           
            return export;
        }

        return null;
    }
}