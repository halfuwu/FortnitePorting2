using System.Diagnostics;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse.UE4.Versions;
using CUE4Parse.Utils;
using FortnitePorting.Exports;
using Newtonsoft.Json;
using Serilog;

namespace FortnitePorting;

public static class FortnitePorting
{
    public static DefaultFileProvider Provider;
    public static Configuration Config;
    public static DirectoryInfo saveDirectory = new(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Saves"));
    private static readonly DirectoryInfo _exportDirectory = new(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Exports"));
    public static readonly DirectoryInfo DataDirectory = new(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".data"));
  
    
    private static readonly Dictionary<string, Func<string, ExportFile?>> _exports = new()
    {
        {"-characterbr", Character.ExportBR},
        {"-characterstw", Character.ExportSTW},
        {"-backpack", Backpack.Export},
        {"-pet", Pet.Export},
        {"-glider", Glider.Export},
        {"-pickaxe", Pickaxe.Export},
        {"-weapon", Weapon.Export},
        //{"-vehicle", Vehicle.Export},
        {"-mesh", Mesh.Export},
        {"-prop", Prop.Export},
    };

    public static void Main(string[] args)
    {
        try
        {
            Console.Title = "Fortnite Porting";
            
            Directory.CreateDirectory(_exportDirectory.FullName);
            Directory.CreateDirectory(saveDirectory.FullName);
            
            var logPath = $"Logs/FortnitePorting-{DateTime.UtcNow:yyyy-MM-dd-hh-mm-ss}.log";
            Log.Logger = new LoggerConfiguration().WriteTo.Console().WriteTo.File(logPath).CreateLogger();
            
            if (args.Length == 0)
            {
                Log.Error("No command arguments found");
                Exit(1);
            }

            var type = args[0];
            if (!_exports.ContainsKey(type))
            {
                Log.Error("Invalid type parameter: {0}", type);
                Exit(1);
            }
            
            LoadConfig();
            if (Config.ExportFolder != string.Empty && Directory.Exists(Config.ExportFolder))
                saveDirectory = new DirectoryInfo(Config.ExportFolder);

            LoadProvider();
            
            
            var sw = new Stopwatch();
            var inputs = args[1].Trim().Split(",");
            foreach (var input in inputs)
            {
                var name = input.Trim();
                sw.Restart();
                Log.Information("Exporting {0}: {1}", type[1..], name);
                var export = _exports[type](name);
                if (export == null)
                {
                    Log.Error("Failed to export {0}: {1}", type[1..], name);
                    continue;
                }
                export.name = export.name.Trim();
                Task.WaitAll(AssetHelpers.RunningTasks.ToArray());
                
                var exportJson = JsonConvert.SerializeObject(export,
                    new JsonSerializerSettings
                        { Formatting = Formatting.Indented, NullValueHandling = NullValueHandling.Ignore });
                Directory.CreateDirectory(Path.Combine(_exportDirectory.FullName, export.type));
                File.WriteAllText(Path.Combine(_exportDirectory.FullName, export.type, export.name + ".json"), exportJson);
                
                sw.Stop();
                Log.Information("Finished exporting {0} in {1}s \n", export.name, Math.Round(sw.Elapsed.TotalSeconds, 2));
            }
            
          
        }
        catch (Exception e)
        {
            Log.Fatal(e.Message + e.StackTrace);
            Log.Fatal("An error occurred, please report this issue");
            Exit(1);
        }
        
        if (!Config.bCloseOnFinish)
            Exit(0);
    }

    public static void LoadConfig(string path = "config.json")
    {
        Config = JsonConvert.DeserializeObject<Configuration>(File.ReadAllText(path));
        if (Config == null)
        {
            Log.Error("Failed to load config");
            Exit(1);
        }
    }

    public static void LoadProvider()
    {
        var GamePath = Config.PaksFolder;
        var Key = Config.MainKey;

        var ExtraDirs = new List<DirectoryInfo>
        {
            new(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData) +
                "\\FortniteGame\\Saved\\PersistentDownloadDir\\InstalledBundles"),
        };

        ExtraDirs = ExtraDirs.Where(x => Directory.Exists(x.FullName)).ToList();
        Provider = new DefaultFileProvider(new DirectoryInfo(GamePath), ExtraDirs,
            SearchOption.AllDirectories, true, new VersionContainer(EGame.GAME_UE5_LATEST));
        Provider.Initialize();
        Provider.SubmitKey(new FGuid(), new FAesKey(Key));
        foreach (var Entry in Config.DynamicKeys)
        {
            Provider.SubmitKey(new FGuid(Entry.Guid), new FAesKey(Entry.Key));
        }

        var usmap = GetNewestUsmap(DataDirectory.FullName);
        if (usmap == null)
        {
            Log.Error("Failed to load mappings from file, attempting to load benbot mappings");
            Provider.LoadMappings();
        }
        else
        {
            Log.Information("Loading mappings from {0}", usmap);
            Provider.MappingsContainer = new FileUsmapTypeMappingsProvider(usmap); 
        }
    }
    
    private static string? GetNewestUsmap(string mappingsFolder)
    {
        if (!Directory.Exists(mappingsFolder))
            return null;

        var directory = new DirectoryInfo(mappingsFolder);
        string? selectedFilePath = null;
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

    public class Configuration
    {
        public string PaksFolder;
        public string ExportFolder;
        public bool bCloseOnFinish;
        public string MainKey;
        public List<DynamicKey> DynamicKeys;

        public class DynamicKey
        {
            public string Guid;
            public string Key;
        }
    }
}