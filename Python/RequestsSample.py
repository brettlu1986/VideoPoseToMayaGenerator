# curl -k https://120.92.100.80:8436/predictions/pose_tracker -d "path=/tmp/pose_test.mp4"
# curl -k https://120.92.100.80:8436/predictions/pose_tracker -T /home/wangwensheng/Downloads/GitLab/GAST-Net-3DPoseEstimation/deploy/test_data/x4.png
# curl -k https://120.92.100.80:8436/predictions/stylegan -T /home/wangwensheng/Downloads/GitLab/GAST-Net-3DPoseEstimation/deploy/test_data/x3.png


#
# sftp://120.92.14.177  ubuntu  Wws849529..
# import requests
# DowloadUrl = "https://ftp.shiyou.kingsoft.com/personal/luzheng/Crazy-Pose_standard_1s233.npz"
# SaveFile = "D:/Projects/AI/VideoPoseToMayaGenerator/Pose3dNPZ_Files/Crazy-Pose.npz"
# DownloadResponse = requests.get(DowloadUrl)
# with open(SaveFile, 'wb') as f:
#     f.write(DownloadResponse.content)


#  D:\ProgrameInstalls\AutoDesk\Maya2022\Maya2022\bin\maya.exe -file Man.mb
#  echo %PYTHONUSERBASE%
#  set PYTHONUSERBASE=D:\Projects\AI\VideoPoseToMayaGenerator\EmptyTest

#curl成功 sftp： 关键在于 --insecure,  upload的 sftp地址最后要加对应 remote目录 /
#curl --insecure --user ubuntu:Wws849529.. -T Crazy-Pose_lz.mp4 sftp://120.92.14.177/tmp/models/results/


#curl成功例子 ftp
#curl -T 1.txt -u "rog2kfadmin:Rog2kingsoft@456@" ftp://ftp.shiyou.kingsoft.com/personal/luzheng/
#curl -T Crazy-Pose.mp4 -u "rog2kfadmin:Rog2kingsoft@456@" ftp://ftp.shiyou.kingsoft.com/personal/luzheng/


# requests 下载 示例， 上传一直没有成功
'''
# DowloadUrl = "https://ftp.shiyou.kingsoft.com/personal/luzheng/FF7RE-CLOUD.mp4"
# SaveFile = "D:/Projects/AI/VideoPoseToMayaGenerator/Pose3dNPZ_Files/test.mp4"
# DownloadResponse = requests.get(DowloadUrl)
# with open(SaveFile, 'wb') as f:
#     f.write(DownloadResponse.content)
'''

#FTP上传下载示例
'''
import os
from ftplib import FTP

#这个地方不能加 personal/luzheng类似这样的目录， 否则 ftp会链接不上
FTPTarget = self.FtpConnect('ftp.shiyou.kingsoft.com', 21, 'rog2kfadmin', 'Rog2kingsoft@456@', 2)

# #模拟上传
if FTPTarget:
    self.FtpUpload(File, '/personal/luzheng/')

#模拟下载
if FTPTarget:
    FileName = 'pose_meixi_standard_1s2222.npz'
    SaveDir = "D:/Projects/AI/VideoPoseToMayaGenerator/Pose3dNPZ_Files/" + FileName
    self.FtpDownload(FileName, '/personal/luzheng/', SaveDir )

def ScpUpload(self, Host, UserName, PassWord, File):
	#ssh = SSHClient()
	print('')
	
def FtpConnect(self, Host, Port, UserName, PassWord, DebugLevel):
	TheFtp = FTP()
	TheFtp.set_pasv(False)
	TheFtp.set_debuglevel(DebugLevel)
	TheFtp.connect(Host, Port)
	TheFtp.login(UserName, PassWord)
	return TheFtp
	

def FtpUpload(self, UploadFile, RemotePath, DebugLevel = 0):
	BuffSize = os.path.getsize(UploadFile)
	Fp = open(UploadFile, 'rb')
	#测试 显示当前目录
	#FTPTarget.dir()
	#链接上来之后，需要先cmd到指定的path
	FTPTarget.cwd(RemotePath)

	SaveFileName = UploadFile[UploadFile.rfind('/') + 1:]
	FTPTarget.storbinary('STOR ' + SaveFileName, Fp, BuffSize)

	FTPTarget.set_debuglevel(DebugLevel)
	FTPTarget.close()

#FTP lib下载
def FtpDownload(self, DoneloadFile, RemotePath, LocalDirectory):
	Fp = open(LocalDirectory, 'wb')

	FTPTarget.cwd(RemotePath)
	FTPTarget.retrbinary('RETR ' + DoneloadFile, Fp.write)
	FTPTarget.close()
'''

#scp 上传下载  单独再python3.9的系统版本是可行的， 在mayapy 3.7的环境下， import paramiko会崩溃， 原因未知，唉
'''
from scp import SCPClient
import paramiko
from paramiko import SSHClient

#upload
File = 'D:/Projects/AI/VideoPoseToMayaGenerator/Videos/FF7RE-CLOUD.mp4'
UploadAddr = '120.92.100.80'

#down load 
#SavePath = 'D:\Projects\AI\VideoPoseToMayaGenerator\Pose3dNPZ_Files'
#DownloadAddr = '120.92.100.80:8433'

def Progress(filename, size, sent):
	print("%s's progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )

username = 'ubuntu'
password = 'Wws849529..'

ssh = SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ssh.connect(hostname=UploadAddr, username=username, password=password)
with SCPClient(ssh.get_transport(), progress=Progress) as scp:
	#upload
	scp.put(File, remote_path='/tmp')
	#download 
	#scp.get('/tmp/models/results/fake0.exr', SavePath)
	
scp.close()
ssh.close()
'''