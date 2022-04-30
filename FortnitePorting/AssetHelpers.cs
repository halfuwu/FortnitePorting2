﻿using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Animation;
using CUE4Parse.UE4.Assets.Exports.Material;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Assets.Exports.StaticMesh;
using CUE4Parse.UE4.Assets.Exports.Texture;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Objects.Core.i18N;
using CUE4Parse.UE4.Objects.Core.Math;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse.Utils;
using CUE4Parse_Conversion.Animations;
using CUE4Parse_Conversion.Meshes;
using CUE4Parse_Conversion.Textures;
using Serilog;
using SkiaSharp;
using static FortnitePorting.Program;

namespace FortnitePorting;

public static class AssetHelpers
{
    public static void ExportCharacterParts(IEnumerable<UObject> parts, List<ExportPart> exportParts)
    {
        foreach (var part in parts)
        {
            var exportPart = new ExportPart();

            if (!part.TryGetValue(out USkeletalMesh skeletalMesh, "SkeletalMesh")) 
                continue;
            ExportObject(skeletalMesh);
            exportPart.meshPath = skeletalMesh.GetPathName();

            part.TryGetValue<EFortCustomPartType>(out var slotType, "CharacterPartType");
            exportPart.slotType = slotType.ToString();

            if (part.TryGetValue<UObject>(out var AdditionalData, "AdditionalData"))
            {
                exportPart.socketName = AdditionalData
                    .GetOrDefault<FName>("AttachSocketName", null, StringComparison.OrdinalIgnoreCase).Text;
            }

            
            



            skeletalMesh.TryConvert(out var convertedMesh);
            if (convertedMesh.LODs.Count == 0) continue;
            
            exportPart.materials = new List<ExportMaterial>();
            foreach (var (section, matIdx) in convertedMesh.LODs[0].Sections.Value.Enumerate())
            {
                if (section.Material == null) continue;
                if (section.Material.TryLoad(out var sectionMaterial))
                {
                    if (sectionMaterial is UMaterialInstanceConstant materialInstance)
                    {
                        var material = new ExportMaterial
                        {
                            matPath = materialInstance.GetPathName(),
                            matIdx = matIdx,
                            matParameters = ExportMaterialParams(materialInstance)
                        };
                        exportPart.materials.Add(material);
                    }
                    else
                    {
                        var material = new ExportMaterial
                        {
                            matPath = sectionMaterial.GetPathName(),
                            matIdx = matIdx,
                            matParameters = new ExportMaterialParameters()
                        };
                        exportPart.materials.Add(material);
                    }
                }
            }

            if (part.TryGetValue(out FStructFallback[] overrides, "MaterialOverrides"))
            {
                foreach (var matOverride in overrides)
                {
                    var materialPath = matOverride.Get<FSoftObjectPath>("OverrideMaterial");
                    if (materialPath.TryLoad(out UMaterialInstanceConstant materialInstance))
                    {
                        var material = new ExportMaterial
                        {
                            matPath = materialInstance.GetPathName(),
                            matIdx = matOverride.Get<int>("MaterialOverrideIndex"),
                            matParameters = ExportMaterialParams(materialInstance)
                        };
                        exportPart.materials.Add(material);
                    }
                }
            }
            
            exportParts.Add(exportPart);
        }
    }

    public static void ExportStyles(IEnumerable<UObject> styles, ref ExportFile? export)
    {
        foreach (var style in styles)
        {
            if (style.ExportType == "AthenaCharacterItemDefinition") continue;
            var selectedStyle = style.ExportType switch
            {
                "FortCosmeticCharacterPartVariant" => PromptStyle(style, "PartOptions"),
                "FortCosmeticMaterialVariant" => PromptStyle(style, "MaterialOptions"),
                "FortCosmeticParticleVariant" => PromptStyle(style, "ParticleOptions"),
                _ => default
            };

            if (selectedStyle.TryGetValue(out UObject[] variantParts, "VariantParts")  && variantParts.Length > 0)
            {
                export.variantParts = new List<ExportPart>();
                ExportCharacterParts(variantParts, export.variantParts);
            }
            if (selectedStyle.TryGetValue(out FStructFallback[] variantMaterials, "VariantMaterials") && variantMaterials.Length > 0)
            {
                export.variantMaterials = new List<ExportVariantMaterial>();
                foreach (var material in variantMaterials)
                {
                    if (material.TryGetValue(out UMaterialInstanceConstant overrideMaterial, "OverrideMaterial"))
                    {
                        export.variantMaterials.Add(new ExportVariantMaterial
                        {
                            overrideMaterial = material.Get<FSoftObjectPath>("OverrideMaterial").AssetPathName.Text,
                            matIdx = material.Get<int>("MaterialOverrideIndex"),
                            materialToSwap = material.Get<FSoftObjectPath>("MaterialToSwap").AssetPathName.Text,
                            MaterialParameters = ExportMaterialParams(overrideMaterial)
                        });
                    }
                }
            }
            
            // TODO Variant Params
        }
    }

