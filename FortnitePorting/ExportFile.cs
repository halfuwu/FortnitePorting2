using CUE4Parse.UE4.Objects.Core.Math;

namespace FortnitePorting;

public class ExportFile
{
    public string name;
    public string type;
    public ExportAnim animPart;
    public List<ExportPart> baseStyle;
    public List<ExportPart> variantParts;
    public List<ExportVariantMaterial> variantMaterials;
    public List<ExportVariantParameters> variantParameters;
}

public class ExportPart
{
    public string meshPath;
    public string slotType;
    public string socketName;
    public List<ExportMaterial> materials;
}

public class ExportAnim
{
    public string animPath;
}

public class ExportMaterial
{
    public string matPath;
    public int matIdx;
    public ExportMaterialParameters matParameters;
}

public class ExportVariantMaterial 
{
    public string overrideMaterial;
    public string materialToSwap;
    public int matIdx;
    public ExportMaterialParameters matParameters;
}

public class ExportMaterialParameters
{
    public List<TextureParameter> TextureParameters;
    public List<ScalarParameter> ScalarParameters;
    public List<VectorParameter> VectorParameters;
    public List<VectorParameter> ComponentMaskParameters;
    public List<SwitchParameter> SwitchParameters;
    public SubsurfaceInfo SubsurfaceInfo;
}

public class ExportVariantParameters
{
    public string materialToAlter;
    public List<TextureParameter> TextureParameters;
    public List<ScalarParameter> ScalarParameters;
    public List<VectorParameter> VectorParameters;
}

public class SubsurfaceInfo
{
    public float scatterRadius;
    public FLinearColor color;
}

public class TextureParameter
{
    public string Info;
    public string Value;
}
public class ScalarParameter
{
    public string Info;
    public float Value;
}
public class SwitchParameter
{
    public string Info;
    public bool Value;
}
public class VectorParameter
{
    public string Info;
    public FLinearColor Value;
}
