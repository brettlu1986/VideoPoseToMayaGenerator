#ImportAiMotionWithUI

'''
1.ѡ�йؽڣ�Ŀǰ֧�ֵ��ǹؽڶ�����������Ƥ������������UI, ��Ӷ��������ļ��У� ����Remap���������� ���µ���Import
2.��Timer, ��鵱ǰ���ض������ȣ� ����ÿ30֡���ݣ�һ֡һ���ļ�������һ�Σ����õȴ�ʱ��������ʱ��Ĭ�϶���������ϡ�ֹͣTimer
3.����һ֡�Ķ�������
4.д�ؼ�֡����

Pseudocode:

RemapSkeletonParam()
CreateImportUI()
StartLoadTimer()
LoadFrameMotionData()
WriteToKeyAttriButeFrame()

TODO:
1. ������Ҫ��ѡ�йؽ�root, ��ѡ�е���ʾ�жϷŵ�ǰ����
2.���һ�� reset�У� ���� reset��ԭʼ��t-pose
3.��� pose-3d�е� ����� apply

���ھ������
 #matrix test
    Transform = cmds.xform('pelvis', objectSpace=True, query=True, matrix=True)
    #��ѯ translate rotate scale  relative��
    #Translate = cmds.xform('pelvis', objectSpace=True, query=True, translation=True)
    #Rotate = cmds.xform('pelvis', objectSpace=True, query=True, rotation=True)
    #Scale = cmds.xform('pelvis', objectSpace=True, query=True, scale=True)
    
    #�������, Transform��������� �������� �������Ϊ�ҳ�
    Matrix_Root = MMatrix(Transform)
    #�������
    Matrix_Root_Inverse = Matrix_Root.inverse()
    
    #���ݾ�����ŷ����
    TransformationMatrix = OM.MTransformationMatrix(Matrix_Root)
    #Ĭ�ϰ� kxyz��˳�򷵻�  type is MEulerRotation 
    Euler_Rad = TransformationMatrix.rotation()
    #����Ƕȶ�Ӧ ���� xform��ȡ�ó��� Rotate
    RotateValue = [math.degrees(angle) for angle in (Euler_Rad.x, Euler_Rad.y, Euler_Rad.z)]
    #��ȡtranslation��Ҫ ���� OpenMaya.MSpace �ռ���Ϊ����
    #kPostTransform = 3 kPreTransform = 2 kTransform = 1 kWorld = 4
    #��3�� �ǰ��մ���ķ��أ���Ӧ���� xform ��translate�� type is MVector
    TranslateValue = TransformationMatrix.translation(OM.MSpace.kPostTransform)
    #scale����ͬ�� xform scale �Ǹ�����[sx, sy , sz]
    Scale = TransformationMatrix.scale(OM.MSpace.kPostTransform)

    #���� translate rot scale ����matrix
    TransformationMatrix = OM.MTransformationMatrix()
    Translate = OM.MVector(InputTranslate[0], InputTranslate[1],InputTranslate[2])
    TransformationMatrix.setTranslation(Translate, OM.MSpace.kTransform)
    #�ص� ע������ InputRotate �ǻ���  ��Ҫ math.radians()ת��һ��
    TransformationMatrix.setRotation(OM.MEulerRotation(InputRotate[0], InputRotate[1], InputRotate[2]))
    TransformationMatrix.setScale([InputScale[0], InputScale[1], InputScale[2]], OM.MSpace.kTransform)
    #��������� matrix
    NewMatrix = TransformationMatrix.asMatrix() 
    #���Կ������������֤NewMatrix��� ��һ�µ�

'''

import maya.cmds as cmds
import maya.mel as mel
import functools
import json
import numpy as np

import math
import maya.api.OpenMaya as OM
from maya.api.OpenMaya import MVector, MMatrix, MPoint

#Config 
ErrorMsgTypeStr = {
    'SelectTypeWrong' : 'Current Selection in Outliner should be the jonit root.',
    'FileNotNull' : 'Dir or File path should not be null.',
    'LoadDefaultT-PoseError' : 'To Load T-Pose, we must select root joint and load T-Pose first',
    'WrongJointFormat' : 'Pose3d joint index map to skeletal joint name fail',
    'ShouldSameSize': 'Current Joints Size should same as Parent Joints Size.',
    'ShouldHaveFormatName' : 'Should Have Format Name'
}

JointIndexToName = {
        0:'pelvis',
        1:'thigh_r',
        2:'calf_r',
        3:'foot_r',
        4:'thigh_l',    
        5:'calf_l',
        6:'foot_l',
        7:'spine_02',
        8:'spine_03',
        9:'neck_01',
        10:'head',
        11:'upperarm_l',
        12:'lowerarm_l',
        13:'hand_l',
        14:'upperarm_r',
        15:'lowerarm_r',
        16:'hand_r'
}

#Variables
WindowId = 'ImportAnimUI'
WindowTitle = 'ImportAnimUI'

NanStr = 'Nan'

#Path EditWidth
EditFieldWidth=400

SelectTargetRoot = None
StartFrame = 0
EndFrame = 0

CurrentJoints = []  #root�£� ��ǰ������� root��child�ռ�transform�����нڵ�
CurrentJointsParent = [] #��CurrentJointsһһ��Ӧ����CurrentJoints�����и��ڵ㣬 None�����Ǹ��ڵ㣬��ӦIndex��-1�� ����Index��CurrentJoints������

CurrentFrameDatas = []#ÿ֡Frameһ֡�Ĺؽ�����

DefaultTPoseFrameData = None

#ͳһ����һ�¹ؽڳ��ȣ� ����pose3d����ͳһ�Ŵ�100�������ݷŴ���λ�öԵ�ǰ�ؽڳ���ͳһ���е�������
Pose3dPoseScale = 100
#��¼��ǰÿ���ؽ���Ҫ �仯����ֵ
Pose3dJointDistance = []

#classes
class JointParent:
    def __init__(self, Joint_Index, Joint_Name, Parent_Name, Parent_Index):
        self.JointIndex = Joint_Index
        self.JointName = Joint_Name
        self.ParentName = Parent_Name
        self.ParentIndex = Parent_Index
        
    def GetJointName(self):
        return self.JointName

    def GetJointIndex(self):
        return self.JointIndex
        
    def GetParentName(self):
        return self.ParentName
        
    def GetParentIndex(self):
        return self.ParentIndex

    def Display(self):
        print 'JointParent: %s, %s, %s, %s' % (self.JointIndex, self.JointName, self.ParentName, self.ParentIndex)

class JointData:
    def __init__(self, Name, Translate, Rotate, Scale):
        self.JointName = Name
        self.Translate = Translate
        self.Rotate = Rotate
        self.Scale = Scale
        
    def GetJointName(self):
        return self.JointName

    def GetTranslate(self):
        return self.Translate 

    def SetTranslate(self, NewTrans):
        self.Translate = NewTrans
        
    def SetRotate(self, NewRotate):
        self.Rotate = NewRotate
    
    def GetRotate(self):
        return self.Rotate  
        
    def GetScale(self):
        return self.Scale
        
    def Display(self):
        print 'JointData: %s, %s, %s, %s' % (self.JointName, self.Translate, self.Rotate, self.Scale)

class FrameData:
    def __init__(self, FrameIndex, JointDatas):
        self.FrameIndex = FrameIndex 
        self.JointDatas = JointDatas
    
    def GetFrameIndex(self):
        return self.FrameIndex
        
    def GetJointDatas(self):
        return self.JointDatas  
        
    def Display(self):
        print 'FrameData: %s' % (self.FrameIndex)
        for key in self.JointDatas:
            Joint = self.JointDatas[key]
            Joint.Display()
        
#functions 
def ErrorMessage(KeyMsg):
    cmds.confirmDialog(title='Error Message', message=ErrorMsgTypeStr[KeyMsg], button=['Ok'])
    print "ErrorMsg: %s" % (ErrorMsgTypeStr[KeyMsg])  
    
#IsJointExist
def IsJointExist(JointName):
    for Name in CurrentJoints:
        if Name == JointName:
            return True
    return False

#ApplyPath
def ApplyDir(pImportField, *pArgs):
    
    Dir = cmds.textField(pImportField, query=True, text=True)
    if not Dir or Dir == '':
        ErrorMessage('FileNotNull')
        return
    #TODO
    print 'Apply Path: %s' % Dir
    LoadFrameMotionDatas()

