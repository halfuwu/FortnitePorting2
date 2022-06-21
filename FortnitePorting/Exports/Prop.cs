using CUE4Parse.UE4.Assets;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Component.StaticMesh;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Assets.Exports.StaticMesh;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.Engine;
using CUE4Parse.Utils;
using Serilog;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Prop
{
    public static ExportFile? Export(string input)
    {
        ExportFile? Export = null;
        var Asset = Provider.LoadObject("FortniteGame/Content/Playsets/PlaysetProps/" + input);
        var Name = Asset.Get<FText>("DisplayName").Text;
        foreach (var (path, file) in Provider.Files)
        {
            var filePath = path.Replace(".uasset", string.Empty);
            if (filePath.SubstringAfterLast("/") != Name.ToLower()) 
                continue;

            var blueprintGeneratedClass = Provider.LoadObject<UBlueprintGeneratedClass>(filePath + "." + filePath.SubstringAfterLast("/") + "_C"); // this is so dumb
            var components = blueprintGeneratedClass.ClassDefaultObject.Load();
            var meshComponent = components.Get<UObject>("StaticMesh");
            Export = Mesh.Export(meshComponent.GetPathName(), Asset.Name, "Prop");
            break;
        }
        
        return Export;
    }
}