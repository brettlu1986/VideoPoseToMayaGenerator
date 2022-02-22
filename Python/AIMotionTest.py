
import site
import importlib

site.addsitedir('D:/Projects/AI/VideoPoseToMayaGenerator/Python')

import AIMotionToMaya 
importlib.reload(AIMotionToMaya)


MotionIns = AIMotionToMaya.ImportAIMotionWithUI()
MotionIns.Run()