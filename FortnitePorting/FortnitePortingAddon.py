import bpy
from bpy.props import StringProperty, BoolProperty, PointerProperty, EnumProperty, FloatProperty, FloatVectorProperty
from bpy.types import Operator, Panel, PropertyGroup, Scene

import os
import urllib3
import re

from io_import_scene_unreal_psa_psk_280 import pskimport, psaimport
from math import radians
from mathutils import Matrix

import json

bl_info = {
    "name": "Fortnite Porting",
    "author": "Half",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Fortnite Porting",
    "description": "Blender Addon for Fortnite Porting",
    "category": "Import-Export",
}


class FPEnums:
    ShaderType = [
        ("Basic", "Basic", "Basic"),
        ("Default", "Default", "Default"),
        # ("Advanced", "Advanced", "Advanced")
    ]

    ExportType = [
        ("Character", "Character", "Character"),
        ("Backpack", "Backpack", "Backpack"),
        ("Pet", "Pet", "Pet"),
        ("Glider", "Glider", "Glider"),
        ("Pickaxe", "Pickaxe", "Pickaxe"),
        ("Emote", "Emote", "Emote"),
        ("Mesh", "Mesh", "Mesh")
    ]


class FPUtils:

    @staticmethod
    def Popup(text, icon='INFO'):

        def draw(self, context):
            self.layout.label(text=text)

        bpy.context.window_manager.popup_menu(draw, title="Fortnite Porting", icon=icon)

    @staticmethod
    def FixRelativePath(key):
        fix = lambda p: os.path.abspath(bpy.path.abspath(p))

        if key in Settings and Settings[key].startswith('//'):
            Settings[key] = fix(Settings[key])

    @staticmethod
    def WebRequest(url: str) -> urllib3.response.HTTPResponse:
        http = urllib3.PoolManager()
        return http.request("GET", url)

    @staticmethod
    def AppendShaders(*names):
        for name in names:
            if not bpy.data.node_groups.get(name):
                with bpy.data.libraries.load(
                        os.path.join(os.path.dirname(Settings.ConfigFile), "FPShader.blend")) as (
                        data_from, data_to):
                    data_to.node_groups = data_from.node_groups
                break

    @staticmethod
    def ImportAnim(path: str, skeleton: bpy.types.Armature ) -> bool:
        path = path[1:] if path.startswith("/") else path
        AnimPath = os.path.join(os.path.dirname(Settings.ConfigFile), "Saves", path.split(".")[0] + "_SEQ0") + ".psa"
        if not os.path.exists(AnimPath):
            return False
        return psaimport(AnimPath, bpy.context, oArmature=skeleton)

    @staticmethod
    def ImportMesh(path: str) -> bool:
        path = path[1:] if path.startswith("/") else path
        MeshPath = os.path.join(os.path.dirname(Settings.ConfigFile), "Saves",
                                path.split(".")[0] + "_LOD0")
        if os.path.exists(MeshPath + ".psk"):
            MeshPath += ".psk"
        if os.path.exists(MeshPath + ".pskx"):
            MeshPath += ".pskx"
        return pskimport(MeshPath, bpy.context, bReorientBones=Settings.ReorientedBones)

    @staticmethod
    def ImportTexture(path: str) -> bpy.types.Image:
        path = path.split(".")[0]
        path = path[1:] if path.startswith("/") else path
        TexturePath = os.path.join(os.path.dirname(Settings.ConfigFile), "Saves", path + ".png")
        if not os.path.exists(TexturePath):
            return False
        return bpy.data.images.load(TexturePath)

    @staticmethod
    def MergeSkeletons(skeletons):
        bpy.ops.object.select_all(action='DESELECT')

        # crappy code incoming D:
        Skeletons = skeletons
        Meshes = {}
        ConstraintParts = []

        # Join Skeletons
        for Part, Data in Skeletons.items():
            Skeleton = Data["Skeleton"]
            if Part == 'Body':
                bpy.context.view_layer.objects.active = Skeleton  # body skeleton
            if (Part != 'Hat' and Part != 'MiscOrTail') or (Data[
                                                                'Socket'] == 'Face' or Data[
                                                                'Socket'] == "None"):  # skip parented stuff unless face socket or none
                Skeleton.select_set(True)
                Meshes[Part] = FPUtils.MeshFromSkeleton(Skeleton)
            else:
                ConstraintParts.append(Data)

        bpy.ops.object.join()
        MasterSkeleton = bpy.context.active_object
        bpy.ops.object.select_all(action='DESELECT')

        # Join Meshes
        for Part, Mesh in Meshes.items():
            if Part == 'Body':
                bpy.context.view_layer.objects.active = Mesh
            Mesh.select_set(True)
        bpy.ops.object.join()
        bpy.ops.object.select_all(action='DESELECT')

        # Bone Parenting
        MasterBoneTree = {}
        for Bone in MasterSkeleton.data.bones:
            try:
                BoneReg = re.sub(".\d\d\d", "", Bone.name)
                ParentReg = re.sub(".\d\d\d", "", Bone.parent.name)
                MasterBoneTree[BoneReg] = ParentReg
            except AttributeError:
                pass

        bpy.context.view_layer.objects.active = MasterSkeleton
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.armature.select_all(action='DESELECT')
        bpy.ops.object.select_pattern(pattern="*.[0-9][0-9][0-9]")
        bpy.ops.armature.delete()
        SkelBones = MasterSkeleton.data.edit_bones

        for Bone, Parent in MasterBoneTree.items():
            if TargetBone := SkelBones.get(Bone):
                TargetBone.parent = SkelBones.get(Parent)

        # Manual Attachments
        ManualAttachments = {
            "L_eye_lid_lower_mid": "faceAttach",
            "L_eye_lid_upper_mid": "faceAttach",
            "R_eye_lid_lower_mid": "faceAttach",
            "R_eye_lid_upper_mid": "faceAttach",
            "dyn_spine_05": "spine_05"
        }

        for Child, Parent in ManualAttachments.items():
            if TargetBone := SkelBones.get(Child):
                TargetBone.parent = SkelBones.get(Parent)

        bpy.ops.object.mode_set(mode='OBJECT')

        for Part in ConstraintParts:
            Skeleton = Part["Skeleton"]
            Socket = Part["Socket"].lower()
            if Socket == 'hat':
                FPUtils.ConstraintObject(Skeleton, MasterSkeleton, "head")
            if Socket == 'tail':
                FPUtils.ConstraintObject(Skeleton, MasterSkeleton, "pelvis")

    @staticmethod
    def ConstraintObject(child: bpy.types.Object, parent: bpy.types.Object, bone: str,
                         rot=[radians(0), radians(90), radians(0)]):
        constraint = child.constraints.new('CHILD_OF')
        constraint.target = parent
        constraint.subtarget = bone
        child.rotation_mode = 'XYZ'
        child.rotation_euler = rot
        constraint.inverse_matrix = Matrix.Identity(4)

    @staticmethod
    def MeshFromSkeleton(skeleton: bpy.types.Object) -> bpy.types.Object:
        return skeleton.children[0]  # hehe psk mesh

    @staticmethod
    def CreateCollection(name: str):
        if name in bpy.data.collections:
            return
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.collection.create(name=name)
        bpy.context.scene.collection.children.link(bpy.data.collections[name])
        bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[
            name]

    BasicMap = {
        # Name, Shader Idx, Graph Pos
        "TexMap": [
            ("Diffuse", 0, [-300, -75]),
            ("Diffuse Texture with Alpha Mask", 0, [-300, -75]),
            ("M", 1, [-300, -125]),
            ("SpecularMasks", 4, [-300, -175]),
            ("Normals", 5, [-300, -225]),
            ("Emissive", 6, [-300, -275]),
            ("Visor_Emissive", 6, [-300, -275])
        ],
        # Name, Shader Idx
        "NumMap": [
            ("emissive mult", 7),
        ],
        # Name, Shader Idx, Alpha Idx (Optional)
        "VecMap": [
            ("Skin Boost Color And Exponent", 2, 3),
        ],
        # Name, Shader Idx
        "SwitchMap": []

    }

    DefaultMap = {
        "TexMap": [
            ("Diffuse", 0, [-300, -75]),
            ("Diffuse Texture with Alpha Mask", 0, [-300, -75]),
            ("M", 1, [-300, -125]),
            ("SpecularMasks", 8, [-300, -175]),
            ("Normals", 11, [-300, -225]),
            ("Emissive", 13, [-300, -275]),
            ("Visor_Emissive", 13, [-300, -275])
        ],
        "NumMap": [
            ("RoughnessMin", 9),
            ("RoughnessMax", 10),
            ("emissive mult", 14),
        ],
        "VecMap": [
            ("Skin Boost Color And Exponent", 6, 7),
            ("Emissive Color", 16),
            ("EmissiveColor", 16),
        ],
        "SwitchMap": [
            ("Emissive", 15)
        ]
    }

    AdvancedMap = {
        "TexMap": [
            ("Diffuse", 0, [-300, -75]),
            ("M", 1, [-300, -125]),
            ("SpecularMasks", 4, [-300, -175]),
            ("Normals", 5, [-300, -225]),
            ("Emissive", 6, [-300, -275])
        ]
    }

    @staticmethod
    def ImportMaterial(Target, Data, MatName, Mesh=None):
        Target.use_nodes = True
        Target.name = MatName

        nodes = Target.node_tree.nodes
        nodes.clear()
        links = Target.node_tree.links
        links.clear()

        if Mesh and {x for x in ["HairNone", "NoHair"] if x in Target.name}:
            bpy.ops.object.editmode_toggle()
            bpy.ops.mesh.select_all(action='DESELECT')
            slot = Mesh.material_slots.find(Target.name)
            bpy.context.object.active_material_index = slot
            bpy.ops.object.material_slot_select()
            bpy.ops.mesh.delete(type='FACE')
            bpy.ops.object.editmode_toggle()

        Output = nodes.new(type="ShaderNodeOutputMaterial")
        Output.location = 200, 0

        Shader = nodes.new("ShaderNodeGroup")
        Shader.name = "FP " + Settings.ShaderType
        Shader.node_tree = bpy.data.node_groups.get(Shader.name)

        links.new(Shader.outputs[0], Output.inputs[0])

        TargetShaderMap = FPUtils.BasicMap
        if Settings.ShaderType == 'Default':
            TargetShaderMap = FPUtils.DefaultMap
            Shader.inputs[2].default_value = Settings.AOStrength
            Shader.inputs[3].default_value = Settings.CavityStrength
            Shader.inputs[5].default_value = Settings.SSStrength
            if Settings.CustomSS:
                Shader.inputs[4].default_value = (Settings.SSColor[0], Settings.SSColor[1], Settings.SSColor[2], 1)
        elif Settings.ShaderType == 'Advanced':
            TargetShaderMap = FPUtils.AdvancedMap

        def TextureParam(Param):
            NodeInfo = next(filter(lambda x: x[0] == Param.get("Info"), TargetShaderMap["TexMap"]), None)
            if not NodeInfo:
                return

            if not (Image := FPUtils.ImportTexture(Param.get("Value"))):
                return

            Node = nodes.new(type="ShaderNodeTexImage")
            Node.image = Image
            Node.image.alpha_mode = 'CHANNEL_PACKED'
            Node.location = NodeInfo[2]
            Node.hide = True
            if NodeInfo[0] in ("Normals", "SpecularMasks", "M"):
                Node.image.colorspace_settings.name = "Linear"
            links.new(Node.outputs[0], Shader.inputs[NodeInfo[1]])

        def ScalarParam(Param):
            NodeInfo = next(filter(lambda x: x[0] == Param.get("Info"), TargetShaderMap["NumMap"]), None)
            if not NodeInfo:
                return

            Shader.inputs[NodeInfo[1]].default_value = Param.get("Value")

        def VectorParam(Param):
            NodeInfo = next(filter(lambda x: x[0] == Param.get("Info"), TargetShaderMap["VecMap"]), None)
            if not NodeInfo:
                return

            Vector = Param.get("Value")
            Shader.inputs[NodeInfo[1]].default_value = (Vector["R"], Vector["G"], Vector["B"], 1)
            if len(NodeInfo) > 2 and NodeInfo[2]:  # Where to use alpha channel
                Shader.inputs[NodeInfo[2]].default_value = Vector["A"]

        def SwitchParam(Param):
            NodeInfo = next(filter(lambda x: x[0] == Param.get("Info"), TargetShaderMap["SwitchMap"]), None)
            if not NodeInfo:
                return

            Bool = Param.get("Value")
            Shader.inputs[NodeInfo[1]].default_value = 1 if Bool else 0

        if TextureParams := Data.get("TextureParameters"):
            for Param in TextureParams:
                TextureParam(Param)
        if ScalarParams := Data.get("ScalarParameters"):
            for Param in ScalarParams:
                ScalarParam(Param)
        if VectorParams := Data.get("VectorParameters"):
            for Param in VectorParams:
                VectorParam(Param)
        if SwitchParams := Data.get("SwitchParameters"):
            for Param in SwitchParams:
                continue
                # SwitchParam(Param)

    @staticmethod
    def ReadConfig(self, context):
        FPUtils.FixRelativePath('ConfigFile')
        if Settings.ConfigFile == "" or not os.path.exists(Settings.ConfigFile):
            return

        with open(Settings.ConfigFile, 'r') as ConfigFile:
            Config = json.loads(ConfigFile.read())
            Settings.PaksFolder = Config.get("PaksFolder")
            Settings.MainKey = Config.get("MainKey")
            Settings.CloseOnFinish = Config.get("bCloseOnFinish")

    @staticmethod
    def WriteConfig(self, context):
        FPUtils.FixRelativePath('PaksFolder')
        if Settings.ConfigFile == "" or not os.path.exists(Settings.ConfigFile):
            return

        with open(Settings.ConfigFile, 'r') as ConfigFile:
            Config = json.loads(ConfigFile.read())
            Config["PaksFolder"] = Settings.PaksFolder
            Config["MainKey"] = Settings.MainKey
            Config["bCloseOnFinish"] = Settings.CloseOnFinish
            json.dump(Config, open(Settings.ConfigFile, "w"), indent=4)


