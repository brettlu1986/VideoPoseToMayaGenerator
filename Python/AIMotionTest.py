
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