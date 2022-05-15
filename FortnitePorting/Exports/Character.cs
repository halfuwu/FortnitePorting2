using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.Utils;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Character
{
    public static ExportFile? ExportBR(string input)
    {
        var path = $"FortniteGame/Content/Athena/Items/Cosmetics/Characters/{input}.{input}";
        if (!input.StartsWith("CID_")) 
            path = Benbot.GetCosmeticPath(input, "AthenaCharacter");


        if (Provider.TryLoadObject(path, out var character))
        {
            var export = new ExportFile();
            export.type = "Character";
            export.name = character.Get<FText>("DisplayName").Text;
            if (export.name.Equals("TBD"))
                export.name = character.Name;
            
            var parts = character.Get<UObject[]>("BaseCharacterParts");
            export.baseStyle = new List<ExportPart>();
            AssetHelpers.ExportCharacterParts(parts, export.baseStyle);

            var styles = character.GetOrDefault("ItemVariants", Array.Empty<UObject>());
            AssetHelpers.ExportStyles(styles, ref export);

            return export;
        }

        return null;
    }
    public static ExportFile? ExportSTW(string input)
    {
        UObject? character = null;
        foreach (var (key, _) in Provider.Files)
        {
            if (!key.StartsWith("fortnitegame/plugins/gamefeatures/savetheworld/content/heroes/")) continue;
            if (!key.SubstringAfterLast("/").StartsWith("cid_")) continue;
            
            var asset = Provider.LoadObject(key.Replace(".uasset", ""));
            if (asset.Get<FText>("DisplayName").Text.ToLower().Equals(input.ToLower()))
            {
                character = asset;
                break;
            }
        }

        if (character != null)
        {
            var export = new ExportFile();
            export.type = "Character";
            export.name = character.Get<FText>("DisplayName").Text;
            
            var styles = character.GetOrDefault("ItemVariants", Array.Empty<UObject>());
            AssetHelpers.ExportStyles(styles, ref export);

            return export;
        }

        return null;
    }
}