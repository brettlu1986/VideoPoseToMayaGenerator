#ImportAiMotionWithUI

'''
1.加载 npz, 根据T-pose创建关节
2.先写 读取 并组织 关键帧数据
3.起Timer, 大概每30毫秒加载一个关键帧到 maya
4.或者 走网络传输
'''

import maya.cmds as cmds
import functools
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

#Variables
WindowId = 'ImportAnimUI'
WindowTitle = 'ImportAnimUI'
NanStr = 'Nan'

#Path EditWidth
EditFieldWidth = 400

#统一对齐一下关节长度， 假设pose3d坐标统一放大100倍，根据放大后的位置对当前关节长度统一进行调整适配
Pose3dPoseScale = 100

StartFrame = 0
EndFrame = 0
Progress = 0
ProgressEnd = 0
TotalFrame = 0

CurrentFrameDatas = []#每帧Frame一帧的关节数据
DefaultTPoseFrameData = None
Pose3dData = None

SkinnedNodesDatas = {}
RootTransformName = 'SK_Male'
RootTransformRot = [-90, -90, 0]
RootTransformLoc = [0, 0, 0]

#Classes
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
        print ('JointData: %s, %s, %s, %s' % (self.JointName, self.Translate, self.Rotate, self.Scale))

class FrameData:
    def __init__(self, FrameIndex, JointDatas):
        self.FrameIndex = FrameIndex 
        self.JointDatas = JointDatas
    
    def GetFrameIndex(self):
        return self.FrameIndex
        
    def GetJointDatas(self):
        return self.JointDatas  
        
    def Display(self):
        print ('FrameData: %s' % (self.FrameIndex))
        for key in self.JointDatas:
            Joint = self.JointDatas[key]
            Joint.Display()
        
class SkinnedNodeData:
    def __init__(self, _Name, _Type, _ParentName, _ParentType, _ParentIndex):
        self.Name = _Name
        self.Type = _Type
        self.Parent = _ParentName
        self.ParentType = _ParentType
        self.ParentIndex = _ParentIndex
        
        self.JointLen = 0
        self.PositionInTpose = [0, 0, 0]

    def SetJointLength(self, NewLen):
        self.JointLen = NewLen  

    def SetPositionInTPose(self, NewPos):
        self.PositionInTpose = NewPos 

    def GetJointLength(self):
        return self.JointLen 

    def GetPositionInTPose(self):
        return self.PositionInTpose

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
        print ('%s parent is %s,type is %s' % (self.Name, self.Parent, self.Type))

#util functions
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

def ConvertPos3dRotateToMaya(JointValue):
    NewRot = [RoundHalfUp(JointValue[3], 3) , RoundHalfUp(JointValue[4], 3), RoundHalfUp(JointValue[5], 3)]
    return [NewRot[1], NewRot[2], NewRot[0]]

def ConvertPos3dAxisValueToMaya(JointValue):
    return [RoundHalfUp(JointValue[0], 3), RoundHalfUp(JointValue[1], 3), RoundHalfUp(JointValue[2], 3)]

#ErrorMessage 
def ErrorMessage(KeyMsg):
    cmds.confirmDialog(title='Error Message', message=ErrorMsgTypeStr[KeyMsg], button=['Ok'])
    print ("ErrorMsg: %s" % (ErrorMsgTypeStr[KeyMsg])  )

#ApplyFile
def ApplyFile(pImportField, *pArgs):
    File = cmds.textField(pImportField, query=True, text=True)
    if not File or File == '':
        ErrorMessage('FileNotNull')
        return
    #print ('Apply File: %s' % File  )   
    global Pose3dData
    Pose3dData = LoadPose3dData(File)

    #创建T-pose数据
    CreateTPoseData()
    #根据 T-pose数据生成关节
    CreateJoints()
    #创建所有 帧数据
    GenerateFrameJointDatas()
    #生成关键帧，删除 tmp骨架
    GenerateFrames()
    
#ImportFromAnimFilePath : 直接复制文件路径进去，点击Apply， 或者Browse选择json文件
def OpenImportFileDialog(pImportField, *pArgs):
   Path = cmds.fileDialog2(fileFilter='*.npz', dialogStyle=2, fileMode=1, cap='Select Import File')
   if Path:
       cmds.textField(pImportField, edit=True, text=Path[0])
       #print ('Import From Anim File:%s '% (Path))

#Browse to load anim data
def CreateImportUI(pOpenImportFileDialog, pApplyFile):
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
    cmds.separator(h=10, style='none')
    cmds.button(label='Cancel', command=cancelCallBack)
    
    def resetToDefault(*pArgs):
        #TODO: reset to default
        print ('clear the keys')
        #ClearKeys()
    cmds.button(label='Reset2TPose', command=resetToDefault)
    cmds.showWindow()

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

