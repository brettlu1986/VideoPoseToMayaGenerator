
import site 
import importlib

import os
RootDir = os.path.dirname(os.path.abspath('.'))
PyPath = RootDir + '/VideoPoseToMayaGenerator/Python'
site.addsitedir(PyPath)

import AiMotionCore as MotionCore 
import AIMotionToMaya
import ProcedureVideo

importlib.reload(MotionCore)
importlib.reload(AIMotionToMaya)
importlib.reload(ProcedureVideo)

MotionCoreIns = MotionCore.AiMotionCore()

MotionToMaya = MotionCoreIns.GetProcessMotionMaya()
MotionToMaya.Run()



