import numpy, math, re, csv, os
from __main__ import vtk, qt, ctk, slicer


class MeshStats:
    def __init__(self, parent):
        parent.title = "Mesh Statistics"
        parent.dependencies = []
        parent.contributors = ["Lucie Macron"]
        parent.helpText = """
            """
        parent.acknowledgementText = """
            This module was developed by Lucie Macron, University of Michigan
            """
        self.parent = parent


class MeshStatsWidget:
    class StatisticStore(object):
        def __init__(self):
            self.min = 0
            self.max = 0
            self.mean = 0
            self.std = 0
            self.percentile15 = 0
            self.percentile50 = 0
            self.percentile75 = 0
            self.percentile95 = 0

    def __init__(self, parent=None):
        self.developerMode = True
        if not parent:
            self.parent = slicer.qMRMLWidget()
            self.parent.setLayout(qt.QVBoxLayout())
            self.parent.setMRMLScene(slicer.mrmlScene)
        else:
            self.parent = parent
        self.layout = self.parent.layout()
        
        if not parent:
            self.setup()
            self.parent.show()

    def setup(self):
        print " ----- SetUp ------"
        if self.developerMode:
            self.reloadButton = qt.QPushButton("Reload")
            self.reloadButton.toolTip = "Reload this module."
            self.reloadButton.name = "SurfaceToolbox Reload"
            self.layout.addWidget(self.reloadButton)
            self.reloadButton.connect('clicked()', self.onReload)
            
            self.testButton = qt.QPushButton("Test")
            self.layout.addWidget(self.testButton)
            self.testButton.connect('clicked()', self.testFunctions)

        # -------------------------------------------------------------------------------------
        self.logic = MeshStatsLogic()
        # Dictionary Of field. Keys = Name of the field
        self.fieldDictionary = dict()
        self.shapeList = list()
        self.arrayList = list()
        
        # ------------------------------------------------------------------------------------
        #                                    SHAPES INPUT
        # ------------------------------------------------------------------------------------
        self.inputComboBox = slicer.qMRMLCheckableNodeComboBox()
        self.inputComboBox.nodeTypes = ['vtkMRMLModelNode']
        self.inputComboBox.setMRMLScene(slicer.mrmlScene)
        inputLayout = qt.QFormLayout()
        inputLayout.addRow(" Shape: ", self.inputComboBox)
        self.layout.addLayout(inputLayout)

        self.inputComboBox.connect('checkedNodesChanged()', self.onInputComboBoxCheckedNodesChanged)
        # ------------------------------------------------------------------------------------
        #                                  ROI TABLE
        # ------------------------------------------------------------------------------------
        self.ROIComboBox = ctk.ctkComboBox()
        ROILayout = qt.QFormLayout()
        ROILayout.addRow(" Region considered: ", self.ROIComboBox)
        self.layout.addLayout(ROILayout)

        # ------------------------------------------------------------------------------------
        #                                  FIELD TABLE
        # ------------------------------------------------------------------------------------
        self.tableField = qt.QTableWidget()
        self.tableField.setColumnCount(2)
        self.tableField.setMinimumHeight(230)
        self.tableField.setHorizontalHeaderLabels([' ', 'Field Name'])
        self.tableField.setColumnWidth(0, 18)
        self.tableField.setColumnWidth(1, 210)

        fieldLayout = qt.QFormLayout()
        fieldLayout.addRow(" Field: ", self.tableField)
        self.layout.addLayout(fieldLayout)
        
        # ------------------------------------------------------------------------------------
        #                                    RUN
        # ------------------------------------------------------------------------------------
        self.runButton = qt.QPushButton(" Run ")
        self.runButton.enabled = False
        roiLayout = qt.QHBoxLayout()
        # roiLayout.setAlignment(2)
        roiLayout.addWidget(self.runButton)
        self.layout.addLayout(roiLayout)

        self.runButton.connect('clicked()', self.onRunButton)
        # ------------------------------------------------------------------------------------
        #                          Statistics Table - Export
        # ------------------------------------------------------------------------------------
        self.tab = qt.QTabWidget()
        # ---------------------------- Directory - Export Button -----------------------------
        self.exportButton = qt.QPushButton("Export")
        self.exportButton.enabled = True

        self.directoryExport = ctk.ctkDirectoryButton()

        self.exportCheckBox = qt.QCheckBox("Separate Files")
        self.exportCheckBox.setChecked(True)

        self.exportLayout = qt.QVBoxLayout()

        self.directAndCheckLayout = qt.QHBoxLayout()
        self.directAndCheckLayout.addWidget(self.directoryExport)
        self.directAndCheckLayout.addWidget(self.exportCheckBox)

        self.exportLayout.addLayout(self.directAndCheckLayout)
        self.exportLayout.addWidget(self.exportButton)
        self.updateInterface()

        # ------------------------------------------------------------------------------------
        #                                   OBSERVERS
        # ------------------------------------------------------------------------------------

        def onCloseScene(obj, event):
            print " --- OnCloseScene ---"
            # initialize Parameters
            globals()["MeshStats"] = slicer.util.reloadScriptedModule("MeshStats")

        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, onCloseScene)

    def updateInterface(self):
        self.runButton.enabled = not self.inputComboBox.noneChecked()
        self.tableField.clearContents()
        self.tableField.setRowCount(0)

        del self.arrayList[:]
        self.ROIComboBox.clear()
        self.ROIComboBox.addItem('Entire Shape')

        tableFieldNumRows = 0
        expression = r"ROI$"
        if self.shapeList:
            pointData = self.shapeList[0].GetModelDisplayNode().GetInputPolyData().GetPointData()
            numOfArray = pointData.GetNumberOfArrays()
            for i in range(0, numOfArray):
                self.arrayList.append(pointData.GetArray(i).GetName())
            print self.arrayList
            for arrayName in self.arrayList:
                bool = self.compareArray(self.shapeList, arrayName)
                print bool
                if bool:
                    if not re.search(expression, arrayName):
                        tableFieldNumRows += 1
                        self.tableField.setRowCount(tableFieldNumRows)
                        self.tableField.setCellWidget(tableFieldNumRows - 1, 0, qt.QCheckBox())
                        self.tableField.setCellWidget(tableFieldNumRows - 1, 1, qt.QLabel(arrayName))
                    else:
                        self.ROIComboBox.addItem(arrayName)
        self.layout.addStretch(1)

    def onInputComboBoxCheckedNodesChanged(self):
        self.shapeList = self.inputComboBox.checkedNodes()
        print self.shapeList
        self.updateInterface()

    def onExportButton(self):
        print self.exportCheckBox.isChecked()
        directory = self.directoryExport.directory
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(" /!\ WARNING /!\ ")
        messageBox.setIcon(messageBox.Warning)

        if self.exportCheckBox.isChecked(): # if exportation in different files
            for fieldName, shapeDict in self.fieldDictionary.iteritems():
                filename = directory + "/" + fieldName + ".csv"
                if os.path.exists(filename):
                    messageBox.setText("File " + fieldName + ".csv already exist in this folder.")
                    messageBox.setInformativeText("Do you want to replace it? ")
                    messageBox.setStandardButtons(messageBox.NoToAll | messageBox.No | messageBox.YesToAll | messageBox.Yes)
                    choice = messageBox.exec_()
                    if choice == messageBox.NoToAll:
                        break
                    if choice == messageBox.Yes:
                        self.logic.exportFieldAsCSV(filename, fieldName, shapeDict)
                    if choice == messageBox.YesToAll:
                        for fieldName, shapeDict in self.fieldDictionary.iteritems():
                            filename = directory + "/" + fieldName + ".csv"
                            self.logic.exportFieldAsCSV(filename, fieldName, shapeDict)
                        break
                else:
                    self.logic.exportFieldAsCSV(filename, fieldName, shapeDict)
        else:
            filename = directory + "/" + self.ROIComboBox.currentText + ".csv"
            self.logic.exportAllAsCSV(filename, self.fieldDictionary)

    def displayStatisticsOnStatsTable(self):
        # ---------------------------- Statistics Table ----------------------------
        for keyField, valueField in self.fieldDictionary.iteritems():
            statTable = qt.QTableWidget()
            statTable.setMinimumHeight(200)
            statTable.setColumnCount(9)
            statTable.setHorizontalHeaderLabels(['Shape', 'Min', 'Max', 'Average', 'STD', 'PER15', 'PER50', 'PER75', 'PER95'])
            self.tab.addTab(statTable, keyField)
            # Add Values:
            numberOfRows = valueField.__len__()
            statTable.setRowCount(numberOfRows)
            i = numberOfRows -1
            for key, value in valueField.iteritems():
                statTable.setCellWidget(i, 0, qt.QLabel(key))
                statTable.setCellWidget(i, 1, qt.QLabel(value.min))
                statTable.setCellWidget(i, 2, qt.QLabel(value.max))
                statTable.setCellWidget(i, 3, qt.QLabel(value.mean))
                statTable.setCellWidget(i, 4, qt.QLabel(value.std))
                statTable.setCellWidget(i, 5, qt.QLabel(value.percentile15))
                statTable.setCellWidget(i, 6, qt.QLabel(value.percentile50))
                statTable.setCellWidget(i, 7, qt.QLabel(value.percentile75))
                statTable.setCellWidget(i, 8, qt.QLabel(value.percentile95))
                i -= 1
        self.layout.addWidget(self.tab)
        self.layout.addLayout(self.exportLayout)
        self.exportButton.connect('clicked()', self.onExportButton)

    def compareArray(self, shapeList, arrayName):
        listBool = list()
        for shape in shapeList:
            pointData = shape.GetModelDisplayNode().GetInputPolyData().GetPointData()
            listBool.append(pointData.HasArray(arrayName))
        for bool in listBool:
            if bool == 0:
                return False
        return True

    def onRunButton(self):
        print " TEST"
        ROIToCompute = self.ROIComboBox.currentText
        if ROIToCompute and self.shapeList:
            self.fieldDictionary.clear()
            numberOfRowField = self.tableField.rowCount
            for i in range(0, numberOfRowField):
                widget = self.tableField.cellWidget(i, 0)
                if widget.isChecked():
                    self.fieldDictionary[self.tableField.cellWidget(i, 1).text] = dict()

            if self.fieldDictionary.__len__() > 0:
                for key, value in self.fieldDictionary.iteritems():
                    for shape in self.shapeList:
                        activePointData =shape.GetModelDisplayNode().GetInputPolyData().GetPointData()
                        fieldArray = activePointData.GetArray(key)

                        value[shape.GetName()] = self.StatisticStore()
                        if ROIToCompute == 'Entire Shape':
                            self.logic.computeAll(fieldArray, value[shape.GetName()], 'None')
                        else:
                            ROIArray = activePointData.GetArray(ROIToCompute)
                            self.logic.computeAll(fieldArray, value[shape.GetName()], ROIArray)
                indexWidgetTab = self.layout.indexOf(self.tab)
                if indexWidgetTab != -1:
                    for i in range(0, self.tab.count):
                        widget = self.tab.widget(i)
                        widget.clearContents()
                        widget.setRowCount(0)
                    self.tab.clear()
                    self.exportButton.disconnect('clicked()', self.onExportButton)
                    self.layout.removeWidget(self.exportButton)
                    self.layout.removeItem(self.exportLayout)

                self.displayStatisticsOnStatsTable()

    def onReload(self, moduleName="MeshStats"):
        """Generic reload method for any scripted module.
            ModuleWizard will subsitute correct default moduleName.
            """
        print " --------------------- RELOAD ------------------------ \n"
        globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)
    
    def testFunctions(self):
        print " ----------------------- TEST ------------------------- "
        BOOL = self.logic.testMinMaxMeanFunctions()
        print BOOL
        self.logic.testPercentileFunction()


