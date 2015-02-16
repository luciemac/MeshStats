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

        def printElement(self):
            print "min, max: ", self.min, self.max
            print "mean :", self.mean
            print "std", self.std

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

        self.modelList = list()
        self.fieldList = list()

        self.ROIList = list()

        self.ROIDict = dict() # Key = Name of ROI
                              # Value = Dictionary of Fields (key = Name of Field
                              #                               Value = dictionary of shapes
                              #                                             key = name of shapes
                              #                                             value = Statistics store()
        
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
        self.ROIComboBox.adjustSize()
        self.ROICheckBox = qt.QCheckBox('All')

        ROILayout = qt.QHBoxLayout()
        ROILayout_0 = qt.QFormLayout()
        ROILayout_0.addRow(" Region considered: ", self.ROIComboBox)

        ROILayout.addLayout(ROILayout_0)
        ROILayout.addWidget(self.ROICheckBox)

        self.layout.addLayout(ROILayout)
        self.ROICheckBox.connect('stateChanged(int)', self.onROICheckBoxStateChanged)
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
        self.tabROI = qt.QTabWidget()
        self.tabROI.setTabPosition(2)
        self.tabROI.adjustSize()
        # ---------------------------- Directory - Export Button -----------------------------
        self.directoryExport = ctk.ctkDirectoryButton()

        self.exportCheckBox = qt.QCheckBox("Separate Files")
        self.exportCheckBox.setChecked(True)

        self.exportDotButton = qt.QPushButton("Export as 0.000 ")
        self.exportDotButton.enabled = True
        self.exportComaButton = qt.QPushButton("Export as 0,000")
        self.exportComaButton.enabled = True


        self.exportLayout = qt.QVBoxLayout()

        self.directAndCheckLayout = qt.QHBoxLayout()
        self.directAndCheckLayout.addWidget(self.directoryExport)
        self.directAndCheckLayout.addWidget(self.exportCheckBox)

        self.exportButtonsLayout = qt.QHBoxLayout()
        self.exportButtonsLayout.addWidget(self.exportDotButton)
        self.exportButtonsLayout.addWidget(self.exportComaButton)


        self.exportLayout.addLayout(self.directAndCheckLayout)
        self.exportLayout.addLayout(self.exportButtonsLayout)
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
        del self.fieldList[:]

        self.ROIComboBox.clear()
        self.ROIComboBox.addItem('Entire Shape')

        del self.ROIList[:]
        self.ROIList.append('Entire Shape')

        tableFieldNumRows = 0
        expression = r"ROI$"
        if self.modelList:
            pointData = self.modelList[0].GetModelDisplayNode().GetInputPolyData().GetPointData()
            numOfArray = pointData.GetNumberOfArrays()
            for i in range(0, numOfArray):
                self.fieldList.append(pointData.GetArray(i).GetName())
            print self.fieldList
            for arrayName in self.fieldList:
                bool = self.compareArray(self.modelList, arrayName)
                print bool
                if bool:
                    if pointData.GetArray(arrayName).GetNumberOfComponents() == 1:
                        if not re.search(expression, arrayName):
                            tableFieldNumRows += 1
                            self.tableField.setRowCount(tableFieldNumRows)
                            self.tableField.setCellWidget(tableFieldNumRows - 1, 0, qt.QCheckBox())
                            self.tableField.setCellWidget(tableFieldNumRows - 1, 1, qt.QLabel(arrayName))
                        else:
                            self.ROIComboBox.addItem(arrayName)
                            self.ROIList.append(arrayName)
        self.layout.addStretch(1)

    def onInputComboBoxCheckedNodesChanged(self):
        self.modelList = self.inputComboBox.checkedNodes()
        print self.modelList
        self.updateInterface()

    def defineStatisticsTable(self, fieldDictionaryValue):
        # ---------------------------- Statistics Table ----------------------------
        statTable = qt.QTableWidget()
        statTable.setMinimumHeight(200)
        statTable.setColumnCount(9)
        statTable.setHorizontalHeaderLabels(['Shape', 'Min', 'Max', 'Average', 'STD', 'PER15', 'PER50', 'PER75', 'PER95'])
        # Add Values:
        numberOfRows = fieldDictionaryValue.__len__()
        statTable.setRowCount(numberOfRows)
        i = numberOfRows -1
        for key, value in fieldDictionaryValue.iteritems():
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
        statTable.resizeColumnToContents(0)
        return statTable

    def compareArray(self, modelList, arrayName):
        listBool = list()
        for model in modelList:
            pointData = model.GetModelDisplayNode().GetInputPolyData().GetPointData()
            listBool.append(pointData.HasArray(arrayName))
        for bool in listBool:
            if bool == 0:
                return False
        return True

    def onROICheckBoxStateChanged(self, intCheckState):
        # intCheckState == 2 when checked
        # intCheckState == 0 when unchecked
        print " ===== TEST =====", intCheckState
        if intCheckState == 2:
            self.ROIComboBox.setEnabled(False)
        else:
            if intCheckState == 0:
                self.ROIComboBox.setEnabled(True)

    def onRunButton(self):
        self.ROIDict.clear()
        print "____________ On run ____________"
        if self.modelList:
            #REMOVE PREVIOUS TABLE IF IT EXISTS:
            indexWidgetTabROI = self.layout.indexOf(self.tabROI)
            if indexWidgetTabROI != -1:
                for i in range(0, self.tabROI.count):
                    tabWidget = self.tabROI.widget(i)
                    for i in range(0, tabWidget.count):
                        tableWidget = tabWidget.widget(i)
                        tableWidget.clearContents()
                        tableWidget.setRowCount(0)
                    tabWidget.clear()
                self.tabROI.clear()

                self.exportDotButton.disconnect('clicked()', self.onExportDotButton)
                self.layout.removeWidget(self.exportDotButton)
                self.exportComaButton.disconnect('clicked()', self.onExportComaButton)
                self.layout.removeWidget(self.exportComaButton)
                self.layout.removeItem(self.exportLayout)

            # DEFINE NEW TABLE
            if self.ROICheckBox.isChecked():
                print "PLOP"
                for ROIName in self.ROIList:
                    if not self.ROIDict.has_key(ROIName):
                        self.ROIDict[ROIName] = dict()

            else:
                ROIToCompute = self.ROIComboBox.currentText
                if not self.ROIDict.has_key(ROIToCompute):
                    self.ROIDict[ROIToCompute] = dict()

            numberOfRowField = self.tableField.rowCount
            for ROIName, ROIFieldDict in self.ROIDict.iteritems():
                for i in range(0, numberOfRowField):
                    widget = self.tableField.cellWidget(i, 0)
                    if widget.isChecked():
                        ROIFieldDict[self.tableField.cellWidget(i, 1).text] = dict()
                for fieldName, fieldValue in ROIFieldDict.iteritems():
                    print "Field Name: ", fieldName
                    for shape in self.modelList:
                        print "Shape: ", shape.GetName()
                        activePointData = shape.GetModelDisplayNode().GetInputPolyData().GetPointData()
                        fieldArray = activePointData.GetArray(fieldName)
                        fieldValue[shape.GetName()] = self.StatisticStore()

                        if ROIName == 'Entire Shape':
                            print "Entire Shape"
                            self.logic.computeAll(fieldArray, fieldValue[shape.GetName()], 'None')
                        else:
                            print "Autre"
                            ROIArray = activePointData.GetArray(ROIName)
                            self.logic.computeAll(fieldArray, fieldValue[shape.GetName()], ROIArray)

        self.updateTable()

    def updateTable(self):
        print "===== UPDATE TABLE ====="
        # ROIToCompute = self.ROIComboBox.currentText

        for ROIName, FieldDict in self.ROIDict.iteritems():
            print "ROIName", ROIName
            tab = qt.QTabWidget()
            tab.adjustSize()
            tab.setTabPosition(0)
            for fieldName, fieldDictValue in FieldDict.iteritems():
                statisticsTable = self.defineStatisticsTable(fieldDictValue)
                tab.addTab(statisticsTable, fieldName)
            self.tabROI.addTab(tab, ROIName)
            print "DONE"

        self.layout.addWidget(self.tabROI)
        self.layout.addLayout(self.exportLayout)
        self.exportDotButton.connect('clicked()', self.onExportDotButton)
        self.exportComaButton.connect('clicked()', self.onExportComaButton)

    def exportationFunction(self, BoolComa):
        #  BoolComa is a boolean to know what kind of exportation is wanted
        #  BoolComa = True for COMA Exportation And False for DOT's one

        print self.exportCheckBox.isChecked()
        directory = self.directoryExport.directory
        messageBox = ctk.ctkMessageBox()
        messageBox.setWindowTitle(" /!\ WARNING /!\ ")
        messageBox.setIcon(messageBox.Warning)

        if self.exportCheckBox.isChecked():  # if exportation in different files
            for ROIName, ROIDictValue in sorted(self.ROIDict.iteritems()):
                directoryFolder = directory + '/' + ROIName
                if not os.path.exists(directoryFolder):
                    os.mkdir(directoryFolder)
                for fieldName, modelDict in sorted(ROIDictValue.iteritems()):
                    filename = directoryFolder + "/" + fieldName + ".csv"
                    if os.path.exists(filename):
                        messageBox.setText("On "+ ROIName + ", file " + fieldName + ".csv already exist in this folder.")
                        messageBox.setInformativeText("Do you want to replace it on " + ROIName + "?")
                        messageBox.setStandardButtons(messageBox.NoToAll | messageBox.No | messageBox.YesToAll | messageBox.Yes)
                        choice = messageBox.exec_()
                        if choice == messageBox.NoToAll:
                            print " No To All"
                            break
                        if choice == messageBox.Yes:
                            print " Yes "
                            self.logic.exportFieldAsCSV(filename, fieldName, modelDict)
                            if BoolComa:
                                self.logic.convertCSVWithComa(filename)
                        if choice == messageBox.YesToAll:
                            print " Yes To All"
                            for fieldName, shapeDict in sorted(ROIDictValue.iteritems()):
                                filename = directoryFolder + "/" + fieldName + ".csv"
                                self.logic.exportFieldAsCSV(filename, fieldName, shapeDict)
                                if BoolComa:
                                    self.logic.convertCSVWithComa(filename)
                            break
                    else:
                        self.logic.exportFieldAsCSV(filename, fieldName, modelDict)
                        if BoolComa:
                            self.logic.convertCSVWithComa(filename)
        else:
            for ROIName, ROIDictValue in sorted(self.ROIDict.iteritems()):
                filename = directory + "/" + ROIName + ".csv"
                if os.path.exists(filename):
                    messageBox.setText("File " + ROIName + ".csv already exist in this folder.")
                    messageBox.setInformativeText("Do you want to replace it? ")
                    messageBox.setStandardButtons(messageBox.NoToAll | messageBox.No | messageBox.YesToAll | messageBox.Yes)
                    choice = messageBox.exec_()
                    if choice == messageBox.NoToAll:
                        break
                    if choice == messageBox.Yes:
                        self.logic.exportAllAsCSV(filename, ROIName, ROIDictValue)
                        if BoolComa:
                            self.logic.convertCSVWithComa(filename)
                    if choice == messageBox.YesToAll:
                        for ROIName, ROIDictValue in sorted(self.ROIDict.iteritems()):
                            filename = directory + "/" + ROIName + ".csv"
                            self.logic.exportAllAsCSV(filename, ROIName, ROIDictValue)
                            if self.exportCheckBox.isChecked():
                                self.logic.convertCSVWithComa(filename)
                        break
                else:
                    self.logic.exportAllAsCSV(filename, ROIName, ROIDictValue)
                    if BoolComa:
                        self.logic.convertCSVWithComa(filename)

    def onExportDotButton(self):
        self.exportationFunction(False)

    def onExportComaButton(self):
        self.exportationFunction(True)

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
        self.numberOfDecimals = 3

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
        return round(numpy.mean(valueArray), self.numberOfDecimals)
    
    def computeMinMax(self, valueArray):
        return round(numpy.min(valueArray), self.numberOfDecimals), round(numpy.max(valueArray), self.numberOfDecimals)
    
    def computeStandartDeviation(self, valueArray):
        return round(numpy.std(valueArray), self.numberOfDecimals)
    
    def computePercentile(self, valueArray, percent):
        valueArray = numpy.sort(valueArray)
        index = (valueArray.size * percent) - 1
        ceilIndex = math.ceil(index)
        return round(valueArray[ceilIndex], self.numberOfDecimals)
    
    def computeAll(self, fieldArray, fieldState, ROIArray):
        array = self.defineArray(fieldArray, ROIArray)
        fieldState.min, fieldState.max = self.computeMinMax(array)
        fieldState.mean = self.computeMean(array)
        fieldState.std = self.computeStandartDeviation(array)
        fieldState.percentile15 = self.computePercentile(array, 0.15)
        fieldState.percentile50 = self.computePercentile(array, 0.50)
        fieldState.percentile75 = self.computePercentile(array, 0.75)
        fieldState.percentile95 = self.computePercentile(array, 0.95)

    def writeFieldFile(self, fileWriter, modelDict):
        for shapeName, shapeStats in modelDict.iteritems():
            fileWriter.writerow([shapeName,
                                 shapeStats.min,
                                 shapeStats.max,
                                 shapeStats.mean,
                                 shapeStats.std,
                                 shapeStats.percentile15,
                                 shapeStats.percentile50,
                                 shapeStats.percentile75,
                                 shapeStats.percentile95])

    def exportAllAsCSV(self, filename, ROIName, ROIDictValue):
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        cw.writerow([ROIName])
        print ROIDictValue
        for fieldName, shapeDict in sorted(ROIDictValue.iteritems()):
            print shapeDict
            cw.writerow([fieldName])
            cw.writerow(['Shape', 'Min', 'Max', 'Average', 'STD', 'PER15', 'PER50', 'PER75', 'PER95'])
            self.writeFieldFile(cw, shapeDict)
            cw.writerow([' '])
        file.close()

    def exportFieldAsCSV(self, filename, fieldName, shapeDict):
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        cw.writerow([fieldName])
        cw.writerow(['Shape', 'Min', 'Max', 'Average', 'STD', 'PER15', 'PER50', 'PER75', 'PER95'])
        self.writeFieldFile(cw, shapeDict)
        file.close()

    def replaceCarac(self, filename, oldCarac, newCarac):
        file = open(filename,'r')
        lines = file.readlines()
        with open (filename, 'r') as file:
            lines = [line.replace(oldCarac, newCarac) for line in file.readlines()]
        file.close()
        file = open(filename, 'w')
        file.writelines(lines)
        file.close()

    def convertCSVWithComa(self, filename):
        self.replaceCarac(filename, ',', ';')
        self.replaceCarac(filename, '.', ',')

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