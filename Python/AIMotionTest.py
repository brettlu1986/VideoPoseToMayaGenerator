
import site
import importlib

site.addsitedir('D:/Projects/AI/VideoPoseToMayaGenerator/Python')

import AIMotionToMaya 
importlib.reload(AIMotionToMaya)


MotionIns = AIMotionToMaya.ImportAIMotionWithUI()

#加载离线生成的 npz数据，包括关键帧
#MotionIns.WorkOffLine()

#创建默认的t-pose骨架，并监听 frame数据有就生成关键帧
MotionIns.WorkRealTime()