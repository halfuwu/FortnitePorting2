using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Objects.Core.i18N;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Pickaxe
{
    public static ExportFile? Export(string input)
    {
        var path = $"FortniteGame/Content/Athena/Items/Cosmetics/Pickaxes/{input}.{input}";
        if (!input.StartsWith("Pickaxe_ID_")) 
            path = Benbot.GetCosmeticPath(input, "AthenaPickaxe");


        if (Provider.TryLoadObject(path, out var pickaxe))
        {
            var export = new ExportFile();
            export.name = pickaxe.Get<FText>("DisplayName").Text;
            export.baseStyle = new List<ExportPart>();
            
            var mainPart = new ExportPart();
            export.baseStyle.Add(mainPart);

            var weapon = pickaxe.Get<UObject>("WeaponDefinition");
            var mesh = weapon.Get<USkeletalMesh>("WeaponMeshOverride");
            Mesh.ExportSkeletalMesh(mesh, ref mainPart);

            if (weapon.TryGetValue<USkeletalMesh>(out var offHandMesh, "WeaponMeshOffhandOverride"))
            {
                var offHandPart = new ExportPart();
                export.baseStyle.Add(offHandPart);
                
                Mesh.ExportSkeletalMesh(offHandMesh, ref offHandPart);
            }
            
            // i dont think pickaxes with override materials exist so im just gonna assume i dont have to add them

            var styles = pickaxe.GetOrDefault("ItemVariants", Array.Empty<UObject>());
            AssetHelpers.ExportStyles(styles, ref export);

            return export;
        }

        return null;
    }
}