class FPPanel(Panel):
    bl_category = "Fortnite Porting"
    bl_description = "Panel to interact with the Fortnite Porting Addon"
    bl_label = "Fortnite Porting"
    bl_region_type = 'UI'
    bl_space_type = 'VIEW_3D'

    def draw(self, context):
        global Settings
        Settings = bpy.context.scene.FPSettings
        layout = self.layout

        box = layout.box()
        box.row().label(text="Configuration", icon='MODIFIER')
        box.row().prop(Settings, "ConfigFile")

        if Settings.ConfigFile == "" or not os.path.exists(Settings.ConfigFile):
            layout.row().label(text="Invalid Config File!", icon='ERROR')
            return

        box.row().prop(Settings, "PaksFolder")
        box.row().prop(Settings, "MainKey")
        box.row().prop(Settings, "CloseOnFinish")
        box.row().operator("fp.fill", icon='FILE_REFRESH')

        box = layout.box()
        row = box.row()
        row.label(text="Material Settings", icon='MATERIAL')
        row = box.row()
        row.prop(Settings, "ShaderType", expand=True)

        if Settings.ShaderType != 'Basic':
            BasicBox = box.box()
            BasicBox.row().label(text="Basic", icon='OPTIONS')
            BasicBox.row().prop(Settings, "AOStrength")
            BasicBox.row().prop(Settings, "CavityStrength")
            BasicBox.row().prop(Settings, "SSStrength")
            SSRow = BasicBox.row()
            SSRow.prop(Settings, "CustomSS")
            if Settings.CustomSS:
                SSRow.prop(Settings, "SSColor")
            Alpha = BasicBox.row()
            Alpha.prop(Settings, "AlphaVertex")
            Alpha.enabled = False

        if Settings.ShaderType == 'Advanced':
            FXBox = box.box()
            FXBox.row().label(text="FX", icon='SHADERFX')
            FXBox.row().prop(Settings, "FXEmission")
            FXBox.row().prop(Settings, "FXClearCoat")
            FXBox.row().prop(Settings, "FXThinFilm")
            FXBox.row().prop(Settings, "FXFuzz")

        box = layout.box()
        box.row().label(text="Import", icon='IMPORT')
        box.row().prop(Settings, "MergeSkeletons")
        box.row().prop(Settings, "ReorientedBones")
        box.row().prop(Settings, "ImportQuads")
        box.row().prop(Settings, "ImportMaterials")
        box.row().prop(Settings, "CreateCollections")
        box.row().prop(Settings, "ImportFile")
        ImportButtonRow = box.row()
        ImportButtonRow.operator("fp.import", icon='IMPORT')
        ImportButtonRow.enabled = Settings.ImportFile != ""

        box = layout.box()
        box.row().label(text="Export", icon='EXPORT')
        box.row().prop(Settings, "ExportType")
        box.row().prop(Settings, "ExportString")
        ExportButtonRow = box.row()
        ExportButtonRow.operator("fp.export", icon='IMPORT')
        ExportButtonRow.enabled = Settings.ExportString != ""

        box = layout.box()
        box.row().label(text="Misc", icon='INFO')
        box.row().operator("fp.checkupdate", icon='FILE_REFRESH')


