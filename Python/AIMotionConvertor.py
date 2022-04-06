
import site 
import importlib

import os
RootDir = os.path.dirname(os.path.abspath('.'))
PyPath = RootDir + '/VideoPoseToMayaGenerator/Python'
site.addsitedir(PyPath)

import AiMotionCore as MotionCore 
import AIMotionToMaya
import ProcedureVideo

#maya issue: 不Reload的话 Python路径下的 Python代码修改会无效
importlib.reload(MotionCore)
importlib.reload(AIMotionToMaya)
importlib.reload(ProcedureVideo)

MotionCoreIns = MotionCore.AiMotionCore()

MotionToMaya = MotionCoreIns.GetProcessMotionMaya()
MotionToMaya.Run()



