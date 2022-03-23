using System.Diagnostics;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;
using FortnitePorting.Exports;
using Newtonsoft.Json;
using Serilog;

namespace FortnitePorting;

public static class Program
{
    public static DefaultFileProvider Provider;
    private static readonly DirectoryInfo _exportDirectory = new(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Exports"));
    public static readonly DirectoryInfo _saveDirectory = new(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Saves"));
    
    private static readonly Dictionary<string, Func<string, ExportFile?>> _exports = new()
    {
        {"-character", Character.Export},
    };

    public static void Main(string[] args)
    {
        Log.Logger = new LoggerConfiguration().WriteTo.Console().CreateLogger();
        
        if (args.Length == 0)
        {
            Log.Error("No command arguments found");
            return;
        }

        const string GamePath = @"C:/Fortnite/FortniteGame/Content/Paks/";
        const string Key = "0x53839BA2A77AE393588184ACBD18EDBC935CA60D554F9D29BC3F135E426C4A6F";

        Provider = new DefaultFileProvider(GamePath, SearchOption.AllDirectories, true,
            new VersionContainer(EGame.GAME_UE5_LATEST));
        Provider.Initialize();
        Provider.SubmitKey(new FGuid(), new FAesKey(Key));
        Provider.MappingsContainer =
            new FileUsmapTypeMappingsProvider(".data/++Fortnite+Release-20.00-CL-19381079-Windows_oo.usmap");
        Directory.CreateDirectory(_exportDirectory.FullName);
        Directory.CreateDirectory(_saveDirectory.FullName);

        var sw = new Stopwatch();
        sw.Start();
        var type = args[0];
        var input = args[1];
        var export = _exports[type](input);

        if (export == null)
        {
            Log.Information("Failed to export {0}", input);
            Exit(1);
        }

        var exportJson = JsonConvert.SerializeObject(export, new JsonSerializerSettings { Formatting = Formatting.Indented, NullValueHandling = NullValueHandling.Ignore});
        File.WriteAllText(Path.Combine(_exportDirectory.FullName, export?.name + ".json"), exportJson);
        sw.Stop();
        
        Log.Information("Finished exporting {0} in {1}s", export?.name, sw.Elapsed.TotalSeconds);
        Exit(0);
    }

    public static void Exit(int code)
    {
        Console.WriteLine("Press any button to exit...");
        Console.ReadKey();
        Environment.Exit(code);
    }
}