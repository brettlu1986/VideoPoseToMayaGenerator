#keyRotationWithUI

import maya.cmds as cmds
import functools

def createUI(pWindowTitle, pApplyCallBack):
    windowId = 'myWindowId'

    if cmds.window(windowId, exists=True):
        cmds.deleteUI(windowId)
    #cmds.window(windowId, title=pWindowTitle, sizeable=False, width=413, height=113 )
    cmds.window(windowId, title=pWindowTitle, sizeable=False, resizeToFitChildren=True )
     
    #columnWidth=[ (1,75)..] means subIndex=1 column with is 75
    #the parameters will fill from 1st row to the last row, 
    cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 75),(2, 60),(3, 60)], columnOffset=[(1, 'right', 3)])
  
    #these code fill the first rows, from left to right
    cmds.text(label='TimeRange:')
    startTimeField = cmds.intField(value=cmds.playbackOptions(q=True, minTime=True))
    endTimeField = cmds.intField(value=cmds.playbackOptions(q=True, maxTime=True))

    #second row
    cmds.text(label='Attribute:')
    targetAttributeField = cmds.textField(text='rotateY')
    cmds.separator(h=10, style='none') #ocuppy the space
    
    #make a space row
    cmds.separator(h=10, style='none')
    cmds.separator(h=10, style='none')
    cmds.separator(h=10, style='none')
    #the forth line
    cmds.separator(h=10, style='none')
    cmds.button(label='Apply', command = functools.partial(pApplyCallBack,
                                                            startTimeField,
                                                            endTimeField,
                                                            targetAttributeField))
    
    def cancelCallBack(*pArags):
        if cmds.window(windowId, exists=True):
            cmds.deleteUI(windowId)
    
    cmds.button(label='Cancel', command=cancelCallBack)

    cmds.showWindow()
    
def KeyFullRotation(pObjectName, pStartTime, pEndTime, pAttribute):
    cmds.cutKey(pObjectName, time=(pStartTime, pEndTime), attribute=pAttribute)
    cmds.setKeyframe(pObjectName, time=pStartTime, attribute=pAttribute, value=0)
    cmds.setKeyframe(pObjectName, time=pEndTime, attribute=pAttribute, value=360)
    cmds.selectKey(pObjectName, time=(pStartTime, pEndTime), attribute=pAttribute)
    cmds.keyTangent(inTangentType='linear', outTangentType='linear')
    
def applyCallBack( pStartTimeField, pEndTimeField, pTargetAttributeField, *pArgs):
    
    startTime = cmds.intField(pStartTimeField, query=True, value=True)
    endTime = cmds.intField(pEndTimeField, query=True, value=True)
    targetAttribute=cmds.textField(pTargetAttributeField, query=True, text=True)
    
    selectionList = cmds.ls(selection=True, type='transform')
    for objectName in selectionList:
        KeyFullRotation(objectName, startTime, endTime, targetAttribute)
    print 'Apply Button Pressed'
    
createUI('MyTitle', applyCallBack)
    