class FPSettings(PropertyGroup):
    # Config
    ConfigFile: StringProperty(name="Config", subtype='FILE_PATH', update=FPUtils.ReadConfig)
    PaksFolder: StringProperty(name="Paks", subtype='DIR_PATH', update=FPUtils.WriteConfig)
    MainKey: StringProperty(name="Main Key", update=FPUtils.WriteConfig)
    CloseOnFinish: BoolProperty(name="Close Console on Finish", update=FPUtils.WriteConfig)

    # Export
    ExportType: EnumProperty(name="Export", items=FPEnums.ExportType, default='Character')
    ExportString: StringProperty(name="")

    # Import
    MergeSkeletons: BoolProperty(name="Merge Skeletons")
    ReorientedBones: BoolProperty(name="Reorient Bones")
    ImportQuads: BoolProperty(name="Use Quad Topology", default=True)
    ImportMaterials: BoolProperty(name="Import Materials", default=True)
    CreateCollections: BoolProperty(name="Create Collections", default=True)
    ImportFile: StringProperty(name="Import File", subtype='FILE_PATH',
                               update=lambda s, c: FPUtils.FixRelativePath('ImportFile'))

    # Material
    ShaderType: EnumProperty(name="Shader", items=FPEnums.ShaderType, default='Default')

    SSStrength: FloatProperty(name="Subsurface", default=0.0, min=0.0, max=1.0, subtype='FACTOR')
    AOStrength: FloatProperty(name="Ambient Occlusion", default=0.0, min=0.0, max=1.0, subtype='FACTOR')
    CavityStrength: FloatProperty(name="Cavity", default=0.0, min=0.0, max=1.0, subtype='FACTOR')
    CustomSS: BoolProperty(name="Custom Subsurface Color")
    SSColor: FloatVectorProperty(name="", subtype='COLOR', default=[1.0, 0.2, 0.1], min=0.0, max=1.0)
    AlphaVertex: BoolProperty(name="Use Vertex Color Masking", description="Not Implemented")

    FXEmission: BoolProperty(name="Use FX Emission")
    FXClearCoat: BoolProperty(name="Use FX ClearCoat")
    FXThinFilm: BoolProperty(name="Use FX ThinFilm")
    FXFuzz: BoolProperty(name="Use FX Fuzz")