#ApplyFile
def ApplyFile(pImportField, *pArgs):
    File = cmds.textField(pImportField, query=True, text=True)
    if not File or File == '':
        ErrorMessage('FileNotNull')
        return
    #print 'Apply File: %s' % File 
    LoadAllMotionDatas(File)
    
   
#ImportFromAnimDirPath : ֱ�Ӹ���·����ȥ�����Apply���� Browseѡ��·��
def OpenImportDirDialog(pImportField, *pArgs): 
   Path = cmds.fileDialog2(fileFilter='*.*', dialogStyle=2, fileMode=3, cap='Select Import Path')
   if Path:
       cmds.textField(pImportField, edit=True, text=Path[0])
       #print 'Import From Anim Dir:%s '% (Path)
   
#ImportFromAnimFilePath : ֱ�Ӹ����ļ�·����ȥ�����Apply�� ����Browseѡ��json�ļ�
def OpenImportFileDialog(pImportField, *pArgs):
   Path = cmds.fileDialog2(fileFilter='*.json', dialogStyle=2, fileMode=1, cap='Select Import File')
   if Path:
       cmds.textField(pImportField, edit=True, text=Path[0])
       #print 'Import From Anim File:%s '% (Path)

#Browse to load anim data
def CreateImportUI(pOpenImportDirDialog, pOpenImportFileDialog, pApplyDir, pApplyFile):
    if not CheckSelectTarget():
        return
    
    LoadTargetRootAndJoint()
    LoadTPoseDefaultData()
    
    if cmds.window(WindowId, exists=True):
        cmds.deleteUI(WindowId)
  
       
    cmds.window(WindowId, title=WindowTitle, sizeable=False, width=600, height=113 )
    #cmds.window(WindowId, title=WindowTitle, sizeable=False, resizeToFitChildren=True )
     
    #columnWidth=[ (1,75)..] means subIndex=1 column with is 75
    #the parameters will fill from 1st row to the last row, 
    cmds.rowColumnLayout(numberOfColumns=4, columnWidth=[(1, 80),(2, EditFieldWidth), (3, 80),(4, 80)], columnOffset=[(1, 'right', 3), 
                                                                                                        (2, 'right', 3),
                                                                                                        (3, 'right', 3),
                                                                                                        (4, 'right', 3)])
  
    #anim dir to apply
    cmds.text(label='AnimDir:')
    dirPathField = cmds.textField(text='', width = EditFieldWidth)
    cmds.button(label='DirBrowser', command = functools.partial(pOpenImportDirDialog,
                                                                dirPathField))
    cmds.button(label='ApplyDir', command = functools.partial(pApplyDir,
                                                                dirPathField))
                                                          
    #make a space row
    cmds.separator(h=10, style='none')
    cmds.separator(h=10, style='none')
    cmds.separator(h=10, style='none')
    cmds.separator(h=10, style='none')
                                     
    #anim file to apply                                                                    
    cmds.text(label='AnimFile:')
    filePathField = cmds.textField(text='', width = EditFieldWidth)
    cmds.button(label='FileBrowser', command = functools.partial(pOpenImportFileDialog,
                                                                filePathField))
    cmds.button(label='ApplyFile', command = functools.partial(pApplyFile,
                                                                filePathField))
   
    #make a space row
    cmds.separator(h=10, style='none')
    cmds.separator(h=10, style='none')
    cmds.separator(h=10, style='none')
    cmds.separator(h=10, style='none')
                                                            
    #these code fill the first rows, from left to right
    def cancelCallBack(*pArags):
        if cmds.window(WindowId, exists=True):
            cmds.deleteUI(WindowId)
    cmds.separator(h=10, style='none')
    cmds.button(label='Cancel', command=cancelCallBack)
    
    def resetToDefault(*pArgs):
        ClearKeys()
        ResetCurrentToTPose()
    cmds.button(label='Reset2TPose', command=resetToDefault)
    
    cmds.showWindow()
    
#CheckSelectTarget
def CheckSelectTarget():
    #ȷ��ѡ�е��ǹؽڸ��ڵ�
    TargetRoot = cmds.ls(orderedSelection=True, type='joint')
    if not TargetRoot:
        ErrorMessage('SelectTypeWrong')
        return False
    return True
    
#LoadTargetRootAndJoint
def LoadTargetRootAndJoint():
    #��ȡ���йؽڵ��ڵ���
    #�ؽ��� (ֻ�浱ǰ���еĹؽ�����)
    #FrameArray -> Frame -> ���йؽ�����
    global SelectTargetRoot
    SelectTargetRoot = cmds.ls(orderedSelection=True, type='joint')
    SelectTargetRoot = SelectTargetRoot[0]
   
    global CurrentJoints
    CurrentJoints = []
    CurrentJoints.append(SelectTargetRoot)
        
    def FindJointChild(JointParent):
        Children = cmds.listRelatives(JointParent, children=True, type='joint')
        if Children:
            for Child in Children:
                CurrentJoints.append(Child)
                FindJointChild(Child)
    FindJointChild(SelectTargetRoot)
          
    #find parent    
    global CurrentJointsParent
      
    def FindIndexInCurrentJoints(Name):
        for Index in range(len(CurrentJoints)):
            if Name == CurrentJoints[Index]:
                return Index
        return -1
        
    
    for Index in range(len(CurrentJoints)):
        if Index == 0:
            CurrentJointsParent.append(JointParent(0, CurrentJoints[Index], NanStr, -1))
        else:
            ParentNode = cmds.listRelatives(CurrentJoints[Index], parent=True, type='joint')
            if ParentNode:   
                ParentIndex = FindIndexInCurrentJoints(ParentNode[0])
                CurrentJointsParent.append(JointParent(Index, CurrentJoints[Index], ParentNode[0], ParentIndex))
    
    # print '%s' % CurrentJoints
    # for Parent in CurrentJointsParent:
    #     Parent.Display()
    
    #ObjectType = cmds.objectType(SelectTargetRoot)
    #print "select %s, ObjectType %s" % (SelectTargetRoot, ObjectType)

     
#LoadFrameMotionDatas
def LoadFrameMotionDatas():
    if not CheckSelectTarget():
        return
       
    print 'Load Frame Motion Datas'

           
#ConstructFrameData(JsonFrame)
def ConstructFrameData(JsonFrame):
    JointDatas = {}
    
    FrameJoints = JsonFrame['frameJointsData']
    for i in range(len(FrameJoints)):
        Data = FrameJoints[i]
        Joint = ConstructJointData(Data)
        JointDatas[Joint.GetJointName()] = Joint
        
    Frame = FrameData(JsonFrame['frameIndex'], JointDatas)
    return Frame
   
#ConstructJointData        
def ConstructJointData(JsonJoint):
    Joint = JointData(JsonJoint['jointName'], 
                         [JsonJoint['translate']['x'], JsonJoint['translate']['y'], JsonJoint['translate']['z']],
                         [JsonJoint['rotation']['x'], JsonJoint['rotation']['y'], JsonJoint['rotation']['z']],
                         [JsonJoint['scale']['x'], JsonJoint['scale']['y'], JsonJoint['scale']['z']],
                         )
    return Joint

#GetAllJoints
def GetAllJoints():
    Joints = []
    TargetRoot = cmds.ls(orderedSelection=True, type='joint')
    TargetRoot = TargetRoot[0]
    Joints = cmds.listRelatives(TargetRoot, allDescendents=True, type='joint')
    Joints.append(TargetRoot)
    return Joints 
     
#ClearKeys
def ClearKeys():
    #ɾ����ǰʱ���ߵ���ʼ������֡����
    StartTime = cmds.playbackOptions(query=True, minTime=True)
    EndTime = cmds.playbackOptions(query=True, maxTime=True)
    
    AllJoints = GetAllJoints()
    for JointName in AllJoints:
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='translateX')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='translateY')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='translateZ')
        
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='rotateX')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='rotateY')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='rotateZ')
        
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='scaleX')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='scaleY')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='scaleZ')
        

    cmds.playbackOptions(minTime=StartFrame, maxTime=EndFrame, animationStartTime=StartFrame, animationEndTime=EndFrame)
    

#KeyJointAttribute
def KeyJointAttribute(pObjectName, pKeyFrame, pAttribute, value):    
    cmds.setKeyframe(pObjectName, time=pKeyFrame, attribute=pAttribute, value=value)
    cmds.keyTangent(inTangentType='linear', outTangentType='linear')
         
def KeyJointTranslate(pObjectName, pKeyFrame, Translate):   
    KeyJointAttribute(pObjectName, pKeyFrame, 'translateX', Translate[0])
    KeyJointAttribute(pObjectName, pKeyFrame, 'translateY', Translate[1])
    KeyJointAttribute(pObjectName, pKeyFrame, 'translateZ', Translate[2])

