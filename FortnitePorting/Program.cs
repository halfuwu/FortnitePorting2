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
    private static Configuration _config;
    private static readonly DirectoryInfo _exportDirectory = new(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Exports"));
    private static readonly DirectoryInfo _dataDirectory = new(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".data"));
    public static readonly DirectoryInfo _saveDirectory = new(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Saves"));
    
    private static readonly Dictionary<string, Func<string, ExportFile?>> _exports = new()
    {
        {"-character", Character.Export},
        {"-mesh", Mesh.Export},
    };

    public static void Main(string[] args)
    {
        Console.Title = "Fortnite Porting";
        Log.Logger = new LoggerConfiguration().WriteTo.Console().CreateLogger();
        
        if (args.Length == 0)
        {
            Log.Error("No command arguments found");
            Exit(0);
        }

        _config = JsonConvert.DeserializeObject<Configuration>(File.ReadAllText("config.json"));
        if (_config == null)
        {
            Log.Error("Failed to load config");
            Exit(0);
        }
        

        var GamePath = _config.PaksFolder;
        var Key = _config.MainKey;

        Provider = new DefaultFileProvider(GamePath, SearchOption.AllDirectories, true,
            new VersionContainer(EGame.GAME_UE5_LATEST));
        Provider.Initialize();
        Provider.SubmitKey(new FGuid(), new FAesKey(Key));
        foreach (var Entry in _config.DynamicKeys)
        {
            Provider.SubmitKey(new FGuid(Entry.Guid), new FAesKey(Entry.Key));
        }

        var usmap = GetNewestUsmap(_dataDirectory.FullName);
        if (usmap == null) Provider.LoadMappings();
        else Provider.MappingsContainer =
            new FileUsmapTypeMappingsProvider(usmap);
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
        
        Log.Information("Finished exporting {0} in {1}s", export?.name, Math.Round(sw.Elapsed.TotalSeconds, 2));
        Exit(0);
    }
    
    private static string? GetNewestUsmap(string mappingsFolder)
    {
        if (!Directory.Exists(mappingsFolder))
            return null;

        var directory = new DirectoryInfo(mappingsFolder);
        var selectedFilePath = string.Empty;
        var modifiedTime = long.MinValue;
        foreach (var file in directory.GetFiles())
        {
            if (file.Name.EndsWith(".usmap") && file.LastWriteTime.ToFileTimeUtc() > modifiedTime)
            {
                selectedFilePath = file.FullName;
                modifiedTime = file.LastWriteTime.ToFileTimeUtc();
            }
        }

        return selectedFilePath;
    }

    public static void Exit(int code)
    {
        Console.WriteLine("Press any button to exit...");
        Console.ReadKey();
        Environment.Exit(code);
    }

    private class Configuration
    {
        public string PaksFolder;
        public string MainKey;
        public List<DynamicKey> DynamicKeys;

        public class DynamicKey
        {
            public string Guid;
            public string Key;
        }
    }
}