class FPImport(Operator):
    bl_idname = "fp.import"
    bl_label = "Import"

    def execute(self, context):
        self.Import()
        return {'FINISHED'}

    @staticmethod
    def Import():
        bpy.ops.object.select_all(action='DESELECT')
        with open(Settings.ImportFile, 'r') as ImportFile:
            Processed = json.loads(ImportFile.read())

        Name = Processed.get("name")
        Type = Processed.get("type")

        if Type == 'Emote':
            Active = bpy.context.active_object
            if Active.type == 'ARMATURE':
                pass
            else:
                FPUtils.Popup("A Skeleton must be Selected!", icon='ERROR')
                return {'FINISHED'}

            AnimPath = Processed.get("animPart").get("animPath")
            AnimName = AnimPath.split(".")[1]

            FPUtils.ImportAnim(AnimPath, Active)
        else:
            FPUtils.AppendShaders("FP Basic", "FP Default")
            if Settings.CreateCollections:
                FPUtils.CreateCollection(Name)

            ImportedSlots = {}

            def ImportPart(part):
                SlotType = part.get("slotType")
                SocketName = part.get("socketName")
                MeshPath = part.get("meshPath")

                if SlotType and SlotType in ImportedSlots:
                    return

                if not FPUtils.ImportMesh(MeshPath):
                    return

                if Type == 'Mesh':
                    ImportedMesh = bpy.context.active_object
                else:
                    Armature = bpy.context.active_object
                    ImportedSlots[SlotType] = {
                        "Skeleton": Armature,
                        "Socket": SocketName
                    }
                    ImportedMesh = FPUtils.MeshFromSkeleton(Armature)

                bpy.context.view_layer.objects.active = ImportedMesh
                ImportedMesh.select_set(True)
                ImportedMesh.data.use_auto_smooth = 0
                bpy.ops.object.shade_smooth()

                if Settings.ImportQuads:
                    bpy.ops.object.editmode_toggle()
                    bpy.ops.mesh.tris_convert_to_quads(uvs=True)

                    if SlotType == 'Head':
                        bpy.ops.mesh.remove_doubles()
                    bpy.ops.object.editmode_toggle()

                if Settings.ImportMaterials:
                    for Material in part.get("materials"):
                        MaterialIdx = Material.get("matIdx")
                        if MaterialIdx >= len(ImportedMesh.material_slots):
                            continue
                        FPUtils.ImportMaterial(ImportedMesh.material_slots.values()[Material.get("matIdx")].material,
                                               Material.get("matParameters"), Material.get("matPath").split(".")[1],
                                               ImportedMesh)

            if StyleParts := Processed.get("variantParts"):
                for StylePart in StyleParts:
                    ImportPart(StylePart)

            if BaseStyle := Processed.get("baseStyle"):
                for BasePart in BaseStyle:
                    ImportPart(BasePart)

            if StyleMaterials := Processed.get("variantMaterials"):
                for StyleMaterial in StyleMaterials:
                    MaterialToSwap = StyleMaterial.get("materialToSwap").split(".")[1]
                    OverrideMaterialName = StyleMaterial.get("overrideMaterial").split(".")[1]
                    FPUtils.ImportMaterial(bpy.data.materials[MaterialToSwap], StyleMaterial.get("matParameters"),
                                           OverrideMaterialName)

            if Settings.MergeSkeletons and len(ImportedSlots) > 1:
                FPUtils.MergeSkeletons(ImportedSlots)

            bpy.ops.object.select_all(action='DESELECT')