def KeyJointRotate(pObjectName, pKeyFrame, Rotate):
    KeyJointAttribute(pObjectName, pKeyFrame, 'rotateX', Rotate[0])
    KeyJointAttribute(pObjectName, pKeyFrame, 'rotateY', Rotate[1])
    KeyJointAttribute(pObjectName, pKeyFrame, 'rotateZ', Rotate[2])

def KeyJointScale(pObjectName, pKeyFrame, Scale):
    KeyJointAttribute(pObjectName, pKeyFrame, 'scaleX', Scale[0])
    KeyJointAttribute(pObjectName, pKeyFrame, 'scaleY', Scale[1])
    KeyJointAttribute(pObjectName, pKeyFrame, 'scaleZ', Scale[2])
       
#ConstructFrame          
def ConstructFrame(Frame):
    FrameIndex = Frame.GetFrameIndex()  
    JointDatas = Frame.GetJointDatas()
    
    def InAllJoints(JointName):
        AllJoints = GetAllJoints()
        for Joint in AllJoints:
            if Joint == JointName:
                return True
        return False

    for JointName in JointDatas:
    #testArr = ['pelvis','thigh_r', 'calf_r']
    # for Index in range(len(testArr)):
    #     JointName = testArr[Index]
        Joint = None
        if IsJointExist(JointName):
            Joint = JointDatas[JointName]
        elif InAllJoints(JointName):
            Joint = DefaultTPoseFrameData.GetJointDatas()[JointName]

        if Joint:
            KeyJointTranslate(JointName, FrameIndex, Joint.GetTranslate())
            KeyJointRotate(JointName, FrameIndex, Joint.GetRotate())
            KeyJointScale(JointName, FrameIndex, Joint.GetScale())

#LoadAllMotionDatas ����һ��json�ļ�����
def LoadAllMotionDatas(JsonFile):
    if not CheckSelectTarget():
        return 
                
    with open(JsonFile) as f:
        data = json.load(f)
    #print 'Load All Motion Datas %s' % (data)
    global CurrentFrameDatas
    CurrentFrameDatas = []
    
    global StartFrame
    StartFrame = 0
    
    global EndFrame
    EndFrame = data['totalFrames'] - 1
       
    for Index in range(data["totalFrames"]):
        #print "Index::%s and FrameIndex::%s" % (Index, data['animSeqData'][Index])
        FrameData = ConstructFrameData(data['animSeqData'][Index])
        #Frame.Display()
        CurrentFrameDatas.append(FrameData)
    
    ClearKeys()
    for Frame in CurrentFrameDatas:
        ConstructFrame(Frame)
    
    
#LoadTPoseDefaultData
def LoadTPoseDefaultData():
    global DefaultTPoseFrameData
   
    JointDatas = {}
    
    AllJoints = GetAllJoints()
    for i in range(len(AllJoints)):
        JointName = AllJoints[i]
        
        AttrTranslate = cmds.getAttr( '%s.translate' % (JointName))
        AttrRot = cmds.getAttr( '%s.rotate' % (JointName))
        AttScale = cmds.getAttr( '%s.scale' % (JointName))
        Joint = JointData(JointName, 
                         [RoundDown(AttrTranslate[0][0], 3), RoundDown(AttrTranslate[0][1], 3), RoundDown(AttrTranslate[0][2], 3) ],
                         [RoundDown(AttrRot[0][0], 3),       RoundDown(AttrRot[0][1], 3),       RoundDown(AttrRot[0][2], 3) ],
                         [RoundDown(AttScale[0][0], 3),      RoundDown(AttScale[0][1], 3),      RoundDown(AttScale[0][2], 3) ],
                         )
        #Joint.Display()
        JointDatas[JointName] = Joint
        
    DefaultTPoseFrameData = FrameData(-1, JointDatas)

#ResetCurrentToTPose
def ResetCurrentToTPose():
    global DefaultTPoseFrameData
    if not DefaultTPoseFrameData:
        ErrorMessage('LoadDefaultT-PoseError')
        return
    
    AllJoints = GetAllJoints()
    
    DefaultJointsData = DefaultTPoseFrameData.GetJointDatas()
    for i in range(len(AllJoints)):
        JointName = AllJoints[i]
        Joint = DefaultJointsData[JointName]
        Trans = Joint.GetTranslate()
        Rot = Joint.GetRotate()
        Scale = Joint.GetScale()
        cmds.setAttr('%s.translate' % (JointName), Trans[0], Trans[1], Trans[2], type="double3")
        cmds.setAttr('%s.rotate' % (JointName), Rot[0], Rot[1], Rot[2], type="double3")
        cmds.setAttr('%s.scale' % (JointName), Scale[0], Scale[1], Scale[2], type="double3")
 
   
#CreateImportUI(OpenImportDirDialog, OpenImportFileDialog, ApplyDir, ApplyFile)


#Load Pose3d
#GetFormatJointName
def GetFormatJointName(JointIndex):
    if not JointIndexToName.has_key(JointIndex):
        return NanStr
    return JointIndexToName[JointIndex]

def GetPose3dJointIdxToCurrentJointsIdx(JointIndex):
    JointName = GetFormatJointName(JointIndex)
    for i in range(len(CurrentJoints)):
        if JointName == CurrentJoints[i]:
            return i 
    return -1

def LimitAngle(Angle):
    if Angle > 180:
        return Angle - 360 
    elif Angle < -180:   
        return Angle + 360
    return Angle

def RoundHalfUp(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + 0.5) / multiplier


