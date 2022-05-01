using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Objects.Core.i18N;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Glider
{
    public static ExportFile? Export(string input)
    {
        var path = $"FortniteGame/Content/Athena/Items/Cosmetics/Gliders/{input}.{input}";
        if (!input.StartsWith("Glider_ID")) 
            path = Benbot.GetCosmeticPath(input, "AthenaGlider");


        if (Provider.TryLoadObject(path, out var glider))
        {
            var export = new ExportFile();
            export.name = glider.Get<FText>("DisplayName").Text;
            export.baseStyle = new List<ExportPart>();
            
            var exportPart = new ExportPart();
            export.baseStyle.Add(exportPart);

            var mesh = glider.Get<USkeletalMesh>("SkeletalMesh");
            Mesh.ExportSkeletalMesh(mesh, ref exportPart);
            
            if (glider.TryGetValue<FStructFallback[]>(out var materialOverrides, "MaterialOverrides"))
            {
                AssetHelpers.ExportOverrideMaterials(materialOverrides, ref exportPart);
            }
            
            var styles = glider.GetOrDefault("ItemVariants", Array.Empty<UObject>());
            AssetHelpers.ExportStyles(styles, ref export);
            
            return export;
        }

        return null;
    }
}