class FPExport(Operator):
    bl_idname = "fp.export"
    bl_label = "Export"

    def execute(self, context):
        if Settings.PaksFolder == '':
            FPUtils.Popup("Paks Folder is Empty! Cannot Export.", 'ERROR')
        elif Settings.MainKey == '':
            FPUtils.Popup("Main Key is Empty! Cannot Export.", 'ERROR')
        else:
            self.Export()
        return {'FINISHED'}

    @staticmethod
    def Export():
        os.chdir(os.path.dirname(Settings.ConfigFile))
        os.system(f'START FortnitePorting.exe -{Settings.ExportType.lower()} "{Settings.ExportString}"')


class FPFill(Operator):
    bl_idname = "fp.fill"
    bl_label = "Update Keys + Mappings"

    def execute(self, context):
        AesResp = FPUtils.WebRequest("https://benbot.app/api/v2/aes")
        Aes = json.loads(AesResp.data)
        if Key := Aes.get("mainKey"):
            Settings.MainKey = Key

        with open(Settings.ConfigFile, 'r') as ConfigFile:
            Config = json.loads(ConfigFile.read())
            while len(Config["DynamicKeys"]) != 0:
                Config["DynamicKeys"].pop()

            for Entry in Aes.get("dynamicKeys"):
                Config["DynamicKeys"].append({
                    "Guid": Entry.get("guid"),
                    "Key": Entry.get("key")
                })

        ConfigJson = json.dumps(Config, indent=4)
        with open(Settings.ConfigFile, 'w') as ConfigFile:
            ConfigFile.write(ConfigJson)

        dataPath = os.path.join(os.path.dirname(Settings.ConfigFile), ".data")
        if not os.path.exists(dataPath):
            os.makedirs(dataPath)

        MapResp = FPUtils.WebRequest("https://benbot.app/api/v1/mappings")
        Map = json.loads(MapResp.data)
        for File in Map:
            if File.get("meta").get("compressionMethod") == "Oodle":
                UsmapResp = FPUtils.WebRequest(File.get("url"))
                with open(os.path.join(os.path.dirname(Settings.ConfigFile), ".data", File.get("fileName")),
                          'wb') as UsmapFile:
                    UsmapFile.write(UsmapResp.data)

        FPUtils.Popup("Updated Keys and Mappings for " + Aes.get("version"))

        return {'FINISHED'}


