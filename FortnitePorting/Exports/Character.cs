using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.UObject;
using Newtonsoft.Json;
using Serilog;
using static FortnitePorting.Program;

namespace FortnitePorting.Exports;

public static class Character
{
    public static ExportFile? Export(string input)
    {
        var path = $"FortniteGame/Content/Athena/Items/Cosmetics/Characters/{input}.{input}";
        if (!input.StartsWith("CID_")) 
            path = Benbot.GetCosmeticPath(input, "AthenaCharacter");


        if (Provider.TryLoadObject(path, out var character))
        {
            var export = new ExportFile();
            export.name = character.Get<FText>("DisplayName").Text;
            
            var parts = character.Get<UObject[]>("BaseCharacterParts");
            export.baseStyle = new List<ExportPart>();
            AssetHelpers.ExportCharacterParts(parts, export.baseStyle);

            var styles = character.GetOrDefault("ItemVariants", Array.Empty<UObject>());
            AssetHelpers.ExportStyles(styles, ref export);

            return export;
        }

        return null;
    }
}