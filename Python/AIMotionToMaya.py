#ImportAiMotionWithUI

__author__ 		= "Lu Zheng"
__copyright__ 	= "Copyright 2022, Lu Zheng"
__credits__ 	= ["Lu Zheng"]
__version__ 	= "1.0.0"
__maintainer__ 	= "Lu Zheng"
__email__ 		= "luzheng2@kingsoft.com"
__status__ 		= "Release"

import maya.cmds as cmds
import functools
import numpy as np
import math

import maya.api.OpenMaya as OM
from maya.api.OpenMaya import MVector, MMatrix, MPoint
from enum import Enum

from collections import deque
import threading
import random
from pyqtgraph.Qt import QtCore

import AiMotionCore as MotionCore

#Config 
ErrorMsgTypeStr = {
    'FileNotNull' : 'Dir or File path should not be null.',
    'LoadDefaultT-PoseError' : 'To Load T-Pose, we must import .npz file first.',
    'NoSk_Male' : 'No Sk_Male imported, import the model first',
    'UploadError' : 'Video Upload Error.'
}

#监听 发送到Maya的代码指令 执行
ListenPort = 7001

StartFrame = 0
EndFrame = 0
Progress = 0
ProgressEnd = 0
TotalFrame = 0

CurrentFrameDatas = []#每帧Frame一帧的关节数据
DefaultTPoseFrameData = None

#存放 解析的 动作关节数据
Pose3dData = np.array([])
#存放 创建的T-pose关节数据
Pose3dTPose = np.array([])

#Root Transform 节点的位置和旋转
SkinnedNodesDatas = {}
RootTransformName = 'SK_Male'
RootTransformRot = [-90, 90, 0]
RootTransformLoc = [0, 0, 0]

#用于表现当前 视频处理进度的 进度条
ProgressMax = 100
ProgressNearMax = 90
ExecuteInterval = 1
ThreadLock = threading.Lock()

#主要用于 视频的上传-》处理-》下载流程 
#每一步基本都有 初始化-》更新-》完成 几个阶段
class ProcessState(Enum):
    INIT = 0
    UPDATE = 1
    NEAR_COMPLETE = 2
    COMPLETE = 3

#标记， Once代表执行一次， PERMANENT代表会持续执行，KILL代表直接结束
class ProcessFlag(Enum):
    ONCE = 1
    PERMANENT = 2
    KILL = 3

#Task 处理任务，当前设计不够通用， 先这么地吧
class ProcessTask:
    def __init__(self, TaskName, *TaskParams ):
        self.TaskName = TaskName
        self.TaskParams = TaskParams[0] 
        
#Classes   关节数据
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

#帧数据， 主要用于存放 每一帧的关节数据
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

#代表当前 Skinned节点数据，记录父子关系等       
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

