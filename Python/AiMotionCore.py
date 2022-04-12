
import ProcedureVideo as VideoProcess
import AIMotionToMaya as AIMotionMaya

#主要用于全局访问的 一个单例
class AiMotionCore:

    init_flag = False
    def __init__(self):

        if AiMotionCore.init_flag:
            return 

        self.ProcedureVideo = VideoProcess.ProcedureVideo()
        self.MotionMaya = AIMotionMaya.ImportAIMotionWithUI()

        AiMotionCore.init_flag = True

    def GetProcessVideo(self):
        return self.ProcedureVideo

    def GetProcessMotionMaya(self):
        return self.MotionMaya

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            orig = super(AiMotionCore, cls)
            cls._instance = orig.__new__(cls, *args, **kwargs)
        
        return cls._instance  