    private static FStructFallback PromptStyle(UObject style, string optionsName)
    {
        var options = style.Get<FStructFallback[]>(optionsName);
        var channelName = style.GetOrDefault("VariantChannelName", new FText("INVALID"));
        
        Log.Information("{0} Variants:", channelName);
        for (var i = 0; i < options.Length; i++)
            Log.Information("{0}. {1}", i+1, options[i].Get<FText>("VariantName").Text);

        int selectedStyleIdx;
        while (true)
        {
            try
            {
                Log.Information("Enter Number of Variant:");
                selectedStyleIdx = int.Parse(Console.ReadLine() ?? string.Empty)-1;

                if (selectedStyleIdx > options.Length-1 || selectedStyleIdx < 0)
                    Log.Information("Number of Variant does not exist");
                else
                    break;
            }
            catch (FormatException)
            {
                Log.Information("Variant can only be selected by its number");
            }
        }

        return options[selectedStyleIdx];
    }
    public static ExportMaterialParameters ExportMaterialParams(UMaterialInstanceConstant material)
    {
        var parameters = new ExportMaterialParameters();
        
        parameters.TextureParameters = new List<TextureParameter>();
        foreach (var param in material.TextureParameterValues)
        {
            if (param.ParameterValue.TryLoad(out UTexture texture))
            {
                ExportObject(texture);
                parameters.TextureParameters.Add(new TextureParameter
                {
                    Info = param.ParameterInfo.Name.Text,
                    Value = texture.GetPathName()
                });
            }
        }
        
        parameters.ScalarParameters = new List<ScalarParameter>();
        foreach (var param in material.ScalarParameterValues)
        {
            parameters.ScalarParameters.Add(new ScalarParameter
            {
                Info = param.ParameterInfo.Name.Text,
                Value = param.ParameterValue
            });
        }
        
        parameters.VectorParameters = new List<VectorParameter>();
        foreach (var param in material.VectorParameterValues)
        {
            if (param.ParameterValue == null) continue;
            parameters.VectorParameters.Add(new VectorParameter
            {
                Info = param.ParameterInfo.Name.Text,
                Value = param.ParameterValue.Value
            });
        }

        if (material.TryGetValue(out FStructFallback staticParameters, "StaticParameters"))
        {
            if (staticParameters.TryGetValue(out FStructFallback[] componentMaskParams, "StaticComponentMaskParameters"))
            {
                parameters.ComponentMaskParameters = new List<VectorParameter>();
                foreach (var param in componentMaskParams)
                {
                    parameters.ComponentMaskParameters.Add(new VectorParameter
                    {
                        Info = param.Get<FStructFallback>("ParameterInfo").Get<FName>("Name").ToString(),
                        Value = new FLinearColor(
                            Convert.ToByte(param.Get<bool>("R")),
                            Convert.ToByte(param.Get<bool>("G")),
                            Convert.ToByte(param.Get<bool>("B")),
                            Convert.ToByte(param.Get<bool>("A"))
                        )
                    });
                }
            }
            if (staticParameters.TryGetValue(out FStructFallback[] switchParams, "StaticSwitchParameters"))
            {
                parameters.SwitchParameters = new List<SwitchParameter>();
                foreach (var param in switchParams)
                {
                    parameters.SwitchParameters.Add(new SwitchParameter
                    {
                        Info = param.Get<FStructFallback>("ParameterInfo").Get<FName>("Name").Text,
                        Value = param.Get<bool>("Value")
                    });
                }
            }
        }
        
        return parameters;
    }

    public static void ExportObject(UObject file)
    {
        try
        {
            if (!File.Exists(GetExportPath(file, "psk", "_LOD0")) && file is USkeletalMesh skeletalMesh)
            {
                ThreadPool.QueueUserWorkItem(_ =>
                {
                    //Log.Information("Saving {0}", file);
                    var exporter = new MeshExporter(skeletalMesh, ELodFormat.FirstLod, false);
                    
                    exporter.TryWriteToDir(_saveDirectory, out var _);
                });
            }
            else if (!File.Exists(GetExportPath(file, "pskx", "_LOD0")) && file is UStaticMesh staticMesh)
            {
                ThreadPool.QueueUserWorkItem(_ =>
                {
                    //Log.Information("Saving {0}", file);
                    var exporter = new MeshExporter(staticMesh, ELodFormat.FirstLod, false);
                    exporter.TryWriteToDir(_saveDirectory, out var _);
                });
            }
            else if (!File.Exists(GetExportPath(file, "png")) && file is UTexture2D texture)
            {
                ThreadPool.QueueUserWorkItem(_ =>
                {
                    //Log.Information("Saving {0}", file);
                    var texturePath = GetExportPath(file, "png");
                    Directory.CreateDirectory(texturePath.Replace('\\', '/').SubstringBeforeLast('/'));
                    using var bitmap = texture.Decode(texture.GetFirstMip());
                    using var data = bitmap?.Encode(SKEncodedImageFormat.Png, 100);
                    using var stream = new FileStream(texturePath, FileMode.Create, FileAccess.Write);

                    data?.AsStream().CopyTo(stream);
                });
            }
            else if (!File.Exists(GetExportPath(file, "psa", "_SEQ0")) && file is UAnimSequence anim)
            {
                ThreadPool.QueueUserWorkItem(_ =>
                {
                    //Log.Information("Saving {0}", file);
                    var exporter = new AnimExporter(anim);
                    exporter.TryWriteToDir(_saveDirectory, out var _);
                });
            }
        }
        catch (IOException) {}
    }
    private static string GetExportPath(UObject obj, string ext, string extra = "")
    {
        var path = obj.Owner.Name;
        path = path.SubstringBeforeLast('.');
        if (path.StartsWith("/")) path = path[1..];

        var finalPath = Path.Combine(_saveDirectory.FullName, path) + $"{extra}.{ext.ToLower()}";
        return finalPath;
    }
    private enum EFortCustomPartType
    {
        Head,
        Body,
        Hat,
        Backpack,
        MiscOrTail,
        Face,
        Gameplay,
        NumTypes
    }

    private enum ECustomHatType
    {
        HeadReplacement,
        Cap,
        Mask,
        Helmet,
        Hat
    }

    public static IEnumerable<(T item, int index)> Enumerate<T>(this IEnumerable<T> self)
        => self.Select((item, index) => (item, index));
}