def RoundDown(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier

def RoundUp(n, decimals=0):
    multiplier = 10 ** decimals
    return math.ceil(n * multiplier) / multiplier

def ConvertPos3dAxisValueToMaya(CurPos):
        #curpos ��x, ��y, ��������z, �������ֶ���
        #��Ҫת�� maya�� pelvis����ϵ
        #[0], [1], [2]Ӧ�� [0], -[1], -[2]
        return [CurPos[0] * Pose3dPoseScale, -CurPos[1] * Pose3dPoseScale, -CurPos[2] * Pose3dPoseScale]


def ConstructPose3dFrameData(FrameIndex, Pose3dFrameCurrent):
    JointDatas = {}
   
    Frame = None
    #init to default t-pose first
    DefaultJointDatas = DefaultTPoseFrameData.GetJointDatas()
    for Name in DefaultJointDatas:
        T = DefaultJointDatas[Name].GetTranslate()
        R = DefaultJointDatas[Name].GetRotate()
        S = DefaultJointDatas[Name].GetScale()
        JointDatas[Name] = JointData(Name, [T[0], T[1], T[2]],
                                           [R[0], R[1], R[2]],
                                           [S[0], S[1], S[2]])

    #���޸� ��Ҫ�޸ĵ� �ؼ�֡�� ĿǰĬ�����еĹؼ��ı�ȫ��������ת��ɵ�, ���մ�������ƫ�ƣ������������ת��ҪӦ�õ����ؽڵ���ת���ǶԵ�
    #��Щ�ؽڿ��ܹ���ͬһ�����׽ڵ㣬 ���������׽ڵ��Ѿ����Ĺ��� ��ô�Ͳ��ٸ��� ��ֻ֤��һ��
    DynamicJointToRootTransforms = {}
    for i in range(len(Pose3dFrameCurrent)):
        JointName = GetFormatJointName(i)
        if JointName == NanStr:
            return Frame 

        IndexInCurrentJoints = GetPose3dJointIdxToCurrentJointsIdx(i)
        if IndexInCurrentJoints == -1:
            continue
        
        #ParentIndex ��Ӧ���� CurrentJoints�е��±�
        ParentIndex = CurrentJointsParent[IndexInCurrentJoints].GetParentIndex()
        if ParentIndex == -1:
            continue

        #if JointName == 'spine_02' or JointName == 'spine_03':

        RealJointTranslateFromRoot = ConvertPos3dAxisValueToMaya(Pose3dFrameCurrent[i])
        DefaultTPoseRotate_JointSpace = DefaultJointDatas[JointName].GetRotate()

        #���쵱ǰ�ؽ� ��root�ľ���
        TransformationMatrix_Current = OM.MTransformationMatrix()
        Translate = OM.MVector(RealJointTranslateFromRoot[0], RealJointTranslateFromRoot[1], RealJointTranslateFromRoot[2])
        TransformationMatrix_Current.setTranslation(Translate, OM.MSpace.kTransform)
        
        TransformationMatrix_Current.setScale([1, 1, 1], OM.MSpace.kTransform)

        if ParentIndex == 0:
            TransformationMatrix_Current.setRotation(OM.MEulerRotation(math.radians(DefaultTPoseRotate_JointSpace[0]),
                                                            math.radians(DefaultTPoseRotate_JointSpace[1]),
                                                            math.radians(DefaultTPoseRotate_JointSpace[2])))
            JointDatas[JointName].SetTranslate(RealJointTranslateFromRoot)

            print '%s position: %s' % (JointName, RealJointTranslateFromRoot)
            DynamicJointToRootTransforms[IndexInCurrentJoints] = TransformationMatrix_Current.asMatrix()
        else:
            TransformationMatrix_Current.setRotation(OM.MEulerRotation(math.radians(0),
                                                            math.radians(0),
                                                            math.radians(0)))

            Matrix_Current = TransformationMatrix_Current.asMatrix()
            
            #�ѵ�ǰ�ӹؽ���root������ ת�� ��ǰ�Ĺؽڿռ� ��Ҫ�õ��ı任
            InverseMatrix = DynamicJointToRootTransforms[ParentIndex].inverse()
            ToJointSpaceMatrix = Matrix_Current * InverseMatrix

            TransformationMatrix_JointSpaceCurrent = OM.MTransformationMatrix(ToJointSpaceMatrix)
            JointCurrentTranslate_JointSpace = TransformationMatrix_JointSpaceCurrent.translation(OM.MSpace.kPostTransform)
            JointDatas[JointName].SetTranslate([JointCurrentTranslate_JointSpace.x, JointCurrentTranslate_JointSpace.y, JointCurrentTranslate_JointSpace.z])


            JointSpaceTransformation = OM.MTransformationMatrix()
            JointSpaceTranslate = OM.MVector(JointCurrentTranslate_JointSpace.x, JointCurrentTranslate_JointSpace.y, JointCurrentTranslate_JointSpace.z)
            JointSpaceTransformation.setTranslation(JointSpaceTranslate, OM.MSpace.kTransform)
            JointSpaceTransformation.setRotation(OM.MEulerRotation(math.radians(DefaultTPoseRotate_JointSpace[0]),
                                                            math.radians(DefaultTPoseRotate_JointSpace[1]),
                                                            math.radians(DefaultTPoseRotate_JointSpace[2])))
            JointSpaceTransformation.setScale([1, 1, 1], OM.MSpace.kTransform)
            
            print '%s position: %s' % (JointName, [JointCurrentTranslate_JointSpace.x, JointCurrentTranslate_JointSpace.y, JointCurrentTranslate_JointSpace.z])
            DynamicJointToRootTransforms[IndexInCurrentJoints] = JointSpaceTransformation.asMatrix() * DynamicJointToRootTransforms[ParentIndex] 

    Frame = FrameData(FrameIndex, JointDatas)
    return Frame


#ConstructPose3dFrameData
# def ConstructPose3dFrameData(FrameIndex, Pose3dFrameCurrent):
#     JointDatas = {}
   
#     Frame = None

#     #init to default t-pose first
#     DefaultJointDatas = DefaultTPoseFrameData.GetJointDatas()
#     for Name in DefaultJointDatas:
#         T = DefaultJointDatas[Name].GetTranslate()
#         R = DefaultJointDatas[Name].GetRotate()
#         S = DefaultJointDatas[Name].GetScale()
#         JointDatas[Name] = JointData(Name, [T[0], T[1], T[2]],
#                                            [R[0], R[1], R[2]],
#                                            [S[0], S[1], S[2]])

#     #���޸� ��Ҫ�޸ĵ� �ؼ�֡�� ĿǰĬ�����еĹؼ��ı�ȫ��������ת��ɵ�, ���մ�������ƫ�ƣ������������ת��ҪӦ�õ����ؽڵ���ת���ǶԵ�
#     #��Щ�ؽڿ��ܹ���ͬһ�����׽ڵ㣬 ���������׽ڵ��Ѿ����Ĺ��� ��ô�Ͳ��ٸ��� ��ֻ֤��һ��
#     ChangedParent = {}
#     DynamicRootToJointTransforms = {}
#     #len(Pose3dFrameCurrent)
#     #testLen = 13
#     for i in range(len(Pose3dFrameCurrent)):
#         JointName = GetFormatJointName(i)
#         if JointName == NanStr:
#             return Frame 

#         IndexInCurrentJoints = GetPose3dJointIdxToCurrentJointsIdx(i)
#         if IndexInCurrentJoints == -1:
#             continue
        
#         #ParentIndex ��Ӧ���� CurrentJoints�е��±�
#         ParentIndex = CurrentJointsParent[IndexInCurrentJoints].GetParentIndex()
#         if ParentIndex == -1:
#             continue

#         #�Ѿ��޸Ĺ�һ�� parent��rotate��,�����ڵ�Ļ� Ҫ���⸸�ڵ�ת���
#         bChangedParent = ChangedParent.has_key(ParentIndex) and ChangedParent[ParentIndex]

#         #���ݵ�ǰ�������ؽڵ�ƫ�ƣ� �ο�T-pose��ƫ�ƣ�������������仯��ŷ���ǣ�Ȼ��ӵ����ڵ�� rotate��
#         ParentJointName = CurrentJoints[ParentIndex]

#         # ParentRot = None  
#         # if bChangedParent:
#         #     ParentRot = DefaultJointDatas[ParentJointName].GetRotate()
#         # else:
#         ParentRot = JointDatas[ParentJointName].GetRotate()

#         #������ ParentIndex,������� ParentIndex����� ���� ������ؽڵ�����ϵ��
#         ParentOffsetRotate = None
#         ParentTargetRotate = None

#         RealJointTranslateFromRoot = ConvertPos3dAxisValueToMaya(Pose3dFrameCurrent[i])
#         DefaultTPoseTranlate_JointSpace = DefaultJointDatas[JointName].GetTranslate()
#         DefaultTPoseRotate_JointSpace = DefaultJointDatas[JointName].GetRotate()

#         #���쵱ǰ�ؽ� ��root�ľ���
#         TransformationMatrix_Current = OM.MTransformationMatrix()
#         Translate = OM.MVector(RealJointTranslateFromRoot[0], RealJointTranslateFromRoot[1], RealJointTranslateFromRoot[2])
#         TransformationMatrix_Current.setTranslation(Translate, OM.MSpace.kTransform)
#         TransformationMatrix_Current.setRotation(OM.MEulerRotation(math.radians(DefaultTPoseRotate_JointSpace[0]),
#                                                             math.radians(DefaultTPoseRotate_JointSpace[1]),
#                                                             math.radians(DefaultTPoseRotate_JointSpace[2])))
#         TransformationMatrix_Current.setScale([1, 1, 1], OM.MSpace.kTransform)

#         #����Ĭ��
#         TransformationDefault = OM.MTransformationMatrix()
#         TranslateDefault = OM.MVector(DefaultTPoseTranlate_JointSpace[0], DefaultTPoseTranlate_JointSpace[1], DefaultTPoseTranlate_JointSpace[2])
#         TransformationDefault.setTranslation(TranslateDefault, OM.MSpace.kTransform)
#         TransformationDefault.setRotation(OM.MEulerRotation(math.radians(DefaultTPoseRotate_JointSpace[0]),
#                                                             math.radians(DefaultTPoseRotate_JointSpace[1]),
#                                                             math.radians(DefaultTPoseRotate_JointSpace[2])))
#         TransformationDefault.setScale([1, 1, 1], OM.MSpace.kTransform)

#         #print 'Child %s to Parent %s' % (JointName, ParentJointName)
#         #�������� ���ڵ��µ� ��һ���ڵ㣬��Щ�ڵ� ֱ����������Լ���ŷ����
#         #bTest = i == testLen - 1
#         if ParentIndex == 0:
            
#             ParentOffsetRotate = cmds.angleBetween(euler=True, v1=(DefaultTPoseTranlate_JointSpace[0], 
#                                                      DefaultTPoseTranlate_JointSpace[1], 
#                                                      DefaultTPoseTranlate_JointSpace[2]), 
#                                                  v2=(RealJointTranslateFromRoot[0], 
#                                                      RealJointTranslateFromRoot[1], 
#                                                      RealJointTranslateFromRoot[2]))

#             # if bTest:
#             #     print "joint0 %s space :%s" % (JointName, DefaultTPoseTranlate_JointSpace)

#             DynamicRootToJointTransforms[IndexInCurrentJoints] = TransformationDefault.asMatrix()
#             # print '=== 1Set Dynamic Index ::%s and Name:: %s' % (IndexInCurrentJoints, JointName)
#         else:
#             Matrix_Current = TransformationMatrix_Current.asMatrix()
            
#             if not bChangedParent:
#                 #�ѵ�ǰ�ӹؽ���root������ ת�� ��ǰ�Ĺؽڿռ� ��Ҫ�õ��ı任
#                 InverseMatrix = DynamicRootToJointTransforms[ParentIndex].inverse()
#                 ToJointSpaceMatrix = Matrix_Current * InverseMatrix

#                 #���ݼ���ĸ��ؽڿռ��������Ĭ�ϸ��ؽ�������������Ҫת����ŷ����
#                 TransformationMatrix_JointSpaceCurrent = OM.MTransformationMatrix(ToJointSpaceMatrix)
#                 JointCurrentTranslate_JointSpace = TransformationMatrix_JointSpaceCurrent.translation(OM.MSpace.kPostTransform)

#                 #if bTest:
#                     # TestTransformation = OM.MTransformationMatrix(DynamicRootToJointTransforms[ParentIndex])
#                     # TestTransformationLoc = TestTransformation.translation(OM.MSpace.kPostTransform)
#                     # Euler_Rad = TestTransformation.rotation()
#                     # TestRotateValue = [math.degrees(angle) for angle in (Euler_Rad.x, Euler_Rad.y, Euler_Rad.z)]
#                     # TestScale = TestTransformation.scale(OM.MSpace.kPostTransform)
#                     # print "joint1 %s parent %s loc :%s rot:%s scale:%s" % (JointName, ParentJointName, TestTransformationLoc, TestRotateValue, TestScale)
#                     #print "joint1 %s space :%s" % (JointName, JointCurrentTranslate_JointSpace)

#                 ParentOffsetRotate = cmds.angleBetween(euler=True, v1=(DefaultTPoseTranlate_JointSpace[0], 
#                                                         DefaultTPoseTranlate_JointSpace[1], 
#                                                         DefaultTPoseTranlate_JointSpace[2]), 
#                                                     v2=(JointCurrentTranslate_JointSpace.x, 
#                                                         JointCurrentTranslate_JointSpace.y, 
#                                                         JointCurrentTranslate_JointSpace.z))

#                 Transformation_DynamicParent = OM.MTransformationMatrix(DynamicRootToJointTransforms[ParentIndex])
#                 Transformation_DynamicParent.setRotation(OM.MEulerRotation(math.radians(ParentRot[0] + ParentOffsetRotate[0]),
#                                                                 math.radians(ParentRot[1] + ParentOffsetRotate[1]),
#                                                                 math.radians(ParentRot[2] + ParentOffsetRotate[2])))
#                 DynamicRootToJointTransforms[ParentIndex] = Transformation_DynamicParent.asMatrix()
#                 # print '=== 2ReSet Dynamic Index ::%s and Name:: %s' % (ParentIndex, ParentJointName)

            

#             DynamicRootToJointTransforms[IndexInCurrentJoints] = TransformationDefault.asMatrix() * DynamicRootToJointTransforms[ParentIndex] 
#             # print '=== 2Set Dynamic Index ::%s and Name:: %s' % (IndexInCurrentJoints, JointName)

#         # print '===================='
#         # print 'set Parent Joint Name %s' %  ParentJointName  
#         if not bChangedParent:

#             # if not bTest:
#             #     ParentTargetRotate = [ParentRot[0] + ParentOffsetRotate[0],
#             #                         ParentRot[1] + ParentOffsetRotate[1],
#             #                         ParentRot[2] + ParentOffsetRotate[2]] 
#             #     print 'rot name:%s' % ParentJointName
#             JointDatas[ParentJointName].SetRotate(ParentTargetRotate)

#         ChangedParent[ParentIndex] = True
    
#     Frame = FrameData(FrameIndex, JointDatas)
#     return Frame
   
def GetPose3dJointIndex(Name):
    for Index in JointIndexToName:
        if JointIndexToName[Index] == Name:
            return Index 
    return -1  

#LoadAllPose3dDatas
def LoadAllPose3dDatas(Pose3dFile):
    if not CheckSelectTarget():
        return
        
    FramesPose3d = np.load(Pose3dFile)['frames_3d']
    
    #��ӡ����Ϣ ����(1, 1662, 17, 3)���� 1���ˣ� 1662֡�� 17���ؽڣ� 3ά����
    FramesDesc = FramesPose3d.shape
    
    global CurrentFrameDatas
    CurrentFrameDatas = []
    
    global StartFrame
    StartFrame = 0
    
    global EndFrame
    EndFrame = FramesDesc[1] - 1
    #print 'EndFrame: %s' % EndFrame

    #��ſ�һ�� ����ؽ�λ�öԲ���
    for i in range(len(FramesPose3d[0][0])):
        JointPos = ConvertPos3dAxisValueToMaya(FramesPose3d[0][0][i])
        print '%s in root %s' % ( GetFormatJointName(i), JointPos)

    # for i in range(len(CurrentJoints)):
    #     print '%s Index is %s' % (i, CurrentJoints[i])

    Success = True
    #frame len : FramesDesc[1] �Ȳ���10֡
    print 'Begin LoadData ------------------->'
    for Index in range(1):
        #��0����
        NewFrameData = ConstructPose3dFrameData(Index, FramesPose3d[0][Index])
        if not NewFrameData:
            ErrorMessage('WrongJointFormat')
            Success = False
            break 

        CurrentFrameDatas.append(NewFrameData)
    print 'Load End ------------------->'

    Progress = 0   
    ProgressEnd = 1#len(CurrentFrameDatas)-1
    if Success == True: 
        print 'Begin Key ------------------->'
        ClearKeys()
        #for Index in range(len(CurrentFrameDatas)):
        for Index in range(1):
            Progress += 1.0
            print 'Key Process:: %.1f%%' % (Progress / ProgressEnd * 100)
            
            ConstructFrame(CurrentFrameDatas[Index])
        print 'End Key ------------------->'

        
#TODO: ������ð�ť�� ��������ǰ����֡���ݣ����л�T-Pose;
#      ���һ�� ����ؽڳ��ȵİ�ť
#      ����µ�һ�ж�ȡ���ã����ڶ�ȡ Pose3dĿ¼ 
#      ���ӳ��ؽ�����  

#��Ҫ��һ����ť�� ÿ����Ҫ��rescale�¹ؽڵĳ���
#����ؽڳ���, ��ӡpose3d�ؽڳ���
def RescaleJointPos(FramePose3d):
    LoadTargetRootAndJoint()
    LoadTPoseDefaultData()
    if not CheckSelectTarget():
        return

    FramesPose3d = np.load(FramePose3d)['frames_3d']
    FramePose3dPos = FramesPose3d[0][0]

    global Pose3dJointDistance
    Pose3dJointDistance = []
    DefaultJointDatas = DefaultTPoseFrameData.GetJointDatas()
    for Index in range(len(CurrentJointsParent)):
        JointParentData = CurrentJointsParent[Index]
        JointChild = JointParentData.GetJointName()
        JointParent = JointParentData.GetParentName()
        if JointParent != NanStr:
            IndexChild = GetPose3dJointIndex(JointChild)
            IndexParent = GetPose3dJointIndex(JointParent)
            PointStart = ConvertPos3dAxisValueToMaya(FramePose3dPos[IndexParent])
            PointEnd = ConvertPos3dAxisValueToMaya(FramePose3dPos[IndexChild])
            Len1 = OM.MVector(PointEnd[0] - PointStart[0], 
                              PointEnd[1] - PointStart[1], 
                              PointEnd[2] - PointStart[2]).length()
            DefaultJointChildData = DefaultTPoseFrameData.GetJointDatas()[JointChild]
            ChildP = DefaultJointChildData.GetTranslate()
            Len2 = OM.MVector(ChildP[0], ChildP[1], ChildP[2]).length()
            
            #��ȡ�ӹؽ���Ը��ؽڵĳ���
            Trans = DefaultJointDatas[JointChild].GetTranslate()
            OriginV = OM.MVector(Trans[0], Trans[1], Trans[2])
            DirectionV = OM.MVector(Trans[0], Trans[1], Trans[2])
            DirectionV = DirectionV.normalize()
            #�����ؽڳ���
            TargetV = OriginV + DirectionV * (Len1 - Len2)
            cmds.setAttr('%s.translate' % (JointChild), TargetV.x, TargetV.y, TargetV.z, type="double3")
            
            Pose3dJointDistance.append(Len1 - Len2)
        else:
            Pose3dJointDistance.append(0)


Pose3dPath = 'D:/Projects/UE4/LiveInputAnimation/LiveLinkResource/video2pose3d/pose_meixi.npz'
#'D:/Work/LiveLinkResource/video2pose3d/pose_meixi.npz'

#���ڶ���������ȵ� Pose3d
#RescaleJointPos(Pose3dPath)

# LoadTargetRootAndJoint()
# LoadTPoseDefaultData()
# LoadAllPose3dDatas(Pose3dPath)

############## �µ� frame���ɷ�����������Ҫ����ת����
class SkinnedNodeData:
    def __init__(self, _Name, _Type, _ParentName, _ParentType, _ParentIndex):
        self.Name = _Name
        self.Type = _Type
        self.Parent = _ParentName
        self.ParentType = _ParentType
        self.ParentIndex = _ParentIndex

    def GetName(self):
        return self.Name

    def GetType(self):
        return self.Type

    def GetParentIndex(self):
        return self.ParentIndex
        
    def GetParent(self):
        return self.Parent

    def GetParentType(self):
        return self.ParentType
        
    def Display(self):
        print '%s parent is %s,type is %s' % (self.Name, self.Parent, self.Type)

SkinnedNodesDatas = {}
RootTransformName = 'SK_Male_Tmp'
RootTransformDuplicate = 'SK_Male'
RootTransformRot = [-90, 0, 0]
PelvisRot = [90, -90, -90]
PelvisLoc = [0, 1.056, 96.751]

def CreateSkinnedNodes():
    global SkinnedNodesDatas
    SkinnedNodesDatas = {
        0:SkinnedNodeData('pelvis_tmp', 'joint', RootTransformName, 'transform', -1),
        1:SkinnedNodeData('thigh_r_tmp', 'joint', 'pelvis_tmp', 'joint', 0),
        2:SkinnedNodeData('calf_r_tmp', 'joint', 'thigh_r_tmp', 'joint', 1),
        3:SkinnedNodeData('foot_r_tmp', 'joint', 'calf_r_tmp', 'joint', 2),
        4:SkinnedNodeData('thigh_l_tmp', 'joint', 'pelvis_tmp', 'joint', 0),
        5:SkinnedNodeData('calf_l_tmp', 'joint', 'thigh_l_tmp', 'joint',4),
        6:SkinnedNodeData('foot_l_tmp', 'joint', 'calf_l_tmp', 'joint',5),
        7:SkinnedNodeData('spine_02_tmp', 'joint', 'pelvis_tmp', 'joint',0),
        8:SkinnedNodeData('spine_03_tmp', 'joint', 'spine_02_tmp', 'joint',7),
        9:SkinnedNodeData('neck_01_tmp', 'joint', 'spine_03_tmp', 'joint',8),
        10:SkinnedNodeData('head_tmp', 'joint', 'neck_01_tmp', 'joint',9),
        11:SkinnedNodeData('upperarm_l_tmp', 'joint', 'spine_03_tmp', 'joint',8),
        12:SkinnedNodeData('lowerarm_l_tmp', 'joint', 'upperarm_l_tmp', 'joint',11),
        13:SkinnedNodeData('hand_l_tmp', 'joint', 'lowerarm_l_tmp', 'joint',12),
        14:SkinnedNodeData('upperarm_r_tmp', 'joint', 'spine_03_tmp', 'joint',8),
        15:SkinnedNodeData('lowerarm_r_tmp', 'joint', 'upperarm_r_tmp', 'joint',14),
        16:SkinnedNodeData('hand_r_tmp', 'joint', 'lowerarm_r_tmp', 'joint',15),
    }

def IsWishParent(Current, WishParent, WishParentType):
    PName = cmds.listRelatives(Current, parent=True, type=WishParentType)
    if PName and PName[0] == WishParent:
        return True
    return False

def LoadPose3dData(Pose3dPath):
    FramesPose3d = np.load(Pose3dPath)['frames_3d']
    return FramesPose3d

def GetJointNewName(OldName):
    return OldName[:-4]

#�õ�0֡��
def CreateJoints():
    global Pose3dData
    cmds.select( d=True )
    JointDatas = Pose3dData[0][0]
    #create root transform
    if not cmds.objExists(RootTransformName):
        cmds.createNode("transform", name=RootTransformName)
        cmds.setAttr('%s.rotate' % (RootTransformName), RootTransformRot[0], RootTransformRot[1], RootTransformRot[2], type="double3")

    #create pelvis
    PelvisName = SkinnedNodesDatas[0].GetName()
    PelvisType = SkinnedNodesDatas[0].GetType()
    Pos = ConvertPos3dAxisValueToMaya(JointDatas[0])
    if not cmds.objExists(PelvisName):
        NewNode = cmds.joint(position= Pos, radius = 3)
        cmds.joint(NewNode, e=True, automaticLimits = True, zso=True, oj='xyz')
        cmds.rename(NewNode,PelvisName)

    cmds.setAttr('%s.translate' % (PelvisName), PelvisLoc[0], PelvisLoc[1], PelvisLoc[2], type="double3")
    cmds.setAttr('%s.rotate' % (PelvisName), PelvisRot[0], PelvisRot[1], PelvisRot[2], type="double3") 
        
    #init other pos in pelvis    
    for Index in range(1, len(JointDatas)):
        SkinnNodeData = SkinnedNodesDatas[Index]
        Name = SkinnNodeData.GetName()
        if not cmds.objExists(Name):
            NewNode = cmds.joint(radius = 3)
            cmds.joint(NewNode, e=True, zso=True, oj='xyz')
            cmds.rename(NewNode, Name)

        if not IsWishParent(Name, PelvisName, PelvisType):
            cmds.parent(Name, PelvisName)

        Pos = ConvertPos3dAxisValueToMaya(JointDatas[Index])
        cmds.joint(Name, edit=True, relative=True, position=Pos)

    #reparent to the right joint 
    for Index in range(1, len(JointDatas)):
        SkinnNodeData = SkinnedNodesDatas[Index]
        if not IsWishParent(SkinnNodeData.GetName(), SkinnNodeData.GetParent(), SkinnNodeData.GetParentType()):
            cmds.parent(SkinnNodeData.GetName(), SkinnNodeData.GetParent())

    #generate T-pose data 
    global DefaultTPoseFrameData, CurrentFrameDatas
    CurrentFrameDatas = []
    CurrentJointDatas = {}
    for i in range(len(JointDatas)):
        JointName = SkinnedNodesDatas[i].GetName()
        AttrTranslate = cmds.getAttr( '%s.translate' % (JointName))
        AttrRot = cmds.getAttr( '%s.rotate' % (JointName))
        AttScale = cmds.getAttr( '%s.scale' % (JointName))
        
        #ȥ��_tmp
        NewName = GetJointNewName(JointName)
        Joint = JointData(NewName, 
                         [AttrTranslate[0][0], AttrTranslate[0][1], AttrTranslate[0][2] ],
                         [AttrRot[0][0],       AttrRot[0][1],       AttrRot[0][2] ],
                         [AttScale[0][0],      AttScale[0][1],      AttScale[0][2]],
                         )
        CurrentJointDatas[NewName] = Joint
    DefaultTPoseFrameData = FrameData(-1, CurrentJointDatas)    
    #push ��һ֡�� ����
    CurrentFrameDatas.append(DefaultTPoseFrameData) 

def DuplicateJoints():
    if not cmds.objExists(RootTransformDuplicate):
        DuplicateObj = cmds.duplicate(RootTransformName, returnRootsOnly=True, renameChildren=True)
        cmds.rename(DuplicateObj, RootTransformDuplicate)

        #rename duplicate joint
        def RenameChildJoint(JointParent):
            Children = cmds.listRelatives(JointParent, children=True, type='joint')
            if Children:
                for Child in Children:
                    #rename �Ѻ���� _tmp1ȥ��, �@��1���Ԅ����ɵ�
                    NewName = Child[:-5]
                    cmds.rename(Child, NewName)
                    RenameChildJoint(NewName)
        RenameChildJoint(RootTransformDuplicate)

def GenerateTempFrameJoint(JointDatas):
    #init other pos in pelvis    
    PelvisName = SkinnedNodesDatas[0].GetName()
    PelvisType = SkinnedNodesDatas[0].GetType()

    for Index in range(1, len(JointDatas)):
        SkinnNodeData = SkinnedNodesDatas[Index]
        Name = SkinnNodeData.GetName()

        if not IsWishParent(Name, PelvisName, PelvisType):
            cmds.parent(Name, PelvisName)

        Pos = ConvertPos3dAxisValueToMaya(JointDatas[Index])
        cmds.joint(Name, edit=True, relative=True, position=Pos)

    #reparent to the right joint 
    for Index in range(1, len(JointDatas)):
        SkinnNodeData = SkinnedNodesDatas[Index]
        if not IsWishParent(SkinnNodeData.GetName(), SkinnNodeData.GetParent(), SkinnNodeData.GetParentType()):
            cmds.parent(SkinnNodeData.GetName(), SkinnNodeData.GetParent())

def GetDefaultJointMatrix(JointName):
    global DefaultTPoseFrameData
    DefaultJointDatas = DefaultTPoseFrameData.GetJointDatas()

    DefaultTPoseTranlate_JointSpace = DefaultJointDatas[JointName].GetTranslate()
    DefaultTPoseRotate_JointSpace = DefaultJointDatas[JointName].GetRotate()

    TransformationDefault = OM.MTransformationMatrix()
    Translate = OM.MVector(DefaultTPoseTranlate_JointSpace[0], DefaultTPoseTranlate_JointSpace[1], DefaultTPoseTranlate_JointSpace[2])
    TransformationDefault.setTranslation(Translate, OM.MSpace.kTransform)
    TransformationDefault.setRotation(OM.MEulerRotation(math.radians(DefaultTPoseRotate_JointSpace[0]),
                                                        math.radians(DefaultTPoseRotate_JointSpace[1]),
                                                        math.radians(DefaultTPoseRotate_JointSpace[2])))
    TransformationDefault.setScale([1, 1, 1], OM.MSpace.kTransform)
    return TransformationDefault.asMatrix()

# def GenerateRealFrameJointByTemp(JointDatas, FrameIndex):          
#     FrameJointDatas = {}
#     #init to default t-pose first
#     DefaultJointDatas = DefaultTPoseFrameData.GetJointDatas()
#     for Name in DefaultJointDatas:
#         T = DefaultJointDatas[Name].GetTranslate()
#         R = DefaultJointDatas[Name].GetRotate()
#         S = DefaultJointDatas[Name].GetScale()
#         FrameJointDatas[Name] = JointData(Name, [T[0], T[1], T[2]],
#                                            [R[0], R[1], R[2]],
#                                            [S[0], S[1], S[2]])

#     #���޸� ��Ҫ�޸ĵ� �ؼ�֡�� ĿǰĬ�����еĹؼ��ı�ȫ��������ת��ɵ�, ���մ�������ƫ�ƣ������������ת��ҪӦ�õ����ؽڵ���ת���ǶԵ�
#     #��Щ�ؽڿ��ܹ���ͬһ�����׽ڵ㣬 ���������׽ڵ��Ѿ����Ĺ��� ��ô�Ͳ��ٸ��� ��ֻ֤��һ��
#     ChangedParent = {}
#     DynamicRootToJointTransforms = {}


#     # len(JointDatas)
#     for i in range(1, 7):
#         #tmp �Ǽ��µģ����ʱ�� ��Ҫ��tmp�Ǽܵ�����ת��һ�£���_tmpȥ��
#         TmpJointName = SkinnedNodesDatas[i].GetName()
#         JointName = GetJointNewName(TmpJointName)
#         ParentName = GetJointNewName(SkinnedNodesDatas[i].GetParent())

#         #�Ѿ��޸Ĺ�һ�� parent��rotate��,�����ڵ�Ļ� Ҫ���⸸�ڵ�ת���
#         bChangedParent = ChangedParent.has_key(ParentName) and ChangedParent[ParentName]

#         ParentRot = FrameJointDatas[ParentName].GetRotate()

#         #������ ParentName,������� ParentName����� ���� ������ؽڵ�����ϵ��
#         ParentOffsetRotate = None
#         ParentTargetRotate = None

#         DefaultTPoseTranlate_JointSpace = DefaultJointDatas[JointName].GetTranslate()
#         DefaultTPoseRotate_JointSpace = DefaultJointDatas[JointName].GetRotate()
       
#         RealJointTranslateFromRoot = ConvertPos3dAxisValueToMaya(JointDatas[i])

#         #���쵱ǰ�ؽ���root�ľ���
#         TransformationMatrix_Current = OM.MTransformationMatrix()
#         Translate = OM.MVector(RealJointTranslateFromRoot[0], RealJointTranslateFromRoot[1], RealJointTranslateFromRoot[2])
#         TransformationMatrix_Current.setTranslation(Translate, OM.MSpace.kTransform)
#         TransformationMatrix_Current.setRotation(OM.MEulerRotation(math.radians(DefaultTPoseRotate_JointSpace[0]),
#                                                             math.radians(DefaultTPoseRotate_JointSpace[1]),
#                                                             math.radians(DefaultTPoseRotate_JointSpace[2])))
#         TransformationMatrix_Current.setScale([1, 1, 1], OM.MSpace.kTransform)

#         RootJointName = GetJointNewName(SkinnedNodesDatas[0].GetName())
#         if ParentName == RootJointName:
#             ParentOffsetRotate = cmds.angleBetween(euler=True, v1=(DefaultTPoseTranlate_JointSpace[0], 
#                                                     DefaultTPoseTranlate_JointSpace[1], 
#                                                     DefaultTPoseTranlate_JointSpace[2]), 
#                                                 v2=(RealJointTranslateFromRoot[0], 
#                                                     RealJointTranslateFromRoot[1], 
#                                                     RealJointTranslateFromRoot[2]))
#             print "real0 pos :%s" % RealJointTranslateFromRoot
#             DynamicRootToJointTransforms[JointName] = TransformationMatrix_Current.asMatrix()
#         else:
#             Matrix_Current = TransformationMatrix_Current.asMatrix()
#             #�ѵ�ǰ�ӹؽ���root������ ת�� ��ǰ�Ĺؽڿռ� ��Ҫ�õ��ı任
#             InverseMatrix = DynamicRootToJointTransforms[ParentName].inverse()
#             ToJointSpaceMatrix = Matrix_Current * InverseMatrix

#             TransformationMatrix_JointSpaceCurrent = OM.MTransformationMatrix(ToJointSpaceMatrix)
#             JointCurrentTranslate_JointSpace = TransformationMatrix_JointSpaceCurrent.translation(OM.MSpace.kPostTransform)
#             print "real1 pos :%s" % JointCurrentTranslate_JointSpace
#             ParentOffsetRotate = cmds.angleBetween(euler=True, v1=(DefaultTPoseTranlate_JointSpace[0], 
#                                                     DefaultTPoseTranlate_JointSpace[1], 
#                                                     DefaultTPoseTranlate_JointSpace[2]), 
#                                                 v2=(JointCurrentTranslate_JointSpace.x, 
#                                                     JointCurrentTranslate_JointSpace.y, 
#                                                     JointCurrentTranslate_JointSpace.z))
#             #default matrix
#             TransformationDefault = GetDefaultJointMatrix(JointName)  

#             ParentIndex = SkinnedNodesDatas[i].GetParentIndex()
#             ParentParentIndex = SkinnedNodesDatas[ParentIndex].GetParentIndex()
#             ParentParentName = GetJointNewName(SkinnedNodesDatas[ParentIndex].GetParent())
#             Transformation_DynamicParent = None
#             if ParentParentIndex == 0:
#                 Transformation_DynamicParent = OM.MTransformationMatrix(DynamicRootToJointTransforms[ParentName])
#                 Transformation_DynamicParent.setRotation(OM.MEulerRotation(math.radians(ParentRot[0] + ParentOffsetRotate[0]),
#                                                                 math.radians(ParentRot[1] + ParentOffsetRotate[1]),
#                                                                 math.radians(ParentRot[2] + ParentOffsetRotate[2])))
#                 DynamicRootToJointTransforms[ParentName] = Transformation_DynamicParent.asMatrix()
#             else:
#                 Parent_TransformationDefault = GetDefaultJointMatrix(ParentName)
#                 Transformation_Parent = OM.MTransformationMatrix(Parent_TransformationDefault)
#                 Transformation_Parent.setRotation(OM.MEulerRotation(math.radians(ParentRot[0] + ParentOffsetRotate[0]),
#                                                                 math.radians(ParentRot[1] + ParentOffsetRotate[1]),
#                                                                 math.radians(ParentRot[2] + ParentOffsetRotate[2])))
#                 DynamicRootToJointTransforms[ParentName] = Transformation_Parent.asMatrix() * DynamicRootToJointTransforms[ParentParentName]
#             #
#             DynamicRootToJointTransforms[JointName] = TransformationDefault * DynamicRootToJointTransforms[ParentName]
      
#         #print '%s OffsetRotate: %s' % (ParentName, ParentOffsetRotate)
#         ParentTargetRotate = [ParentRot[0] + ParentOffsetRotate[0],
#                             ParentRot[1] + ParentOffsetRotate[1],
#                             ParentRot[2] + ParentOffsetRotate[2]] 

#         #print '%s ParentTargetRotate: %s' % (ParentName, ParentTargetRotate)
#         if not bChangedParent:
#             FrameJointDatas[ParentName].SetRotate(ParentTargetRotate)

#         ChangedParent[ParentName] = True
    
#     return FrameData(FrameIndex, FrameJointDatas)

def GenerateRealFrameJointByTemp(JointDatas, FrameIndex):          
    FrameJointDatas = {}
    #init to default t-pose first
    DefaultJointDatas = DefaultTPoseFrameData.GetJointDatas()
    for Name in DefaultJointDatas:
        T = DefaultJointDatas[Name].GetTranslate()
        R = DefaultJointDatas[Name].GetRotate()
        S = DefaultJointDatas[Name].GetScale()
        FrameJointDatas[Name] = JointData(Name, [T[0], T[1], T[2]],
                                           [R[0], R[1], R[2]],
                                           [S[0], S[1], S[2]])

    #���޸� ��Ҫ�޸ĵ� �ؼ�֡�� ĿǰĬ�����еĹؼ��ı�ȫ��������ת��ɵ�, ���մ�������ƫ�ƣ������������ת��ҪӦ�õ����ؽڵ���ת���ǶԵ�
    #��Щ�ؽڿ��ܹ���ͬһ�����׽ڵ㣬 ���������׽ڵ��Ѿ����Ĺ��� ��ô�Ͳ��ٸ��� ��ֻ֤��һ��
    ChangedParent = {}
    for i in range(1, len(JointDatas)):
        #tmp �Ǽ��µģ����ʱ�� ��Ҫ��tmp�Ǽܵ�����ת��һ�£���_tmpȥ��
        TmpJointName = SkinnedNodesDatas[i].GetName()
        JointName = GetJointNewName(TmpJointName)
        ParentName = GetJointNewName(SkinnedNodesDatas[i].GetParent())

        #�Ѿ��޸Ĺ�һ�� parent��rotate��,�����ڵ�Ļ� Ҫ���⸸�ڵ�ת���
        bChangedParent = ChangedParent.has_key(ParentName) and ChangedParent[ParentName]

        ParentRot = FrameJointDatas[ParentName].GetRotate()

        #������ ParentName,������� ParentName����� ���� ������ؽڵ�����ϵ��
        ParentOffsetRotate = None
        ParentTargetRotate = None

        CurrentTranslate = cmds.getAttr( '%s.translate' % (TmpJointName))
        TranslateIn_JointSpace = CurrentTranslate[0]

        DefaultTPoseTranlate_JointSpace = DefaultJointDatas[JointName].GetTranslate()

        ParentOffsetRotate = cmds.angleBetween(euler=True, v1=(DefaultTPoseTranlate_JointSpace[0], 
                                                     DefaultTPoseTranlate_JointSpace[1], 
                                                     DefaultTPoseTranlate_JointSpace[2]), 
                                                 v2=(TranslateIn_JointSpace[0], 
                                                     TranslateIn_JointSpace[1], 
                                                     TranslateIn_JointSpace[2]))

        print '%s TPose %s, InParentJoint Pos %s, Parent %s OffsetRotate %s' % (JointName, DefaultTPoseTranlate_JointSpace, TranslateIn_JointSpace, ParentName, ParentOffsetRotate)
        ParentTargetRotate = [ParentRot[0] + ParentOffsetRotate[0],
                            ParentRot[1] + ParentOffsetRotate[1],
                            ParentRot[2] + ParentOffsetRotate[2]] 

        if not bChangedParent:
            FrameJointDatas[ParentName].SetRotate(ParentTargetRotate)

        ChangedParent[ParentName] = True
    
    return FrameData(FrameIndex, FrameJointDatas)

def GenerateFrameJoint(JointDatas, FrameIndex):
    GenerateTempFrameJoint(JointDatas)
    Frame = GenerateRealFrameJointByTemp(JointDatas, FrameIndex)
    return Frame

def GenerateFrameJointDatas():
    cmds.select( d=True )
    global Pose3dData, TotalFrame, CurrentFrameDatas, Progress
    Progress = 0 
    for i in range(1, TotalFrame):
        Progress += 1.0
        print 'FrameData Progress:: %.1f%%' % (Progress / ProgressEnd * 100)

        JointDatas = Pose3dData[0][i]
        Frame = GenerateFrameJoint(JointDatas, i)
        CurrentFrameDatas.append(Frame)

def ClearTheKeys():
    #ɾ����ǰʱ���ߵ���ʼ������֡����
    StartTime = cmds.playbackOptions(query=True, minTime=True)
    EndTime = cmds.playbackOptions(query=True, maxTime=True)
    
    for DataIndex in SkinnedNodesDatas:
        JointName = SkinnedNodesDatas[DataIndex].GetName()
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='translateX')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='translateY')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='translateZ')
        
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='rotateX')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='rotateY')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='rotateZ')
        
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='scaleX')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='scaleY')
        cmds.cutKey(JointName, time=(StartTime, EndTime), attribute='scaleZ')

    cmds.playbackOptions(minTime=StartFrame, maxTime=EndFrame, animationStartTime=StartFrame, animationEndTime=EndFrame)