#主要处理类，主要是 ui相关的处理流程都在这
class ImportAIMotionWithUI(object):

    def __init__(self):
        #Variables
        self.WindowId = 'ImportAnimUI'
        self.WindowTitle = 'ImportAnimUI'

        #Path EditWidth
        self.EditFieldWidth = 300
        self.ListenButton = None 
        self.ListenButtonColor = [.361,.361,.361]
        self.ListeningColor = [0,1,0]

        #progress 相关
        self.ProgressBar = None
        self.ProgressText = None
        self.CurrentProgress = 0
        self.bRunningProgress = False

        self.ProcessTaskQueue = deque()
        #当前只能有一个
        self.PermanentProgressTask = None
        self.ExcuteTimer = None
        

    #主要是用于 CommandPort通信，通过CommandPort发送代码参数过来
    def AddFrameData(self, FrameIndex, FrameData):
        
        FrameJointDatas = FrameData[0][0]

        Frame = self.GenerateFrameJoint(FrameJointDatas, FrameIndex)
        self.ConstructFrame(Frame)
        CurrentFrameDatas.append(Frame)

    #util functions 
    def LimitAngle(self, Angle):
        if Angle > 180:
            return Angle - 360 
        elif Angle < -180:   
            return Angle + 360
        return Angle

    def RoundHalfUp(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n*multiplier + 0.5) / multiplier

    def RoundDown(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier

    def RoundUp(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.ceil(n * multiplier) / multiplier

    #需要对 Pose3d的 旋转顺序进行转换
    def ConvertPos3dRotateToMaya(self, JointValue):
        NewRot = [self.RoundHalfUp(JointValue[3], 3) , self.RoundHalfUp(JointValue[4], 3), self.RoundHalfUp(JointValue[5], 3)]
        return [NewRot[1], NewRot[2], NewRot[0]]

    #Pose3d 坐标转换
    def ConvertPos3dAxisValueToMaya(self, JointValue):
        return [self.RoundHalfUp(JointValue[0], 3), self.RoundHalfUp(JointValue[1], 3), self.RoundHalfUp(JointValue[2], 3)]

    #ErrorMessage 
    def ErrorMessage(self, KeyMsg):
        cmds.confirmDialog(title='Error Message', message=ErrorMsgTypeStr[KeyMsg], button=['Ok'])
        print ("ErrorMsg: %s" % (ErrorMsgTypeStr[KeyMsg])  )


    def ApplyNpzFile(self, File):
        print('apply npz file')
        global Pose3dData, Pose3dTPose
        Pose3dData, Pose3dTPose = self.LoadPose3dData(File)

        #根据npz t-pose创建 t-pose数据
        self.CreateTPoseData()
        #根据 T-pose数据生成关节
        self.CreateJoints()
        #创建所有 帧数据
        self.GenerateFrameJointDatas()
        #生成关键帧
        self.GenerateFrames()

    #ApplyFile
    def ApplyFile(self, pImportField, *pArgs):
        File = cmds.textField(pImportField, query=True, text=True)
        if not File or File == '':
            self.ErrorMessage('FileNotNull')
            return
        #print ('Apply File: %s' % File  )   
        self.ApplyNpzFile(File)

    #ApplyTPoseFile
    def ApplyTPoseFile(self, pImportField, *pArgs):
        File = cmds.textField(pImportField, query=True, text=True)
        if not File or File == '':
            self.ErrorMessage('FileNotNull')
            return

        global Pose3dData, Pose3dTPose
        Pose3dData, Pose3dTPose = self.LoadPose3dData(File)
        #根据npz t-pose创建 t-pose数据
        self.CreateTPoseData()
        #根据 T-pose数据生成关节
        self.CreateJoints()
        #清理帧， 防止之前残留
        self.ClearKeys()
        
    #ImportFromAnimFilePath :直接复制文件路径进去，点击Apply， 或者Browse选择.npz文件
    def OpenImportFileDialog(self, pImportField, *pArgs):
        Path = cmds.fileDialog2(fileFilter='*.npz', dialogStyle=2, fileMode=1, cap='Select Import File')
        if Path:
            cmds.textField(pImportField, edit=True, text=Path[0])
            #print ('Import From Anim File:%s '% (Path))

    #同上
    def OpenImportTPoseFileDialog(self, pImportField, *pArgs):
        Path = cmds.fileDialog2(fileFilter='*.npz', dialogStyle=2, fileMode=1, cap='Select Import File')
        if Path:
            cmds.textField(pImportField, edit=True, text=Path[0])
            
            #print ('Import From Anim File:%s '% (Path))
        self.bRunningProgress = False

    #选择上传视频
    def OpenImportVideoDialog(self, pImportField, *pArgs):
        Path = cmds.fileDialog2(fileFilter='*.mp4', dialogStyle=2, fileMode=1, cap='Select Import File')
        if Path:
            cmds.textField(pImportField, edit=True, text=Path[0])
            print ('Import Video File:%s '% (Path))

    #进度任务 处理
    def UpdateProcess(self):
        if not self.bRunningProgress:
            return 

        #期望一帧不要把所有的 Progress过程都执行完，不然看不到UI表现，一帧执行一个ProgressTask
        #Premanent的除外
        ThreadLock.acquire()
        #Task不为空
        if self.ProcessTaskQueue:
            ProgressTask = self.ProcessTaskQueue.pop()
            if ProgressTask.TaskName == 'ProgressBar':
                CurProcessState = ProgressTask.TaskParams[0]
                ProcessFlag = ProgressTask.TaskParams[1]
                ProcessTip = ProgressTask.TaskParams[2]

                if ProcessFlag == ProcessFlag.PERMANENT:
                    self.PermanentProgressTask = ProgressTask

                if ProcessFlag == ProcessFlag.ONCE:
                    if CurProcessState == ProcessState.INIT:
                        cmds.progressBar(self.ProgressBar, edit=True, progress=0)
                        cmds.text( self.ProgressText, edit=True, label=ProcessTip)
                        self.CurrentProgress = 0
                    elif CurProcessState == ProcessState.COMPLETE:
                        cmds.progressBar(self.ProgressBar, edit=True, progress=ProgressMax)
                        self.PermanentProgressTask = None

                if ProcessFlag == ProcessFlag.KILL:
                    if CurProcessState == ProcessState.COMPLETE:
                        cmds.progressBar(self.ProgressBar, edit=True, progress=ProgressMax)
                        self.bRunningProgress = False
                        self.PermanentProgressTask = None
            elif ProgressTask.TaskName == 'LoadNpz':
                NpzName = ProgressTask.TaskParams[0]
                self.ApplyNpzFile(NpzName)
    
        if self.PermanentProgressTask:
            PermanentTaskState = self.PermanentProgressTask.TaskParams[0]
            if PermanentTaskState == ProcessState.UPDATE:
                #最多更新到 NearMax， 不更新到100%
                Num = random.randint(1, 5)
                if self.CurrentProgress + Num > ProgressNearMax:
                    Num = ProgressNearMax - self.CurrentProgress if ProgressNearMax > self.CurrentProgress else 0
                    self.CurrentProgress = ProgressMax
                else:
                    self.CurrentProgress = self.CurrentProgress + Num 
                cmds.progressBar(self.ProgressBar, edit=True, step=Num)
            elif PermanentTaskState == ProcessState.NEAR_COMPLETE:
                cmds.progressBar(self.ProgressBar, edit=True, progress=ProgressNearMax)

        ThreadLock.release()

    def Run(self):
        self.CreateSkinnedNodes()
        self.CreateImportUI()
        self.CheckPyConnectState()

    #起本地的 处理更新流程，主要用于update进度条
    def StartProcess(self):
        self.bRunningProgress = True 
        if not self.ExcuteTimer:
            self.ExcuteTimer = QtCore.QTimer()
            self.ExcuteTimer.timeout.connect(self.UpdateProcess)

        self.ExcuteTimer.start(ExecuteInterval * 1000)

    #添加 处理任务
    def AddProcessTask(self, TaskName, *TaskParams):
        ThreadLock.acquire()
        print('task name %s %s' % (TaskName, TaskParams))
        self.ProcessTaskQueue.appendleft(ProcessTask(TaskName, TaskParams))
        ThreadLock.release()
        

    #上传视频，创建视频上传下载线程
    def UploadVideo(self, pImportField, *pArgs):
        
        File = cmds.textField(pImportField, query=True, text=True)
        if not File or File == '':
            self.ErrorMessage('FileNotNull')
            return
        self.StartProcess()
        MotionCoreIns = MotionCore.AiMotionCore()
        ProcessVideo = MotionCoreIns.GetProcessVideo()
        ProcessVideo.StartProcess(File)

    # def CheckCurrentTposeData(self):
    #     #假设当前已经导入了 合适的骨架模型， 选中Root
    #     try:
    #         cmds.select(RootTransformName)
    #     except ValueError as Err:
            #if Err == 'No object matches name':
                #self.ErrorMessage('NoSk_Male')
            
        # SelectRoot = cmds.ls(orderedSelection=True, type='transform')
        # SelectRoot = SelectRoot[0]
        # print('select root :%s' % (SelectRoot))

    #当前Window关闭，需要把TimerStop
    def WindowClose(self):
        self.bRunningProgress = False
        if self.ExcuteTimer:
            self.ExcuteTimer.stop()

    #代码创建UI的逻辑 都在这里
    def CreateImportUI(self):
        if cmds.window(self.WindowId, exists=True):
            cmds.deleteUI(self.WindowId)
        
        cmds.window(self.WindowId, title=self.WindowTitle, sizeable=False, resizeToFitChildren = True, width=600, height=113, closeCommand=self.WindowClose)

        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        cmds.separator()
        cmds.text('Work Offline')
        cmds.separator()
        #cmds.window(self.WindowId, title=self.WindowTitle, sizeable=False, resizeToFitChildren=True )
        
        #columnWidth=[ (1,75)..] means subIndex=1 column with is 75
        #the parameters will fill from 1st row to the last row, 
        cmds.rowColumnLayout(numberOfColumns=5, columnWidth=[(1, 80),(2, self.EditFieldWidth), (3, 80),(4, 80), (5, 80)], 
                            columnAlign = [(1, 'center'), (2, 'center'), (3, 'center'), (4, 'center'), (5, 'center')],
                            columnSpacing = [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)],
                            rowSpacing = [(2, 5), (2, 5), (3, 5), (4, 5), (5, 5)]                              )
                                                                                                            
        #anim file to apply                                                                    
        cmds.text(label='AnimFile:')
        filePathField = cmds.textField(text='', width = self.EditFieldWidth)
        cmds.button(label='FileBrowser', command = functools.partial(self.OpenImportFileDialog,
                                                                    filePathField))
        cmds.button(label='ApplyFile', command = functools.partial(self.ApplyFile,
                                                                    filePathField))

        def ResetToDefault(*pArgs):
            if Pose3dTPose.size == 0:
                self.ErrorMessage('LoadDefaultT-PoseError')

            self.ClearKeys()
            self.ResetToTPose()

        cmds.button(label='Reset2TPose', command=ResetToDefault)

        cmds.setParent('..')
        cmds.separator()
        cmds.text('Work Realtime')
        cmds.separator()

        cmds.rowColumnLayout(numberOfColumns=6, columnWidth=[(1, 80),(2, self.EditFieldWidth), (3, 80),(4, 80), (5, 95)], 
                            columnAlign = [(1, 'center'), (2, 'center'), (3, 'center'), (4, 'center'), (5, 'center')],
                            columnSpacing = [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)],
                            rowSpacing = [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)] )    

        #anim file to apply                                                                    
        cmds.text(label='TPoseFile:')
        tPosefilePathField = cmds.textField(text='', width = self.EditFieldWidth)
        cmds.button(label='FileBrowser', command = functools.partial(self.OpenImportTPoseFileDialog,
                                                                    tPosefilePathField))
        cmds.button(label='ApplyT-Pose', command = functools.partial(self.ApplyTPoseFile,
                                                                    tPosefilePathField))

        def CreateConnection(*pArgs):
            self.ListenToFrameData()
        self.ListenButton = cmds.button(label='CreateConnection', command = CreateConnection)

        # def CloseConnection(*pArgs):
        #     self.StopListen()
        # cmds.button(label='CloseConnection', command = CloseConnection)

        cmds.setParent('..')
        cmds.separator()
        cmds.text('Realtime Video or Live Camera Process')
        cmds.separator()

        cmds.rowColumnLayout(numberOfColumns=6, columnWidth=[(1, 80),(2, self.EditFieldWidth), (3, 80),(4, 80), (5, 90)], 
                            columnAlign = [(1, 'center'), (2, 'center'), (3, 'center'), (4, 'center'), (5, 'center')],
                            columnSpacing = [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)],
                            rowSpacing = [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)] ) 

        #anim file to apply                                                                    
        cmds.text(label='Video File:')
        tVideofilePathField = cmds.textField(text='', width = self.EditFieldWidth)
        cmds.button(label='FileBrowser', command = functools.partial(self.OpenImportVideoDialog,
                                                                    tVideofilePathField))
        cmds.button(label='Upload Video', command = functools.partial(self.UploadVideo,
                                                                    tVideofilePathField))

        cmds.setParent('..')
        cmds.separator()

        cmds.rowColumnLayout(numberOfColumns=6, columnWidth=[(1, 120),(2, self.EditFieldWidth), (3, 80),(4, 80), (5, 90)], 
                            columnAlign = [(1, 'center'), (2, 'center'), (3, 'center'), (4, 'center'), (5, 'center')],
                            columnSpacing = [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)],
                            rowSpacing = [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)] ) 


        self.ProgressText = cmds.text(label='Current Progress:')
        self.ProgressBar = cmds.progressBar(maxValue=ProgressMax, width=500)

        cmds.setParent('..')
        cmds.separator()

        cmds.showWindow()

    #KeyJointAttribute 创建关节属性关键帧
    def KeyJointAttribute(self, pObjectName, pKeyFrame, pAttribute, value):    
        cmds.setKeyframe(pObjectName, time=pKeyFrame, attribute=pAttribute, value=value)
        cmds.keyTangent(inTangentType='linear', outTangentType='linear')
            
    #创建关节 位移
    def KeyJointTranslate(self, pObjectName, pKeyFrame, Translate):   
        self.KeyJointAttribute(pObjectName, pKeyFrame, 'translateX', Translate[0])
        self.KeyJointAttribute(pObjectName, pKeyFrame, 'translateY', Translate[1])
        self.KeyJointAttribute(pObjectName, pKeyFrame, 'translateZ', Translate[2])

    #创建关节 旋转
    def KeyJointRotate(self, pObjectName, pKeyFrame, Rotate):
        self.KeyJointAttribute(pObjectName, pKeyFrame, 'rotateX', Rotate[0])
        self.KeyJointAttribute(pObjectName, pKeyFrame, 'rotateY', Rotate[1])
        self.KeyJointAttribute(pObjectName, pKeyFrame, 'rotateZ', Rotate[2])

    #创建关节 缩放
    def KeyJointScale(self, pObjectName, pKeyFrame, Scale):
        self.KeyJointAttribute(pObjectName, pKeyFrame, 'scaleX', Scale[0])
        self.KeyJointAttribute(pObjectName, pKeyFrame, 'scaleY', Scale[1])
        self.KeyJointAttribute(pObjectName, pKeyFrame, 'scaleZ', Scale[2])

    #重置T-pose数据
    def ResetToTPose(self):
        cmds.setAttr('%s.rotate' % (RootTransformName), RootTransformRot[0], RootTransformRot[1], RootTransformRot[2], type="double3")
        cmds.setAttr('%s.translate' % (RootTransformName), RootTransformLoc[0], RootTransformLoc[1], RootTransformLoc[2], type="double3")
        for Index in SkinnedNodesDatas:
            SkinnNodeData = SkinnedNodesDatas[Index]
            Name = SkinnNodeData.GetName()
            PosJoint = SkinnNodeData.GetPositionInTPose()
            cmds.setAttr('%s.rotate' % (Name), 0, 0, 0, type="double3")
            cmds.setAttr('%s.translate' % (Name), PosJoint[0], PosJoint[1], PosJoint[2], type="double3")
            cmds.xform(Name, preserve=True, rotateOrder='yxz')

    #清理 所有帧数据
    def ClearKeys(self):
        #删除当前时间线的起始跟结束帧数据
        StartTime = cmds.playbackOptions(query=True, minTime=True)
        EndTime = cmds.playbackOptions(query=True, maxTime=True)
        
        global SkinnedNodesDatas
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

    #检查当前CommandPort连接状态
    def CheckPyConnectState(self):
        PyPortStr = ':%s'%(ListenPort)
        bConnected = cmds.commandPort( PyPortStr, q = True)
        if bConnected:
            cmds.button(self.ListenButton, label='Connected', edit=True, backgroundColor=self.ListeningColor)
        else: 
            cmds.button(self.ListenButton, label='CreateConnection', edit=True, backgroundColor=self.ListenButtonColor)

    #创建 关节节点树
    def CreateSkinnedNodes(self):
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
            17:SkinnedNodeData('foot_l_end', 'joint', 'foot_l', 'joint', 6),
            18:SkinnedNodeData('foot_r_end', 'joint', 'foot_r', 'joint', 3),
            19:SkinnedNodeData('hand_l_end', 'joint', 'hand_l', 'joint', 13),
            20:SkinnedNodeData('hand_r_end', 'joint', 'hand_r', 'joint', 16),
        }

    def IsWishParent(self, Current, WishParent, WishParentType):
        PName = cmds.listRelatives(Current, parent=True, type=WishParentType)
        if PName and PName[0] == WishParent:
            return True
        return False

    #加载Npz文件， 初始化Npz数据
    def LoadPose3dData(self, Pose3dPath):
        Pose3dNpz = np.load(Pose3dPath)
        GroupPose3d = Pose3dNpz['n_frames_3d']
        GroupTPose = Pose3dNpz['n_t_pose']

        global StartFrame, EndFrame, Progress, ProgressEnd, TotalFrame
        #GroupPose3d.shape:4维  (几个人， 帧数， 关节数目， 关节数据：平移、旋转)
        TotalFrame = GroupPose3d.shape[1]

        StartFrame = 0
        EndFrame = TotalFrame - 1
        Progress = 0
        ProgressEnd = TotalFrame
        return GroupPose3d, GroupTPose

    #CreateTPoseData
    #根据npz t-pose创建 t-pose数据
    def CreateTPoseData(self):
        JointDatas = Pose3dTPose[0]
        for i in range(len(JointDatas)):
            Point = self.ConvertPos3dAxisValueToMaya(JointDatas[i])
            Len = OM.MVector(Point[0],Point[1], Point[2]).length()
            SkinnedNodesDatas[i].SetJointLength(Len)
            SkinnedNodesDatas[i].SetPositionInTPose(Point)

    #CreateJoints
    #根据创建好的 T-pose数据，在maya创建 关节
    def CreateJoints(self):
        #取消Outliner选中
        cmds.select( d=True )

        #create root transform
        if not cmds.objExists(RootTransformName):
            cmds.createNode("transform", name=RootTransformName)

        cmds.setAttr('%s.rotate' % (RootTransformName), RootTransformRot[0], RootTransformRot[1], RootTransformRot[2], type="double3")
        cmds.setAttr('%s.translate' % (RootTransformName), RootTransformLoc[0], RootTransformLoc[1], RootTransformLoc[2], type="double3")

        #create pelvis
        PelvisName = SkinnedNodesDatas[0].GetName()
        
        #没有盆骨 先创建
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
        cmds.setAttr('%s.rotate' % (PelvisName), 0, 0, 0, type="double3")
            
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
                if not self.IsWishParent(Name, SkinnNodeData.GetParent(), SkinnNodeData.GetParentType()):
                    cmds.parent(Name, SkinnNodeData.GetParent())

                PosJoint = SkinnNodeData.GetPositionInTPose()
                cmds.setAttr('%s.translate' % (Name), PosJoint[0], PosJoint[1], PosJoint[2], type="double3")
                cmds.setAttr('%s.rotate' % (Name), 0, 0, 0, type="double3")

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

    #生成  帧关节数据
    def GenerateFrameJoint(self, JointDatas, FrameIndex):          
        FrameJointDatas = {}
        global DefaultTPoseFrameData
        #init to default t-pose first
        DefaultJointDatas = DefaultTPoseFrameData.GetJointDatas()
        for Name in DefaultJointDatas:
            T = DefaultJointDatas[Name].GetTranslate()
            R = DefaultJointDatas[Name].GetRotate()
            S = DefaultJointDatas[Name].GetScale()
            FrameJointDatas[Name] = JointData(Name, [T[0], T[1], T[2]],
                                            [R[0], R[1], R[2]],
                                            [S[0], S[1], S[2]])

        #TODO: 将来如果需要支持RootMotion在这里 需要判断一下，把 JointDatas[0]单独拿出来，将translate的关键帧 SetTranslate加进去
        for i in range(len(JointDatas)):
            JointName = SkinnedNodesDatas[i].GetName()
            TargetRotate = self.ConvertPos3dRotateToMaya(JointDatas[i])
            FrameJointDatas[JointName].SetRotate(TargetRotate)
        
        return FrameData(FrameIndex, FrameJointDatas)

    #读取所有帧数据
    def GenerateFrameJointDatas(self):
        global Progress, ProgressEnd, TotalFrame, CurrentFrameDatas
        cmds.select( d=True )
        Progress = 0 
        CurrentFrameDatas = []
        for i in range(TotalFrame):
            Progress += 1.0
            
            Num = Progress / ProgressEnd * 100
            print ('FrameData Progress:: %.1f%%' % (Num))
            
            JointDatas = Pose3dData[0][i]
            Frame = self.GenerateFrameJoint(JointDatas, i)
            CurrentFrameDatas.append(Frame)

    #根据帧数据 生成maya关键帧
    def ConstructFrame(self, Frame):
        FrameIndex = Frame.GetFrameIndex()  
        JointDatas = Frame.GetJointDatas()
        cmds.currentTime(FrameIndex, edit=True)
        for JointName in JointDatas:
            Joint = JointDatas[JointName]
            if Joint:
                self.KeyJointTranslate(JointName, FrameIndex, Joint.GetTranslate())
                self.KeyJointRotate(JointName, FrameIndex, Joint.GetRotate())
                self.KeyJointScale(JointName, FrameIndex, Joint.GetScale())

    #生成 maya关键帧
    def GenerateFrames(self):
        #清理遗留关键帧
        self.ClearKeys()

        global Progress, ProgressEnd, CurrentFrameDatas
        Progress = 0 
        #generate frame key
        for Frame in CurrentFrameDatas:
            Progress += 1.0
            print ('AnimKey Process:: %.1f%%' % (Progress / ProgressEnd * 100))
            Num = Progress / ProgressEnd * 100
            cmds.progressBar(self.ProgressBar, edit=True, progress=Num)
            self.ConstructFrame(Frame)

    #监听 CommandPort指令输入
    def ListenToFrameData(self):
        PyPortStr = ':%s'%(ListenPort)

        bConnected = cmds.commandPort( PyPortStr, q = True)
        if not bConnected:
            cmds.commandPort(n = PyPortStr, stp = 'python')
            bConnected = True
                
        if bConnected:
            cmds.button(self.ListenButton, label='Connected', edit=True, backgroundColor=self.ListeningColor)
        else: 
            cmds.button(self.ListenButton, label='CreateConnection', edit=True, backgroundColor=self.ListenButtonColor)


    # def StopListen(self):
    #     PyPortStr = ':%s'%(ListenPort)
    #     try:
    #         if cmds.commandPort( PyPortStr, q = True):
    #             print('founded can close')
    #             cmds.commandPort(n = PyPortStr, close = True)
    #     except:
    #         cmds.warning('could not close port %s' % PyPortStr)
    #     cmds.button(self.ListenButton, label='CreateConnection', edit=True, backgroundColor=self.ListenButtonColor)

if __name__ == "__main__":
    dialog = ImportAIMotionWithUI()






  


