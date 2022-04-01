import site
import importlib


import os

RootDir = os.path.dirname(os.path.abspath('.'))
PyPath = RootDir + '/VideoPoseToMayaGenerator/Python'

site.addsitedir(PyPath)


import AIMotionToMaya 
importlib.reload(AIMotionToMaya)


MotionIns = AIMotionToMaya.ImportAIMotionWithUI()
MotionIns.Run()

# import threading
# import time
# import subprocess

# def Update1(Interval):

#     print('begin upload')
#     BaseIp = '120.92.33.226'
#     RemoteSavePath = '/tmp/models/results/'
#     UploadHost = 'sftp://%s%s' % (BaseIp,RemoteSavePath)
#     UserName = 'ubuntu'
#     Password = 'Wws849529..'

#     File = 'D:/Projects/AI/GAST-Net-3DPoseEstimation/video/Pure-Land-female1.mp4'
#     UploadCommand = 'curl --insecure --user %s:%s -T %s %s' % (UserName,Password,File,UploadHost)
#     p = subprocess.Popen(UploadCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     out, info = p.communicate()
#     print('end upload')
#     while True:
#         print('111')
#         time.sleep(Interval)

# def Update2(Interval):
#     while True: 
#         print('222')
#         time.sleep(Interval)
        

# T1 = threading.Thread(None, target=Update1, args = (1, ))
# T1.start()

# T2 = threading.Thread(None, target=Update2, args = (1, ))
# T2.start()



# from pyqtgraph.Qt import QtCore
# import maya.cmds as cmds

# def update():
#     print('update now')

# timer = QtCore.QTimer()
# timer.timeout.connect(update)
# timer.start(1000)


# def defaultButtonPush(*args):
#     print('press to stop')
#     global timer
#     timer.stop()

# window = cmds.window()
# cmds.columnLayout()
# cmds.button( label='Make Progress!', command=defaultButtonPush )
# cmds.showWindow( window )

# import maya.cmds as cmds
# import maya.utils as utils

# import threading
# import time

# bRunning = False
# ExecuteInterval = 1
# Count = 0

# def Progress():
#     global Count, bRunning
#     Count = Count + 1
#     if Count > 20:
#         bRunning = False
#     print('progress on %s' % Count)

# def Loop(Interval, ):
#     global bRunning
    
#     while bRunning:
#         utils.executeDeferred(Progress)
#         time.sleep(Interval)
        
#     print('timer run finish')

# bRunning = True
# T = threading.Thread(None, target=Loop, args = (ExecuteInterval,))
# T.start()
# print('excute over')


# from collections import deque

# q = deque()

# q.appendleft(1)
# q.appendleft(2)
# q.appendleft(3)

# while q:
#     v = q.pop()
#     print(v)

# print('enum over')

# import maya.cmds as cmds
# cmds.window( width=150 )
# cmds.columnLayout( adjustableColumn=True )
# textIns = cmds.text( label='Default' )
# cmds.text( textIns, edit=True, label='Left' )
# cmds.showWindow()



# import maya.cmds as cmds
# window = cmds.window()
# cmds.columnLayout()
# progressControl = cmds.progressBar(maxValue=100, width=400)
# cmds.progressBar(progressControl, edit=True, step=10)
# cmds.button( label='Make Progress!', command='cmds.progressBar(progressControl, edit=True, progress=0)' )
# cmds.showWindow( window )


