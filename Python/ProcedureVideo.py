import subprocess
import requests
import threading
import os
import AiMotionCore as MotionCore
import time

from AIMotionToMaya import ProcessState
from AIMotionToMaya import ProcessFlag

ExecuteInterval = 1

#主要用于 处理视频上传-》处理-》下载流程的线程类
class ProcedureVideo:

    def __init__(self):
        self.VideoFile = None

    def ProcessRun(self, Interval, File):
        VideoFile = File[File.rfind('/') + 1:]
        VideoName = VideoFile.split('.')[0]

        BaseIp = '120.92.82.74'
        RemoteSavePath = '/tmp/models/results/'
        UploadHost = 'sftp://%s%s' % (BaseIp,RemoteSavePath)
        UserName = 'ubuntu'
        Password = 'Wws849529..'
        
        #1.upload
        MotionCoreIns = MotionCore.AiMotionCore()

        MotionToMaya = MotionCoreIns.GetProcessMotionMaya()
        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.INIT, ProcessFlag.ONCE, 'Upload Video')
        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.UPDATE, ProcessFlag.PERMANENT, '')

        print('begin upload')
        try:
            UploadCommand = 'curl --insecure --user %s:%s -T %s %s' % (UserName,Password,File,UploadHost)
            p = subprocess.Popen(UploadCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, info = p.communicate()
        except: 
            self.ErrorMessage('UploadError')
        else:
            print('upload end')

        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.NEAR_COMPLETE, ProcessFlag.PERMANENT, '')
        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.COMPLETE, ProcessFlag.ONCE, '')
  
        #2. send remote upload video file path to notify server can process
        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.INIT, ProcessFlag.ONCE, 'Process Video')
        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.UPDATE, ProcessFlag.PERMANENT, '')

        RemoteUploadPath = RemoteSavePath + VideoFile
        ProcessVideoHost = 'https://%s:8436/predictions/pose_tracker' % BaseIp
        Response = requests.post(ProcessVideoHost, data = {'path':RemoteUploadPath}, verify=False)

        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.NEAR_COMPLETE, ProcessFlag.PERMANENT, '')
        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.COMPLETE, ProcessFlag.ONCE, '')
        print('Response.text:: %s' % Response.text)

        #3.download npz file
        Content = Response.text.split(":")
        SubIndex = Content[1].find(' ')
        DownloadPath = Content[1][:SubIndex]
        ExtraPath = '_standard/bvh/%s_standard_1s.npz' % VideoName
        DownloadNpzHost = "https://%s:%s%s" % (BaseIp, DownloadPath, ExtraPath)
        print('DownloadNpzHost:%s' % DownloadNpzHost)

        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.INIT, ProcessFlag.ONCE, 'Download Bin')
        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.UPDATE, ProcessFlag.PERMANENT,'')

        DownloadNpzHost = 'http://%s:8433/%s_standard/bvh/%s_standard_1s.npz' % (BaseIp, VideoName, VideoName)
        #'http://120.92.14.177:8433/Crazy-Pose_lz_standard/bvh/Crazy-Pose_lz_standard_1s.npz'
        #'http://120.92.14.177:8433/tmp/models/results/Crazy-Pose_lz_standard/bvh/Crazy-Pose_lz_standard_1s.npz'
        RootDir = os.path.dirname(os.path.abspath('.'))
        SaveFile = RootDir + '/VideoPoseToMayaGenerator/Pose3dNPZ_Files/%s_standard_1s.npz' %(VideoName)

        DownloadResponse = requests.get(DownloadNpzHost)
        with open(SaveFile, 'wb') as f:
            f.write(DownloadResponse.content)

        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.NEAR_COMPLETE, ProcessFlag.PERMANENT,'')
        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.COMPLETE, ProcessFlag.ONCE,'')
        print(DownloadResponse.text)

        #4.apply download file
        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.INIT, ProcessFlag.ONCE, 'Generate Frame')

        MotionToMaya.AddProcessTask('LoadNpz', SaveFile)

        MotionToMaya.AddProcessTask('ProgressBar', ProcessState.COMPLETE, ProcessFlag.KILL,'')

    def StartProcess(self, File):
        T = threading.Thread(None, target=self.ProcessRun, args = (ExecuteInterval, File) )
        T.start()