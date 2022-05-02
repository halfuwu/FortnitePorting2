using CUE4Parse.UE4.Assets.Exports.Animation;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.UObject;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Emote
{
    public static ExportFile? Export(string input)
    {
        var path = $"FortniteGame/Content/Athena/Items/Cosmetics/Dances/{input}.{input}";
        if (!input.StartsWith("EID_")) 
            path = Benbot.GetCosmeticPath(input, "AthenaDance");


        if (Provider.TryLoadObject(path, out var dance))
        {
            var export = new ExportFile();
            export.type = "Emote";
            export.name = dance.Get<FText>("DisplayName").Text;

            var animPart = new ExportAnim();
            export.animPart = animPart;

            var montage = dance.Get<UAnimMontage>("Animation");
            var sections = montage.Get<FStructFallback[]>("CompositeSections");

            // TODO construct chain of psas for full section sequences maybe ???
            var section = sections.FirstOrDefault(x => x.Get<FName>("SectionName").Text.Equals("Loop"));
            section ??= sections.First(x => x.Get<FName>("SectionName").Text.Equals("Default"));

            var anim = section.Get<UAnimSequence>("LinkedSequence");
            AssetHelpers.ExportObject(anim);
            animPart.animPath = anim.GetPathName();
            
            return export;
        }

        return null;
    }
}