def ConstructTheFrame(Frame):
    FrameIndex = Frame.GetFrameIndex()  
    JointDatas = Frame.GetJointDatas()
    cmds.currentTime(FrameIndex, edit=True)
    for JointName in JointDatas:
        Joint = JointDatas[JointName]
        if Joint:
            KeyJointTranslate(JointName, FrameIndex, Joint.GetTranslate())
            KeyJointRotate(JointName, FrameIndex, Joint.GetRotate())
            KeyJointScale(JointName, FrameIndex, Joint.GetScale())

def GenerateFrames():
    #���������ؼ�֡
    ClearTheKeys()
    global Progress
    Progress = 0 
    #generate frame key
    for Frame in CurrentFrameDatas:
        Progress += 1.0
        print 'Key Process:: %.1f%%' % (Progress / ProgressEnd * 100)
        ConstructTheFrame(Frame)

    #ɾ��tmp
    cmds.select(RootTransformName)
    cmds.delete()

#debug
def GenerateDebugJointTmp(FrameIndex):
    global Pose3dData
    JointDatas = Pose3dData[0][FrameIndex]
    GenerateTempFrameJoint(JointDatas)
    NewPos = [-120, 0 , 0]
    cmds.setAttr('%s.translate' % (RootTransformName), NewPos[0], NewPos[1], NewPos[2], type="double3")

