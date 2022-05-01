using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Objects.Core.i18N;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Backpack
{
    public static ExportFile? Export(string input)
    {
        var path = $"FortniteGame/Content/Athena/Items/Cosmetics/Characters/{input}.{input}";
        if (!input.StartsWith("BID_")) 
            path = Benbot.GetCosmeticPath(input, "AthenaBackpack");


        if (Provider.TryLoadObject(path, out var backpack))
        {
            var export = new ExportFile();
            export.name = backpack.Get<FText>("DisplayName").Text;
            
            var parts = backpack.Get<UObject[]>("CharacterParts");
            export.baseStyle = new List<ExportPart>();
            AssetHelpers.ExportCharacterParts(parts, export.baseStyle);

            var styles = backpack.GetOrDefault("ItemVariants", Array.Empty<UObject>());
            AssetHelpers.ExportStyles(styles, ref export);

            return export;
        }

        return null;
    }
}