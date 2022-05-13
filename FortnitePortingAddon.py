import bpy
import mathutils
from bpy.props import StringProperty, BoolProperty, PointerProperty, EnumProperty, FloatProperty, FloatVectorProperty
from bpy.types import Operator, Panel, PropertyGroup, Scene

import os
import urllib3
import re

from io_import_scene_unreal_psa_psk_280 import pskimport, psaimport
from math import radians
from mathutils import Matrix, Vector

import json

bl_info = {
    "name": "Fortnite Porting",
    "author": "Half",
    "version": (0, 0, 3),
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
        ("Weapon", "Weapon", "Weapon"),
        ("Mesh", "Mesh", "Mesh")
    ]

    CharacterType = [
        ("Battle Royale", "Battle Royale", "Battle Royale"),
        ("Save The World", "Save The World", "Save The World"),
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
    def CheckAppendData():
        with bpy.data.libraries.load(
                os.path.join(os.path.dirname(Settings.ConfigFile), "FPData.blend")) as (
                data_from, data_to):
            for name in ['FP Basic', 'FP Default', 'FP Cropped Emissive']:
                if not bpy.data.node_groups.get(name):
                    data_to.node_groups = data_from.node_groups
            for part in ['RIG_FaceBone', 'RIG_FingerRotL', 'RIG_FingerRotR', 'RIG_FootL', 'RIG_FootR', 'RIG_Forearm',
                         'RIG_Hand', 'RIG_Hips', 'RIG_Index', 'RIG_JawBone', 'RIG_MetacarpalTweak', 'RIG_Shoulder',
                         'RIG_Thumb', 'RIG_Tweak', 'RIG_EyeTrackInd', 'RIG_EyeTrackMid', 'RIG_Root', 'RIG_Toe',
                         'RIG_Torso']:
                if not bpy.data.objects.get(part):
                    data_to.objects = data_from.objects

    @staticmethod
    def ImportAnim(path: str, skeleton: bpy.types.Armature) -> bool:
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
    def MergeSkeletons(skeletons) -> bpy.types.Armature:
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

        return MasterSkeleton

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

    @staticmethod
    def FindOccurance(expr, target, default=None):
        if not target:
            return None
        return next(filter(expr, target), None)

    BasicMap = {
        # Name, Shader Idx, Graph Pos
        "TexMap": [
            ("Diffuse", 0, [-300, -75]),
            ("Diffuse Texture with Alpha Mask", 0, [-300, -75]),
            ("Diffuse Map", 0, [-300, -75]),

            ("M", 1, [-300, -125]),
            ("Texture Masks", 1, [-300, -125]),

            ("SpecularMasks", 4, [-300, -175]),
            ("Specular Map", 4, [-300, -175]),

            ("Normals", 5, [-300, -225]),
            ("Normal Map", 5, [-300, -225]),

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
            ("Diffuse Map", 0, [-300, -75]),

            ("M", 1, [-300, -125]),
            ("Texture Masks", 1, [-300, -125]),

            ("SpecularMasks", 8, [-300, -175]),
            ("Specular Map", 8, [-300, -175]),

            ("Normals", 11, [-300, -225]),
            ("Normal Map", 11, [-300, -225]),

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

    VertexColorMap = {
        "Hide Element 01": 1,
        "Hide Element 1_5": 2,
        "Hide Element 02": 3,
        "Hide Element 2_5": 4,
        "Hide Element 03": 5,
        "Hide Element 3_5": 6,
        "Hide Element 04": 7,
        "Hide Element 4_5": 8,
        "Hide Element 05": 9,
        "Hide Element 5_5": 10,
        "Hide Element 06": 11,
        "Hide Element 6_5": 12,
        "Hide Element 07": 13,
        "Hide Element 7_5": 14,
        "Hide Element 08": 15,
        "Hide Element 8_5": 16,
        "Hide Element 09": 17,
        "Hide Element 9_5": 18,
        "Hide Element 10": 19,
        "Hide Element 10_5": 20,
    }

    @staticmethod
    def ImportMaterial(Target, Data, MatName, Mesh=None):
        Target: bpy.types.Material
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
            else:
                if SubsurfaceInfo := Data.get("SubsurfaceInfo"):
                    Color = SubsurfaceInfo.get("color")
                    Shader.inputs[4].default_value = (Color["R"], Color["G"], Color["B"], 1)
        elif Settings.ShaderType == 'Advanced':
            TargetShaderMap = FPUtils.AdvancedMap

        def TextureParam(Param):
            NodeInfo = FPUtils.FindOccurance(lambda x: x[0] == Param.get("Info"), TargetShaderMap["TexMap"])
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
            NodeInfo = FPUtils.FindOccurance(lambda x: x[0] == Param.get("Info"), TargetShaderMap["NumMap"])
            if not NodeInfo:
                return

            Shader.inputs[NodeInfo[1]].default_value = Param.get("Value")

        def VectorParam(Param):
            NodeInfo = FPUtils.FindOccurance(lambda x: x[0] == Param.get("Info"), TargetShaderMap["VecMap"])
            if not NodeInfo:
                return

            Vector = Param.get("Value")
            Shader.inputs[NodeInfo[1]].default_value = (Vector["R"], Vector["G"], Vector["B"], 1)
            if len(NodeInfo) > 2 and NodeInfo[2]:  # Where to use alpha channel
                Shader.inputs[NodeInfo[2]].default_value = Vector["A"]

        def SwitchParam(Param):
            NodeInfo = FPUtils.FindOccurance(lambda x: x[0] == Param.get("Info"), TargetShaderMap["SwitchMap"])
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

        UseCroppedEmissive = FPUtils.FindOccurance(
            lambda x: x.get("Info") == "CroppedEmissive", SwitchParams)
        CroppedEmissivePositions = FPUtils.FindOccurance(
            lambda x: x.get("Info") == "EmissiveUVs_RG_UpperLeftCorner_BA_LowerRightCorner", VectorParams)

        if UseCroppedEmissive and CroppedEmissivePositions:
            EmissiveData = FPUtils.FindOccurance(lambda x: x[0] == "Emissive", TargetShaderMap["TexMap"])
            EmissiveNode = Shader.inputs[EmissiveData[1]].links[0].from_node
            EmissiveNode.extension = 'CLIP'
            Data = CroppedEmissivePositions.get("Value")

            EmissiveShader = nodes.new("ShaderNodeGroup")
            EmissiveShader.node_tree = bpy.data.node_groups.get("FP Cropped Emissive")
            EmissiveShader.location = [EmissiveData[2][0]-200, EmissiveData[2][1]+25]
            EmissiveShader.inputs[0].default_value = Data.get('R')
            EmissiveShader.inputs[1].default_value = Data.get('G')
            EmissiveShader.inputs[2].default_value = Data.get('B')
            EmissiveShader.inputs[3].default_value = Data.get('A')
            links.new(EmissiveShader.outputs[0], EmissiveNode.inputs[0])

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

    @staticmethod
    def CheckIKDeps():
        if Settings.IKRig:
            FPUtils.ReorientBefore = Settings.ReorientedBones
            Settings.ReorientedBones = True
            FPUtils.MergeBefore = Settings.MergeSkeletons
            Settings.MergeSkeletons = True
        else:
            Settings.ReorientedBones = FPUtils.ReorientBefore
            Settings.MergeSkeletons = FPUtils.MergeBefore

    # to revert when unticking ik option
    MergeBefore = False
    ReorientBefore = False

    @staticmethod
    def TastyRig(MasterSkeleton: bpy.types.Armature):
        IKGroup = MasterSkeleton.pose.bone_groups.new(name='IKGroup')
        IKGroup.color_set = 'THEME01'
        PoleGroup = MasterSkeleton.pose.bone_groups.new(name='PoleGroup')
        PoleGroup.color_set = 'THEME06'
        TwistGroup = MasterSkeleton.pose.bone_groups.new(name='TwistGroup')
        TwistGroup.color_set = 'THEME09'
        FaceGroup = MasterSkeleton.pose.bone_groups.new(name='FaceGroup')
        FaceGroup.color_set = 'THEME01'
        DynGroup = MasterSkeleton.pose.bone_groups.new(name='DynGroup')
        DynGroup.color_set = 'THEME07'
        ExtraGroup = MasterSkeleton.pose.bone_groups.new(name='ExtraGroup')
        ExtraGroup.color_set = 'THEME10'

        bpy.ops.object.mode_set(mode='EDIT')
        EditBones = MasterSkeleton.data.edit_bones
        # Name, Head, Tail, Roll
        NewBonesMap = [
            ('hand_ik_r', EditBones.get('hand_r').head, EditBones.get('hand_r').tail,
             EditBones.get('hand_r').roll),
            ('hand_ik_l', EditBones.get('hand_l').head, EditBones.get('hand_l').tail,
             EditBones.get('hand_l').roll),
            ('foot_ik_r', EditBones.get('foot_r').head, EditBones.get('foot_r').tail,
             EditBones.get('foot_r').roll),
            ('foot_ik_l', EditBones.get('foot_l').head, EditBones.get('foot_l').tail,
             EditBones.get('foot_l').roll),
            ('pole_elbow_r', EditBones.get('lowerarm_r').head + Vector((0, 0.5, 0)),
             EditBones.get('lowerarm_r').head + Vector((0, 0.5, -0.05)), 0),
            ('pole_elbow_l', EditBones.get('lowerarm_l').head + Vector((0, 0.5, 0)),
             EditBones.get('lowerarm_l').head + Vector((0, 0.5, -0.05)), 0),
            ('pole_knee_r', EditBones.get('calf_r').head + Vector((0, -0.75, 0)),
             EditBones.get('calf_r').head + Vector((0, -0.75, -0.05)), 0),
            ('pole_knee_l', EditBones.get('calf_l').head + Vector((0, -0.75, 0)),
             EditBones.get('calf_l').head + Vector((0, -0.75, -0.05)), 0),
            ('index_control_l', EditBones.get('index_01_l').head, EditBones.get('index_01_l').tail,
             EditBones.get('index_01_l').roll),
            ('middle_control_l', EditBones.get('middle_01_l').head, EditBones.get('middle_01_l').tail,
             EditBones.get('middle_01_l').roll),
            ('ring_control_l', EditBones.get('ring_01_l').head, EditBones.get('ring_01_l').tail,
             EditBones.get('ring_01_l').roll),
            ('pinky_control_l', EditBones.get('pinky_01_l').head, EditBones.get('pinky_01_l').tail,
             EditBones.get('pinky_01_l').roll),
            ('index_control_r', EditBones.get('index_01_r').head, EditBones.get('index_01_r').tail,
             EditBones.get('index_01_r').roll),
            ('middle_control_r', EditBones.get('middle_01_r').head, EditBones.get('middle_01_r').tail,
             EditBones.get('middle_01_r').roll),
            ('ring_control_r', EditBones.get('ring_01_r').head, EditBones.get('ring_01_r').tail,
             EditBones.get('ring_01_r').roll),
            ('pinky_control_r', EditBones.get('pinky_01_r').head, EditBones.get('pinky_01_r').tail,
             EditBones.get('pinky_01_r').roll),
            ('eye_control_mid', EditBones.get('head').head + Vector((0, -0.675, 0)),
             EditBones.get('head').head + Vector((0, -0.7, 0)), 0),

        ]

        for BoneInfo in NewBonesMap:
            EditBone: bpy.types.EditBone = EditBones.new(BoneInfo[0])
            EditBone.head = BoneInfo[1]
            EditBone.tail = BoneInfo[2]
            EditBone.roll = BoneInfo[3]
            EditBone.parent = EditBones.get('root')
            if BoneInfo[0] == 'eye_control_mid':
                NewBonesMap.append(('eye_control_r', EditBones.get('eye_control_mid').head + Vector((0.0325, 0, 0)),
                                    EditBones.get('eye_control_mid').tail + Vector((0.0325, 0, 0)), 0))
                NewBonesMap.append(('eye_control_l', EditBones.get('eye_control_mid').head + Vector((-0.0325, 0, 0)),
                                    EditBones.get('eye_control_mid').tail + Vector((-0.0325, 0, 0)), 0))

        TailHeadMoves = [
            ('upperarm_r', 'lowerarm_r'),
            ('upperarm_l', 'lowerarm_l'),
            ('lowerarm_r', 'hand_r'),
            ('lowerarm_l', 'hand_l'),

            ('thigh_r', 'calf_r'),
            ('thigh_l', 'calf_l'),
            ('calf_r', 'foot_ik_r'),
            ('calf_l', 'foot_ik_l'),
        ]

        for Bone in TailHeadMoves:
            if (EditBone := EditBones.get(Bone[0])) and (TargetBone := EditBones.get(Bone[1])):
                EditBone.tail = TargetBone.head

        HeadHeadMoves = [
            ('L_eye_lid_upper_mid', 'L_eye'),
            ('L_eye_lid_lower_mid', 'L_eye'),
            ('R_eye_lid_upper_mid', 'R_eye'),
            ('R_eye_lid_lower_mid', 'R_eye'),
        ]

        for Bone in HeadHeadMoves:
            if (EditBone := EditBones.get(Bone[0])) and (TargetBone := EditBones.get(Bone[1])):
                EditBone.head = TargetBone.head

        RemoveBones = ['attach', 'ik_hand_gun', 'ik_hand_r', 'ik_hand_l', 'weapon_r', 'weapon_l',
                       'ik_hand_root',
                       'ik_foot_root', 'ik_foot_r', 'ik_foot_l', 'dyn_simspace']
        for Bone in RemoveBones:
            if RemoveEditBone := EditBones.get(Bone):
                EditBones.remove(RemoveEditBone)

        if Jaw := EditBones.get('C_jaw'):
            Jaw.roll = 0

        MatrixTransformBones = ['index_control_l', 'middle_control_l', 'ring_control_l', 'pinky_control_l',
                                'index_control_r', 'middle_control_r', 'ring_control_r', 'pinky_control_r']
        for Bone in MatrixTransformBones:
            if EditBone := EditBones.get(Bone):
                EditBone.matrix @= Matrix.Translation(Vector((0.025, 0.0, 0.0)))
                EditBone.parent = EditBones.get(Bone.replace("control", "metacarpal"))

        EditBones.get('eye_control_r').parent = EditBones.get('eye_control_mid')
        EditBones.get('eye_control_l').parent = EditBones.get('eye_control_mid')

        bpy.ops.object.mode_set(mode='OBJECT')
        PoseBones = MasterSkeleton.pose.bones
        # Target, Object, Scale, Group (Optional), Rot (Optional)
        SpecialMap = [
            ('root', 'RIG_Root', 0.75),
            ('pelvis', 'RIG_Torso', 3.0, None, (0, -90, 0)),
            ('spine_01', 'RIG_Hips', 2.1),
            ('spine_02', 'RIG_Hips', 1.8),
            ('spine_03', 'RIG_Hips', 1.6),
            ('spine_04', 'RIG_Hips', 1.8),
            ('spine_05', 'RIG_Hips', 1.2),
            ('neck_01', 'RIG_Hips', 1.0),
            ('neck_02', 'RIG_Hips', 1.0),
            ('head', 'RIG_Hips', 1.6),

            ('clavicle_r', 'RIG_Shoulder', 1.0),
            ('clavicle_l', 'RIG_Shoulder', 1.0),

            ('upperarm_twist_01_r', 'RIG_Forearm', .13, TwistGroup),
            ('upperarm_twist_02_r', 'RIG_Forearm', .1, TwistGroup),
            ('lowerarm_twist_01_r', 'RIG_Forearm', .13, TwistGroup),
            ('lowerarm_twist_02_r', 'RIG_Forearm', .13, TwistGroup),
            ('upperarm_twist_01_l', 'RIG_Forearm', .13, TwistGroup),
            ('upperarm_twist_02_l', 'RIG_Forearm', .1, TwistGroup),
            ('lowerarm_twist_01_l', 'RIG_Forearm', .13, TwistGroup),
            ('lowerarm_twist_02_l', 'RIG_Forearm', .13, TwistGroup),

            ('thigh_twist_01_r', 'RIG_Tweak', .15, TwistGroup),
            ('calf_twist_01_r', 'RIG_Tweak', .13, TwistGroup),
            ('calf_twist_02_r', 'RIG_Tweak', .2, TwistGroup),
            ('thigh_twist_01_l', 'RIG_Tweak', .15, TwistGroup),
            ('calf_twist_01_l', 'RIG_Tweak', .13, TwistGroup),
            ('calf_twist_02_l', 'RIG_Tweak', .2, TwistGroup),

            ('hand_ik_r', 'RIG_Hand', 2.6, IKGroup),
            ('hand_ik_l', 'RIG_Hand', 2.6, IKGroup),

            ('foot_ik_r', 'RIG_FootR', 1.0, IKGroup),
            ('foot_ik_l', 'RIG_FootL', 1.0, IKGroup, (0, -90, 0)),

            ('thumb_01_l', 'RIG_Thumb', 1.0),
            ('thumb_02_l', 'RIG_Hips', 0.7),
            ('thumb_03_l', 'RIG_Thumb', 1.0),
            ('index_metacarpal_l', 'RIG_MetacarpalTweak', 0.3),
            ('index_01_l', 'RIG_Index', 1.0),
            ('index_02_l', 'RIG_Index', 1.3),
            ('index_03_l', 'RIG_Index', 0.7),
            ('middle_metacarpal_l', 'RIG_MetacarpalTweak', 0.3),
            ('middle_01_l', 'RIG_Index', 1.0),
            ('middle_02_l', 'RIG_Index', 1.3),
            ('middle_03_l', 'RIG_Index', 0.7),
            ('ring_metacarpal_l', 'RIG_MetacarpalTweak', 0.3),
            ('ring_01_l', 'RIG_Index', 1.0),
            ('ring_02_l', 'RIG_Index', 1.3),
            ('ring_03_l', 'RIG_Index', 0.7),
            ('pinky_metacarpal_l', 'RIG_MetacarpalTweak', 0.3),
            ('pinky_01_l', 'RIG_Index', 1.0),
            ('pinky_02_l', 'RIG_Index', 1.3),
            ('pinky_03_l', 'RIG_Index', 0.7),

            ('thumb_01_r', 'RIG_Thumb', 1.0),
            ('thumb_02_r', 'RIG_Hips', 0.7),
            ('thumb_03_r', 'RIG_Thumb', 1.0),
            ('index_metacarpal_r', 'RIG_MetacarpalTweak', 0.3),
            ('index_01_r', 'RIG_Index', 1.0),
            ('index_02_r', 'RIG_Index', 1.3),
            ('index_03_r', 'RIG_Index', 0.7),
            ('middle_metacarpal_r', 'RIG_MetacarpalTweak', 0.3),
            ('middle_01_r', 'RIG_Index', 1.0),
            ('middle_02_r', 'RIG_Index', 1.3),
            ('middle_03_r', 'RIG_Index', 0.7),
            ('ring_metacarpal_r', 'RIG_MetacarpalTweak', 0.3),
            ('ring_01_r', 'RIG_Index', 1.0),
            ('ring_02_r', 'RIG_Index', 1.3),
            ('ring_03_r', 'RIG_Index', 0.7),
            ('pinky_metacarpal_r', 'RIG_MetacarpalTweak', 0.3),
            ('pinky_01_r', 'RIG_Index', 1.0),
            ('pinky_02_r', 'RIG_Index', 1.3),
            ('pinky_03_r', 'RIG_Index', 0.7),

            ('ball_r', 'RIG_Toe', 2.1),
            ('ball_l', 'RIG_Toe', 2.1),

            ('pole_elbow_r', 'RIG_Tweak', 2.0, PoleGroup),
            ('pole_elbow_l', 'RIG_Tweak', 2.0, PoleGroup),
            ('pole_knee_r', 'RIG_Tweak', 2.0, PoleGroup),
            ('pole_knee_l', 'RIG_Tweak', 2.0, PoleGroup),

            ('index_control_l', 'RIG_FingerRotR', 1.0, ExtraGroup),
            ('middle_control_l', 'RIG_FingerRotR', 1.0, ExtraGroup),
            ('ring_control_l', 'RIG_FingerRotR', 1.0, ExtraGroup),
            ('pinky_control_l', 'RIG_FingerRotR', 1.0, ExtraGroup),
            ('index_control_r', 'RIG_FingerRotR', 1.0, ExtraGroup),
            ('middle_control_r', 'RIG_FingerRotR', 1.0, ExtraGroup),
            ('ring_control_r', 'RIG_FingerRotR', 1.0, ExtraGroup),
            ('pinky_control_r', 'RIG_FingerRotR', 1.0, ExtraGroup),

            ('eye_control_mid', 'RIG_EyeTrackMid', 0.75, ExtraGroup),
            ('eye_control_r', 'RIG_EyeTrackInd', 0.75, ExtraGroup),
            ('eye_control_l', 'RIG_EyeTrackInd', 0.75, ExtraGroup),

        ]

        for Item in SpecialMap:
            if PoseBone := PoseBones.get(Item[0]):
                PoseBone.custom_shape = bpy.data.objects.get(Item[1])
                PoseBone.custom_shape_scale_xyz = Item[2], Item[2], Item[2]
                if len(Item) > 3 and Item[3]:
                    PoseBone.bone_group = Item[3]
                else:
                    PoseBone.bone_group = ExtraGroup
                if len(Item) > 4 and Item[4]:
                    PoseBone.custom_shape_rotation_euler = radians(Item[4][0]), radians(Item[4][1]), radians(
                        Item[4][2])

                if 'twist' in PoseBone.name:
                    PoseBone.use_custom_shape_bone_size = False
                if 'eye_control_' in PoseBone.name:
                    PoseBone.use_custom_shape_bone_size = False
                if PoseBone.name == 'root':
                    PoseBone.use_custom_shape_bone_size = False

        for Bone in PoseBones:
            if not Bone.parent:
                continue

            if 'dyn_' in Bone.name:
                Bone.bone_group = DynGroup

            if 'deform_' in Bone.name and Bone.bone_group_index != 0:
                Bone.custom_shape = bpy.data.objects.get('RIG_Tweak')
                Bone.custom_shape_scale_xyz = 0.5, 0.5, 0.5
                Bone.bone_group = DynGroup

            if Bone.name == 'faceAttach':
                Bone.bone_group = FaceGroup
                continue

            if Bone.parent.name != 'faceAttach' and Bone.parent.name != 'C_jaw':
                continue

            if 'eye_lid_' in Bone.name:
                Bone.bone_group = FaceGroup
                continue

            if Bone.name == 'C_jaw':
                Bone.bone_group = FaceGroup
                Bone.custom_shape = bpy.data.objects.get('RIG_JawBone')
                Bone.custom_shape_scale_xyz = 1.5, 1.5, 1.5
            elif Bone.name in ['teeth_upper', 'teeth_lower', 'tongue']:
                Bone.bone_group = FaceGroup
            elif Bone.name in ['R_eye', 'L_eye']:
                Bone.bone_group = MasterSkeleton.pose.bone_groups[0]
            else:
                Bone.bone_group = FaceGroup
                Bone.custom_shape = bpy.data.objects.get('RIG_FaceBone')
                if "cheek" in Bone.name:
                    Bone.custom_shape_scale_xyz = 2.0, 2.0, 2.0

        RotCopyBones = [
            ('hand_r', 'hand_ik_r', 1.0),
            ('hand_l', 'hand_ik_l', 1.0),
            ('foot_r', 'foot_ik_r', 1.0),
            ('foot_l', 'foot_ik_l', 1.0),

            ('L_eye_lid_upper_mid', 'L_eye', 0.25),
            ('L_eye_lid_lower_mid', 'L_eye', 0.25),
            ('R_eye_lid_upper_mid', 'R_eye', 0.25),
            ('R_eye_lid_lower_mid', 'R_eye', 0.25),

            ('index_01_l', 'index_control_l', 1.0),
            ('index_02_l', 'index_control_l', 1.0),
            ('index_03_l', 'index_control_l', 1.0),
            ('middle_01_l', 'middle_control_l', 1.0),
            ('middle_02_l', 'middle_control_l', 1.0),
            ('middle_03_l', 'middle_control_l', 1.0),
            ('ring_01_l', 'ring_control_l', 1.0),
            ('ring_02_l', 'ring_control_l', 1.0),
            ('ring_03_l', 'ring_control_l', 1.0),
            ('pinky_01_l', 'pinky_control_l', 1.0),
            ('pinky_02_l', 'pinky_control_l', 1.0),
            ('pinky_03_l', 'pinky_control_l', 1.0),

            ('index_01_r', 'index_control_r', 1.0),
            ('index_02_r', 'index_control_r', 1.0),
            ('index_03_r', 'index_control_r', 1.0),
            ('middle_01_r', 'middle_control_r', 1.0),
            ('middle_02_r', 'middle_control_r', 1.0),
            ('middle_03_r', 'middle_control_r', 1.0),
            ('ring_01_r', 'ring_control_r', 1.0),
            ('ring_02_r', 'ring_control_r', 1.0),
            ('ring_03_r', 'ring_control_r', 1.0),
            ('pinky_01_r', 'pinky_control_r', 1.0),
            ('pinky_02_r', 'pinky_control_r', 1.0),
            ('pinky_03_r', 'pinky_control_r', 1.0),
        ]

        for Bone in RotCopyBones:
            if PoseBone := PoseBones.get(Bone[0]):
                con = PoseBone.constraints.new('COPY_ROTATION')
                con.target = MasterSkeleton
                con.subtarget = Bone[1]
                con.influence = Bone[2]
                if 'hand_ik' in Bone[1] or 'foot_ik' in Bone[1]:
                    con.target_space = 'WORLD'
                    con.owner_space = 'WORLD'
                elif 'control' in Bone[1]:
                    con.mix_mode = 'OFFSET'
                    con.target_space = 'LOCAL_OWNER_ORIENT'
                    con.owner_space = 'LOCAL'
                else:
                    con.target_space = 'LOCAL_OWNER_ORIENT'
                    con.owner_space = 'LOCAL'

        IKBones = [
            ('lowerarm_r', 'hand_ik_r', 'pole_elbow_r'),
            ('lowerarm_l', 'hand_ik_l', 'pole_elbow_l'),
            ('calf_r', 'foot_ik_r', 'pole_knee_r'),
            ('calf_l', 'foot_ik_l', 'pole_knee_l'),
        ]

        for Bone in IKBones:
            con = PoseBones.get(Bone[0]).constraints.new('IK')
            con.target = MasterSkeleton
            con.subtarget = Bone[1]
            con.pole_target = MasterSkeleton
            con.pole_subtarget = Bone[2]
            con.pole_angle = radians(180)
            con.chain_count = 2

        TrackBones = [
            ('R_eye', 'eye_control_r', 0),
            ('L_eye', 'eye_control_l', 0),
            ('eye_control_mid', 'head', 0.285)
        ]
        for Bone in TrackBones:
            if PoseBone := PoseBones.get(Bone[0]):
                con = PoseBone.constraints.new('TRACK_TO')
                con.target = MasterSkeleton
                con.subtarget = Bone[1]
                con.head_tail = Bone[2]
                con.track_axis = 'TRACK_Y'
                con.up_axis = 'UP_Z'

        Bones = MasterSkeleton.data.bones
        for Bone in ['hand_r', 'hand_l', 'foot_r', 'foot_l', 'faceAttach']:
            if Bone := Bones.get(Bone):
                Bone.hide = True

        Bones.get('spine_01').use_inherit_rotation = False
        Bones.get('neck_01').use_inherit_rotation = False

        BoneGroups = {
            'IKGroup': 1,
            'PoleGroup': 1,
            'TwistGroup': 2,
            'DynGroup': 3,
            'FaceGroup': 4,
            'ExtraGroup': 1
        }
        LayerOneBones = ['upperarm_r', 'lowerarm_r', 'upperarm_l', 'lowerarm_l', 'thigh_r', 'calf_r', 'thigh_l',
                         'calf_l', 'clavicle_r', 'clavicle_l', 'ball_r', 'ball_l', 'pelvis', 'spine_01',
                         'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01', 'neck_02', 'head', 'root']
        for Bone in Bones:
            if Bone.name in LayerOneBones:
                Bone.layers[1] = True
                continue
            if Bone.name in ['R_eye', 'L_eye', 'eye_control_mid', 'eye_control_r', 'eye_control_l']:
                Bone.layers[4] = True
                continue
            if Group := PoseBones.get(Bone.name).bone_group:
                if Group.name in ['Unused bones', 'No children']:
                    continue
                Index = BoneGroups[Group.name]
                Bone.layers[Index] = True


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
        TastyRow = box.row()
        TastyRow.prop(Settings, "IKRig")
        TastyRow.operator("fp.tasty", icon='URL')
        MergeRow = box.row()
        MergeRow.prop(Settings, "MergeSkeletons")
        ReorientRow = box.row()
        ReorientRow.prop(Settings, "ReorientedBones")
        if Settings.IKRig:
            MergeRow.enabled = False
            ReorientRow.enabled = False
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
        if Settings.ExportType == 'Character':
            box.row().prop(Settings, "CharacterType", expand=True)
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
    CharacterType: EnumProperty(name="Character Type", items=FPEnums.CharacterType, default='Battle Royale')
    ExportString: StringProperty(name="")

    # Import
    MergeSkeletons: BoolProperty(name="Merge Skeletons")
    ReorientedBones: BoolProperty(name="Reorient Bones")
    IKRig: BoolProperty(name="Use Tasty™ Rig", update=lambda s, c: FPUtils.CheckIKDeps())
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
    bl_context = 'scene'

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
            return

        FPUtils.CheckAppendData()
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

        # disgusting nested code i apologize
        if VariantParams := Processed.get("variantParameters"):
            for Part in Processed.get("baseStyle"):
                for Material in Part.get("materials"):
                    for ParamSet in VariantParams:
                        if ParamSet.get("materialToAlter") != Material.get("matPath"):
                            continue
                        Params = Material.get("matParameters")
                        for Texture in ParamSet.get("TextureParameters"):
                            Info = next(
                                filter(lambda x: x.get("Info") == Texture.get("Info"), Params.get("TextureParameters")),
                                None)
                            if Info:
                                Info["Value"] = Texture.get("Value")
                                continue
                            Params.get("TextureParameters").append({
                                "Info": Texture.get("Info"),
                                "Value": Texture.get("Value")
                            })
                        for Float in ParamSet.get("ScalarParameters"):
                            Info = next(
                                filter(lambda x: x.get("Info") == Float.get("Info"), Params.get("ScalarParameters")),
                                None)
                            if Info:
                                Info["Value"] = Float.get("Value")
                                continue
                            Params.get("ScalarParameters").append({
                                "Info": Float.get("Info"),
                                "Value": Float.get("Value")
                            })

                        for Color in ParamSet.get("VectorParameters"):
                            Info = next(
                                filter(lambda x: x.get("Info") == Color.get("Info"), Params.get("VectorParameters")),
                                None)
                            if Info:
                                Info["Value"] = Color.get("Value")
                                continue
                            Params.get("VectorParameters").append({
                                "Info": Color.get("Info"),
                                "Value": Color.get("Value")
                            })

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
                if not bpy.data.materials.get("MaterialToSwap"):
                    continue
                bpy.data.materials[MaterialToSwap].name = OverrideMaterialName
                FPUtils.ImportMaterial(bpy.data.materials[MaterialToSwap], StyleMaterial.get("matParameters"),
                                       OverrideMaterialName)

        if Type != 'Character':
            return

        MasterSkeleton: bpy.types.Object
        if Settings.MergeSkeletons:
            MasterSkeleton = FPUtils.MergeSkeletons(ImportedSlots)

        if Settings.IKRig and Type == 'Character':
            FPUtils.TastyRig(MasterSkeleton)

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
        ExportType = Settings.ExportType.lower()
        if ExportType == 'character':
            ExportType += "br" if Settings.CharacterType == 'Battle Royale' else "stw"

        os.system(f'start FortnitePorting -{ExportType} "{Settings.ExportString}"')


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


class FPTasty(Operator):
    bl_idname = "fp.tasty"
    bl_label = "Credit to Ta5tyy2"

    def execute(self, context):
        os.system("start https://twitter.com/Ta5tyy2")
        return {'FINISHED'}


Operators = [FPPanel, FPSettings, FPImport, FPExport, FPFill, FPCheckUpdate, FPUpdate, FPTasty]


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