def ClearKeys():
    #删除当前时间线的起始跟结束帧数据
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

def CreateSkinnedNodes():
    global SkinnedNodesDatas
    SkinnedNodesDatas = {
        0:SkinnedNodeData('pelvis', 'joint', RootTransformName, 'transform', -1),
        1:SkinnedNodeData('thigh_r', 'joint', 'pelvis', 'joint', 0),
        2:SkinnedNodeData('calf_r', 'joint', 'thigh_r', 'joint', 1),
        3:SkinnedNodeData('foot_r', 'joint', 'calf_r', 'joint', 2),
        4:SkinnedNodeData('thigh_l', 'joint', 'pelvis', 'joint', 0),
        5:SkinnedNodeData('calf_l', 'joint', 'thigh_l', 'joint', 4),
        6:SkinnedNodeData('foot_l', 'joint', 'calf_l', 'joint', 5),
        7:SkinnedNodeData('spine_02', 'joint', 'pelvis', 'joint', 0),
        8:SkinnedNodeData('spine_03', 'joint', 'spine_02', 'joint', 7),
        9:SkinnedNodeData('neck_01', 'joint', 'spine_03', 'joint', 8),
        10:SkinnedNodeData('head', 'joint', 'neck_01', 'joint', 9),
        11:SkinnedNodeData('upperarm_l', 'joint', 'spine_03', 'joint', 8),
        12:SkinnedNodeData('lowerarm_l', 'joint', 'upperarm_l', 'joint', 11),
        13:SkinnedNodeData('hand_l', 'joint', 'lowerarm_l', 'joint', 12),
        14:SkinnedNodeData('upperarm_r', 'joint', 'spine_03', 'joint', 8),
        15:SkinnedNodeData('lowerarm_r', 'joint', 'upperarm_r', 'joint', 14),
        16:SkinnedNodeData('hand_r', 'joint', 'lowerarm_r', 'joint', 15),
    }

def IsWishParent(Current, WishParent, WishParentType):
    PName = cmds.listRelatives(Current, parent=True, type=WishParentType)
    if PName and PName[0] == WishParent:
        return True
    return False

def LoadPose3dData(Pose3dPath):
    FramesPose3d = np.load(Pose3dPath)['frames_3d']

    global StartFrame, EndFrame, Progress, ProgressEnd, TotalFrame

    TotalFrame = FramesPose3d.shape[0]

    StartFrame = 0
    EndFrame = TotalFrame - 1
    Progress = 0
    ProgressEnd = TotalFrame
    return FramesPose3d

#GetTPoseJointPostion
#根据关节长度来确定 t-pose时候的 关节坐标
def GetTPoseJointPostion(JointIndex, JointLength):
    if JointIndex == 1:#thigh_r
        return [-JointLength, 0 , 0]
    elif JointIndex == 2 or JointIndex == 3 or JointIndex == 5 or JointIndex == 6:#calf_r foot_r calf_l foot_l
        return [0, 0, -JointLength]
    elif JointIndex == 4:#thigh_l
        return [JointLength, 0, 0]
    elif JointIndex == 7 or JointIndex == 8 or JointIndex == 9 or JointIndex == 10:#spine_02 spine_03 neck_01 head
        return [0, 0, JointLength]
    elif JointIndex == 11 or JointIndex == 12 or JointIndex == 13:#upperarm_l lowerarm_l hand_l
        return [JointLength, 0, 0]
    elif JointIndex == 14 or JointIndex == 15 or JointIndex == 16:#upperarm_r lowerarm_r hand_r
        return [-JointLength, 0, 0]

#CreateTPoseData
#根据第一帧 计算关节长度， 然后创建T-pose关节数据，默认应该是相同的坐标系，并且旋转都是 0 0 0
def CreateTPoseData():
    global Pose3dData
     #暂时先用 第0帧的数据来计算  t-pose 关节位置
    JointDatas = Pose3dData[0]
    
    for i in range(len(JointDatas)):
        ParentIndex = SkinnedNodesDatas[i].GetParentIndex()
        if ParentIndex == -1:
            SkinnedNodesDatas[i].SetJointLength(0)
            SkinnedNodesDatas[i].SetPositionInTPose([0, 0, 0])
        else:
            #计算 关节的长度 
            PointStart = ConvertPos3dAxisValueToMaya(JointDatas[ParentIndex])
            PointEnd = ConvertPos3dAxisValueToMaya(JointDatas[i])

            Len = OM.MVector(PointEnd[0] - PointStart[0],
                             PointEnd[1] - PointStart[1],
                             PointEnd[2] - PointStart[2]).length()
            SkinnedNodesDatas[i].SetJointLength(Len)
            SkinnedNodesDatas[i].SetPositionInTPose(GetTPoseJointPostion(i, Len))

