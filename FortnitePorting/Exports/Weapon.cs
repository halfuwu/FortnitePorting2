using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.Utils;
using CUE4Parse_Fortnite.Enums;
using Serilog;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Weapon
{
    public static ExportFile? Export(string input)
    {
        var weapons = new List<UObject>();
        var weaponName = string.Empty;
        foreach (var (key, _) in Provider.Files)
        {
            if (!key.StartsWith("fortnitegame/content/athena/items/weapons/")) continue;
            if (!key.SubstringAfterLast("/").StartsWith("wid_")) continue;
            
            var asset = Provider.LoadObject(key.Replace(".uasset", ""));
            if (asset.TryGetValue<FText>(out var name, "DisplayName"))
            {
                if (name.Text.ToLower().Trim().Equals(input.ToLower()))
                {
                    weaponName = name.Text.Trim();
                    weapons.Add(asset);
                }
            }
        }
        weapons = weapons.OrderBy(x => x.GetOrDefault("Rarity", EFortRarity.Uncommon)).ToList();

        if (weapons.Count > 0)
        {
            var export = new ExportFile();
            export.type = "Weapon";
            export.name = weaponName;
            export.baseStyle = new List<ExportPart>();
            
            var part = new ExportPart();
            export.baseStyle.Add(part);
            
            var weapon = PromptWeapon(weapons, weaponName);
            var hasOverride = weapon.TryGetValue<USkeletalMesh>(out var mesh, "WeaponMeshOverride");
            if (!hasOverride)
                weapon.TryGetValue<USkeletalMesh>(out mesh, "PickupSkeletalMesh");
            Mesh.ExportSkeletalMesh(mesh, ref part);
            
            return export;
        }

        return null;
    }

    private static UObject PromptWeapon(IReadOnlyList<UObject> weapons, string weaponName)
    {
        Log.Information("{0} Rarities:", weaponName);
        for (var i = 0; i < weapons.Count; i++)
            Log.Information("{0}. {1} {2}", i+1, 
                weapons[i].GetOrDefault("Rarity", EFortRarity.Uncommon).GetNameText().Text, weaponName);
        int selectedWeaponIdx;
        while (true)
        {
            try
            {
                Log.Information("Enter Number of Rarity:");
                selectedWeaponIdx = int.Parse(Console.ReadLine() ?? string.Empty)-1;

                if (selectedWeaponIdx > weapons.Count-1 || selectedWeaponIdx < 0)
                    Log.Information("Number of Rarity does not exist");
                else
                    break;
            }
            catch (FormatException)
            {
                Log.Information("Rarity can only be selected by its number");
            }
        }

        return weapons[selectedWeaponIdx];
    }
}