#generate debug frame 
def GenerateDebugJointFrame(FrameIndex):
    global Pose3dData
    JointDatas = Pose3dData[0][FrameIndex]
    Frame = GenerateRealFrameJointByTemp(JointDatas, FrameIndex)
    #ClearTheKeys()
    #ConstructTheFrame(Frame)
    
##
CreateSkinnedNodes()
Pose3dData = LoadPose3dData(Pose3dPath)
FramesDesc = Pose3dData.shape

#���Ȱ��յ�0֡ ���ɹؽ�, ��������Ĭ��T-Pose����
CreateJoints()
#���ƹؽڸ��ڵ㣬֮ǰ���ɵĹؽ� ���� parent���㣬���Ƴ����Ĺؽ����ڸ����������ɹؼ�֡�����ͬʱҲ���ԶԱȵ���
DuplicateJoints()

bDebug = True
DebugFrame = 100

if not bDebug:
    TotalFrame = 100#FramesDesc[1]
    StartFrame = 0
    EndFrame = TotalFrame - 1

    Progress = 0
    ProgressEnd = TotalFrame
    GenerateFrameJointDatas()
    #���ɹؼ�֡��ɾ�� tmp�Ǽ�
    GenerateFrames()
else:
    GenerateDebugJointTmp(DebugFrame)
    GenerateDebugJointFrame(DebugFrame)

  


