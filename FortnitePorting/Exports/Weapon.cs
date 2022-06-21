using System.ComponentModel;
using System.Diagnostics;
using System.Reflection;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.Utils;
using CUE4Parse_Fortnite.Enums;
using Newtonsoft.Json;
using Serilog;
using static FortnitePorting.FortnitePorting;

namespace FortnitePorting.Exports;

public static class Weapon
{
    private static string WeaponMappingsPath = Path.Combine(DataDirectory.FullName, "WeaponMappings.json");
    public static ExportFile? Export(string input)
    {
        var weaponMap = new Dictionary<string, string>();
        if (File.Exists(WeaponMappingsPath))
            weaponMap = JsonConvert.DeserializeObject<Dictionary<string, string>>(File.ReadAllText(WeaponMappingsPath));
        else
            Log.Information("Generating first time weapons mapping file at {0}, this takes about 30 seconds", WeaponMappingsPath);

        foreach (var (path, _) in Provider.Files)
        {
            if (weaponMap.Keys.Contains(path)) continue;
            if (!path.SubstringAfterLast("/").StartsWith("wid_")) continue;
            
            var asset = Provider.LoadObject(path.Replace(".uasset", ""));
            if (asset.TryGetValue<FText>(out var name, "DisplayName"))
            {
                weaponMap[path] = name.Text;
            }
        }
        
        File.WriteAllText(WeaponMappingsPath, JsonConvert.SerializeObject(weaponMap));
        
        var weaponName = string.Empty;
        var weapons = new List<UObject>();
        foreach (var (path, name) in weaponMap)
        {
           if (!name.ToLower().Trim().Equals(input.ToLower())) continue;
           var asset = Provider.LoadObject(path.Replace(".uasset", string.Empty));
           if (weapons.Count == 0)
               weaponName = asset.GetOrDefault<FText>("DisplayName").Text;
               
           weapons.Add(asset);
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
        if (weapons.Count == 1)
            return weapons[0];
        Log.Information("{0} Rarities:", weaponName);
        for (var i = 0; i < weapons.Count; i++)
        {
            var rarity = weapons[i].GetOrDefault("Rarity", EFortRarity.Uncommon);
            var rarityField = typeof(EFortRarity).GetField(rarity.ToString());
            var rarityString = rarityField.GetCustomAttribute<DescriptionAttribute>().Description;
            Log.Information("{0}. {1} {2} ({3})", i+1, rarityString, weaponName, weapons[i].Name);
        }
            
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