class FPCheckUpdate(Operator):
    bl_idname = "fp.checkupdate"
    bl_label = "Check for Updates"

    TargetUpdate = None

    def execute(self, context):
        FPUtils.Popup("Not Implemented Yet!", icon='ERROR')
        return {'FINISHED'}

        Resp = FPUtils.WebRequest("https://api.github.com/repos/halfuwu/FortnitePorting2/releases")
        Releases = json.loads(Resp.data)
        Tag = Releases[0].get("tag_name")
        FPCheckUpdate.TargetUpdate = Tag

        FoundVersionS = Tag.split(".")
        FoundVersion = int(FoundVersionS[0]), int(FoundVersionS[1]), int(FoundVersionS[2])
        CurrentVersion = bl_info["version"]
        if FoundVersion > CurrentVersion:
            bpy.context.window_manager.popup_menu(FPCheckUpdate.DrawUpdateWindow, title="Fortnite Porting Update",
                                                  icon='FILE_TICK')
        else:
            FPUtils.Popup("Up to Date!")
        return {'FINISHED'}

    @staticmethod
    def DrawUpdateWindow(self, context):
        layout = self.layout
        layout.row().label(text=f"An update for Version {FPCheckUpdate.TargetUpdate} was found! ")
        layout.row().operator("fp.update", icon='IMPORT')


class FPUpdate(Operator):
    bl_idname = "fp.update"
    bl_label = "Update Program?"

    def execute(self, context):
        Resp = FPUtils.WebRequest("https://api.github.com/repos/halfuwu/FortnitePorting2/releases")
        Releases = json.loads(Resp.data)
        ZipRelease = json.loads(FPUtils.WebRequest(Releases[0].get("assets_url")).data)[0]

        return {'FINISHED'}


Operators = [FPPanel, FPSettings, FPImport, FPExport, FPFill, FPCheckUpdate, FPUpdate]


def register():
    for Op in Operators:
        bpy.utils.register_class(Op)

    Scene.FPSettings = PointerProperty(type=FPSettings)


def unregister():
    for Op in Operators:
        bpy.utils.unregister_class(Op)

    del Scene.FPSettings


if __name__ == "__main__":
    register()
