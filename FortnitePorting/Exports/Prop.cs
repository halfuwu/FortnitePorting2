using CUE4Parse.FN.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.StaticMesh;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.Engine;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Prop
{
    public static ExportFile? Export(string input)
    {
        var Asset = Provider.LoadObject("FortniteGame/Content/Playsets/PlaysetProps/" + input);

        var export = new ExportFile();
        export.type = "Prop";
        export.name = Asset.Get<FText>("DisplayName").Text;
        export.baseStyle = new List<ExportPart>();

        var exportPart = new ExportPart();
        export.baseStyle.Add(exportPart);

        var actorRecord = Asset.GetOrDefault<ULevelSaveRecord>("ActorSaveRecord");
        FActorTemplateRecord? templeteRecords = null;
        foreach (var kv in actorRecord.GetOrDefault<UScriptMap>("TemplateRecords").Properties) {
            var val = kv.Value.GetValue(typeof(FActorTemplateRecord));
            templeteRecords = val is FActorTemplateRecord rec ? rec : null;
            break;
        }
        if (templeteRecords is null) throw new Exception("actor class not found");

        var blueprintGeneratedClass = templeteRecords.ActorClass.Load<UBlueprintGeneratedClass>();
        var components = blueprintGeneratedClass.ClassDefaultObject.Load();
        var meshComponent = components.Get<UStaticMesh>("StaticMesh");

        Mesh.ExportStaticMesh(meshComponent, ref exportPart);

        // var index = 0;
        // foreach (var prop in templeteRecords.ReadActorData(actorRecord.Owner, actorRecord.SaveVersion).Properties)
        // {
        //     if (prop.Name != "TextureData") continue;
        //     var textureDataPkg = (string)prop.Tag.GetValue(typeof(string));
        //     if (Provider.TryLoadObject(textureDataPkg, out var td))
        //     {
        //         if (exportPart.materials.Count > index)
        //         {
        //             var diffuse = td.GetOrDefault<FPackageIndex>("Diffuse").ResolvedObject?.GetPathName();
        //             var normal = td.GetOrDefault<FPackageIndex>("Normal").ResolvedObject?.GetPathName();
        //             var specular = td.GetOrDefault<FPackageIndex>("Specular").ResolvedObject?.GetPathName();
        //
        //             if (diffuse is not null)
        //             {
        //                 var foundIndex = exportPart.materials[index].matParameters.TextureParameters.FindIndex(x => x.Info == "Diffuse");
        //                 if (foundIndex != -1)
        //                     exportPart.materials[index].matParameters.TextureParameters[foundIndex].Value = diffuse;
        //             }
        //
        //             if (normal is not null)
        //             {
        //                 var foundIndex = exportPart.materials[index].matParameters.TextureParameters.FindIndex(x => x.Info == "Normal");
        //                 if (foundIndex != -1)
        //                     exportPart.materials[index].matParameters.TextureParameters[foundIndex].Value = normal;
        //             }
        //
        //             if (specular is not null)
        //             {
        //                 var foundIndex = exportPart.materials[index].matParameters.TextureParameters.FindIndex(x => x.Info == "Specular");
        //                 if (foundIndex != -1)
        //                     exportPart.materials[index].matParameters.TextureParameters[foundIndex].Value = specular;
        //             }
        //
        //
        //             foreach (var texture in exportPart.materials[index].matParameters.TextureParameters)
        //             {
        //
        //             }
        //         }
        //         index++;
        //     }
        // }

        return export;
    }
}