class MeshStatsLogic:
    def __init__(self):
        pass

    def findArray(self, arrayName, node):
        pointData = node.GetModelDisplayNode().GetInputPolyData().GetPointData()
        bool = False
        for i in range(0, pointData.GetNumberOfArrays()):
            if arrayName == pointData.GetArray(i):
                bool = True
        return bool

    def defineArray(self, fieldArray, ROIArray):
        valueList = list()
        if ROIArray == 'None':
            for i in range(0, fieldArray.GetNumberOfTuples()):
                valueList.append(fieldArray.GetValue(i))
            valueArray = numpy.array(valueList)
        else:
            if ROIArray.GetNumberOfTuples() != fieldArray.GetNumberOfTuples():
                print "Size are not good!!!"
                return None
            else:
                for i in range(0, fieldArray.GetNumberOfTuples()):
                    if ROIArray.GetValue(i) == 1.0:
                        valueList.append(fieldArray.GetValue(i))
                valueArray = numpy.array(valueList)
        return valueArray
    
    def computeMean(self, valueArray):
        return numpy.mean(valueArray)
    
    def computeMinMax(self, valueArray):
        return numpy.min(valueArray), numpy.max(valueArray)
    
    def computeStandartDeviation(self, valueArray):
        return numpy.std(valueArray)
    
    def computePercentile(self, valueArray, percent):
        valueArray = numpy.sort(valueArray)
        index = (valueArray.size * percent) - 1
        ceilIndex = math.ceil(index)
        return valueArray[ceilIndex]
    
    def computeAll(self, fieldArray, fieldState, ROIArray):
        array = self.defineArray(fieldArray, ROIArray)
        fieldState.min, fieldState.max = self.computeMinMax(array)
        fieldState.mean = self.computeMean(array)
        fieldState.std = self.computeStandartDeviation(array)
        fieldState.percentile15 = self.computePercentile(array, 0.15)
        fieldState.percentile50 = self.computePercentile(array, 0.50)
        fieldState.percentile75 = self.computePercentile(array, 0.75)
        fieldState.percentile95 = self.computePercentile(array, 0.95)
    
    def exportAllAsCSV(self, filename, fieldDictionary):
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        for fieldName, shapeDict in fieldDictionary.iteritems():
            cw.writerow([fieldName])
            cw.writerow(['Shape', 'Min', 'Max', 'Average', 'STD', 'PER15', 'PER50', 'PER75', 'PER95'])
            for shapeName, shapeStats in shapeDict.iteritems():
                cw.writerow([shapeName,
                             shapeStats.min,
                             shapeStats.max,
                             shapeStats.mean,
                             shapeStats.std,
                             shapeStats.percentile15,
                             shapeStats.percentile50,
                             shapeStats.percentile75,
                             shapeStats.percentile95])
            cw.writerow([' '])
        file.close()

    def exportFieldAsCSV(self, filename, fieldName, shapeDict):
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        cw.writerow([fieldName])
        cw.writerow(['Shape', 'Min', 'Max', 'Average', 'STD', 'PER15', 'PER50', 'PER75', 'PER95'])
        for shapeName, shapeStats in shapeDict.iteritems():
            cw.writerow([shapeName,
                         shapeStats.min,
                         shapeStats.max,
                         shapeStats.mean,
                         shapeStats.std,
                         shapeStats.percentile15,
                         shapeStats.percentile50,
                         shapeStats.percentile75,
                         shapeStats.percentile95])
        file.close()
    
    def testMinMaxMeanFunctions(self):
        arrayValue = vtk.vtkDoubleArray()
        ROIArray = vtk.vtkDoubleArray()
        for i in range(1, 101):
            arrayValue.InsertNextValue(i)
            ROIArray.InsertNextValue(1.0)
        array = self.defineArray(arrayValue, ROIArray)
        print array
        min, max = self.computeMinMax(array)
        mean = self.computeMean(array)
        std = self.computeStandartDeviation(array)
        
        print min, max, mean, std
    
    def testPercentileFunction(self):
        # pair number of value:
        arrayValue = vtk.vtkDoubleArray()
        ROIArray = vtk.vtkDoubleArray()
        for i in range(1, 101):
            arrayValue.InsertNextValue(i)
            ROIArray.InsertNextValue(1.0)
        array = self.defineArray(arrayValue, ROIArray)
        print array
        
        percentile15 = self.computePercentile(array, 0.15)
        percentile50 = self.computePercentile(array, 0.50)
        percentile75 = self.computePercentile(array, 0.75)
        percentile95 = self.computePercentile(array, 0.95)
        print percentile15, percentile50, percentile75, percentile95
        # odd number of value:
        
        arrayValue = vtk.vtkDoubleArray()
        ROIArray = vtk.vtkDoubleArray()
        for i in range(1, 100):
            arrayValue.InsertNextValue(i)
            ROIArray.InsertNextValue(1.0)
        array = self.defineArray(arrayValue, ROIArray)
        print array
        
        percentile15 = self.computePercentile(array, 0.15)
        percentile50 = self.computePercentile(array, 0.50)
        percentile75 = self.computePercentile(array, 0.75)
        percentile95 = self.computePercentile(array, 0.95)
        print percentile15, percentile50, percentile75, percentile95