#CreateJoints
#根据创建好的 T-pose数据，在maya创建 关节
def CreateJoints():
    #取消outliner里的选中
    cmds.select( d=True )

    #create root transform
    if not cmds.objExists(RootTransformName):
        cmds.createNode("transform", name=RootTransformName)

    cmds.setAttr('%s.rotate' % (RootTransformName), RootTransformRot[0], RootTransformRot[1], RootTransformRot[2], type="double3")
    cmds.setAttr('%s.translate' % (RootTransformName), RootTransformLoc[0], RootTransformLoc[1], RootTransformLoc[2], type="double3")

    #create pelvis
    PelvisName = SkinnedNodesDatas[0].GetName()
    
    #没有胯骨 先创建
    if not cmds.objExists(PelvisName):
        #默认就会创建成 上面的 RootTransform的子节点
        NewNode = cmds.joint(radius = 3)
        #e=True代表 Edit=True， 表示可以改变属性值， 比如 translate
        cmds.joint(NewNode, e=True, automaticLimits = True, zso=True)
        #默认创建的名字不够规范， 所以 rename一下
        cmds.rename(NewNode, PelvisName)
        cmds.xform(PelvisName, preserve=True, rotateOrder='yxz')

    Pos = SkinnedNodesDatas[0].GetPositionInTPose()
    cmds.setAttr('%s.translate' % (PelvisName), Pos[0], Pos[1], Pos[2], type="double3")
        
    #init other pos in pelvis    
    for Index in SkinnedNodesDatas:
        if Index != 0:
            SkinnNodeData = SkinnedNodesDatas[Index]
            Name = SkinnNodeData.GetName()
            if not cmds.objExists(Name):
                NewNode = cmds.joint(radius = 3)
                #cmds.joint(NewNode)
                cmds.joint(NewNode, e=True, zso=True)
                cmds.rename(NewNode, Name)
                cmds.xform(Name, preserve=True, rotateOrder='yxz')

            if not IsWishParent(Name, SkinnNodeData.GetParent(), SkinnNodeData.GetParentType()):
                cmds.parent(Name, SkinnNodeData.GetParent())

            PosJoint = SkinnNodeData.GetPositionInTPose()
            cmds.joint(Name, edit=True, relative=True, position=PosJoint)

    #generate T-pose data 
    global DefaultTPoseFrameData
    CurrentJointDatas = {}
    for i in SkinnedNodesDatas:
        JointName = SkinnedNodesDatas[i].GetName()
        AttrTranslate = cmds.getAttr( '%s.translate' % (JointName))
        AttrRot = cmds.getAttr( '%s.rotate' % (JointName))
        AttScale = cmds.getAttr( '%s.scale' % (JointName))
       
        Joint = JointData(JointName, 
                         [AttrTranslate[0][0], AttrTranslate[0][1], AttrTranslate[0][2] ],
                         [AttrRot[0][0],       AttrRot[0][1],       AttrRot[0][2] ],
                         [AttScale[0][0],      AttScale[0][1],      AttScale[0][2]],
                         )
        CurrentJointDatas[JointName] = Joint
    DefaultTPoseFrameData = FrameData(-1, CurrentJointDatas)

def GenerateFrameJoint(JointDatas, FrameIndex):          
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

    for i in range(len(JointDatas)):
        JointName = SkinnedNodesDatas[i].GetName()
        TargetRotate = ConvertPos3dRotateToMaya(JointDatas[i])
        FrameJointDatas[JointName].SetRotate(TargetRotate)
    
    return FrameData(FrameIndex, FrameJointDatas)

def GenerateFrameJointDatas():
    cmds.select( d=True )
    global Pose3dData, TotalFrame, CurrentFrameDatas, Progress
    Progress = 0 
    for i in range(TotalFrame):
        Progress += 1.0
        print ('FrameData Progress:: %.1f%%' % (Progress / ProgressEnd * 100))
        JointDatas = Pose3dData[i]
        Frame = GenerateFrameJoint(JointDatas, i)
        CurrentFrameDatas.append(Frame)

def ConstructFrame(Frame):
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
    #清理遗留关键帧
    ClearKeys()

    global Progress
    Progress = 0 
    #generate frame key
    for Frame in CurrentFrameDatas:
        Progress += 1.0
        print ('AnimKey Process:: %.1f%%' % (Progress / ProgressEnd * 100))
        ConstructFrame(Frame)

CreateSkinnedNodes()
CreateImportUI(OpenImportFileDialog, ApplyFile)




  


