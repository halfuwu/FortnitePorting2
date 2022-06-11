using System.Globalization;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.Engine;
using CUE4Parse.Utils;
using Serilog;
using static FortnitePorting.FortnitePorting;
namespace FortnitePorting.Exports;

public static class Vehicle
{
    public static ExportFile? Export(string input)
    {
        var potentialVehicles = new List<UObject>();
        foreach (var (path, _) in Provider.Files)
        {
            if (!path.SubstringAfterLast("/").StartsWith("vid_")) continue;
            
            var asset = Provider.LoadObject(path.Replace(".uasset", ""));
            if (asset.TryGetValue<FText>(out var name, "DisplayName"))
            {
                if (input.Equals(name.Text))
                    potentialVehicles.Add(asset);
            }
            if (asset.TryGetValue<string[]>(out var vehicleNames, "SpawnVehicleNames")) 
                potentialVehicles.AddRange(from vehicleName in vehicleNames where vehicleName.ToLower().Contains(input.ToLower()) select asset);
            
        }

        if (potentialVehicles.Count > 0)
        {
            var selectedVehicle = PromptVehicle(potentialVehicles, input);
        
            var export = new ExportFile();
            export.type = "Vehicle";
            var displayName = selectedVehicle.GetOrDefault<FText>("DisplayName");
            export.name = displayName is null ? selectedVehicle.Name : displayName.Text;
            export.baseStyle = new List<ExportPart>();
            
            var exportPart = new ExportPart();
            export.baseStyle.Add(exportPart);
            
            var blueprintClass = selectedVehicle.Get<UBlueprintGeneratedClass>("VehicleActorClass");
            var components = blueprintClass.ClassDefaultObject.Load();
            var skeletalMeshComponent = components.Get<UObject>("SkeletalMesh");
            var skeletalMesh = skeletalMeshComponent.Get<USkeletalMesh>("SkeletalMesh");
            Mesh.ExportSkeletalMesh(skeletalMesh, ref exportPart);

            return export;
        }

        return null;
    }

    private static UObject PromptVehicle(IReadOnlyList<UObject> vehicles, string vehicleName)
    {
        if (vehicles.Count == 1)
            return vehicles[0];
        Log.Information("Searched {0} Vehicles:", CultureInfo.CurrentCulture.TextInfo.ToTitleCase(vehicleName));
        for (var i = 0; i < vehicles.Count; i++)
        {
            Log.Information("{0}. {1}", i + 1, vehicles[i].Name);
        }

        int selectedVehicleIdx;
        while (true)
        {
            try
            {
                Log.Information("Enter Number of Vehicle:");
                selectedVehicleIdx = int.Parse(Console.ReadLine() ?? string.Empty) - 1;

                if (selectedVehicleIdx > vehicles.Count - 1 || selectedVehicleIdx < 0)
                    Log.Information("Number of Vehicle does not exist");
                else
                    break;
            }
            catch (FormatException)
            {
                Log.Information("Vehicle can only be selected by its number");
            }
        }

        return vehicles[selectedVehicleIdx];
    }
}