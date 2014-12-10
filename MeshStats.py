import numpy, math, time, re, csv
import unittest
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
        
        class fieldState (object):
            def __init__(self):
                self.min = 0
                self.max = 0
                self.mean = 0
                self.std = 0
                self.percentile15 = 0
                self.percentile50 = 0
                self.percentile75 = 0
                self.percentile95 = 0
            def printElements(self):
                print" min:", self.min, " max:", self.max, " mean:", self.mean, " std:", self.std
                print "percentile15:", self.percentile15, " percentile50:", self.percentile50, " percentile75:", self.percentile75, " percentile95:", self.percentile95
        
        # -------------------------------------------------------------------------------------
        self.logic = MeshStatsLogic()
        # Dictionary Of field. Keys = Name of the field
        self.fieldDictionary = dict()
        self.ROIList = list()
        
        # ------------------------------------------------------------------------------------
        #                                    Shapes
        # ------------------------------------------------------------------------------------
        inputLabel = qt.QLabel("Shape: ")
        inputComboBox = slicer.qMRMLNodeComboBox()
        inputComboBox.nodeTypes = ['vtkMRMLModelNode']
        inputComboBox.selectNodeUponCreation = False
        inputComboBox.addEnabled = False
        inputComboBox.removeEnabled = False
        inputComboBox.noneEnabled = True
        inputComboBox.showHidden = False
        inputComboBox.showChildNodeTypes = False
        inputComboBox.setMRMLScene(slicer.mrmlScene)
        
        inputLayout = qt.QHBoxLayout()
        inputLayout.addWidget(inputLabel)
        inputLayout.addWidget(inputComboBox)
        
        self.layout.addLayout(inputLayout)
        
        fieldLabel = qt.QLabel("Field: ")
        ROILabel = qt.QLabel("ROI: ")
        
        labelLayout = qt.QHBoxLayout()
        labelLayout.addWidget(fieldLabel)
        labelLayout.addWidget(ROILabel)
        
        
        tableField = qt.QTableWidget()
        tableField.setColumnCount(2)
        tableField.setMaximumWidth(230)
        tableField.setHorizontalHeaderLabels([' ', 'Field Name'])
        tableField.setColumnWidth(0, 18)
        tableField.setColumnWidth(1, 180)
        
        ROITable = qt.QTableWidget()
        ROITable.setMaximumWidth(230)
        ROITable.setColumnCount(2)
        ROITable.setHorizontalHeaderLabels([' ', 'Region Considered'])
        ROITable.setColumnWidth(0, 18)
        ROITable.setColumnWidth(1, 180)
        
        tablesLayout = qt.QHBoxLayout()
        tablesLayout.addWidget(tableField)
        tablesLayout.addWidget(ROITable)
        
        labelTablesLayout = qt.QVBoxLayout()
        labelTablesLayout.addLayout(labelLayout)
        labelTablesLayout.addLayout(tablesLayout)
        self.layout.addLayout(labelTablesLayout)
        
        # ------------------------------------------------------------------------------------
        #                                    Apply
        # ------------------------------------------------------------------------------------
        applyButton = qt.QPushButton("Apply")
        applyButton.setMaximumWidth(100)
        applyButton.enabled = False
        applyLayout = qt.QHBoxLayout()
        applyLayout.setAlignment(2)
        applyLayout.addWidget(applyButton)
        self.layout.addLayout(applyLayout)
        
        # ------------------------------------------------------------------------------------
        #                          Statistics Table - Export
        # ------------------------------------------------------------------------------------
        tab = qt.QTabWidget()
        # ---------------------------- Directory - Export Button -----------------------------
        exportButton = qt.QPushButton("Export")
        exportButton.setMaximumWidth(100)
        exportButton.enabled = True
        
        exportLayout = qt.QHBoxLayout()
        exportLayout.setAlignment(2)
        exportLayout.addWidget(exportButton)
        
        # ------------------------------------------------------------------------------------
        
        def onCurrentNodeChanged():
            activeNode = inputComboBox.currentNode()
            tableField.clearContents()
            tableField.setRowCount(0)
            ROITable.clearContents()
            ROITable.setRowCount(0)
            
            if activeNode:
                pointData = activeNode.GetModelDisplayNode().GetInputPolyData().GetPointData()
                numOfField = pointData.GetNumberOfArrays()
                if numOfField > 0:
                    tableFieldNumRows = 0
                    tableROINumRows = 1
                    ROITable.setRowCount(tableROINumRows)
                    ROITable.setCellWidget(0, 0, qt.QCheckBox())
                    ROITable.setCellWidget(0, 1, qt.QLabel('Entire Shape'))
                    expression = r"ROI$"
                    
                    for i in range(0, numOfField):
                        fieldName = pointData.GetArray(i).GetName()
                        checkBox = qt.QCheckBox()
                        if not re.search(expression, pointData.GetArray(i).GetName()):
                            tableFieldNumRows += 1
                            tableField.setRowCount(tableFieldNumRows)
                            tableField.setCellWidget(tableFieldNumRows - 1, 0, checkBox)
                            tableField.setCellWidget(tableFieldNumRows - 1, 1, qt.QLabel(fieldName))
                        else:
                            tableROINumRows += 1
                            ROITable.setRowCount(tableROINumRows)
                            ROITable.setCellWidget(tableROINumRows - 1, 0, checkBox)
                            ROITable.setCellWidget(tableROINumRows -1, 1, qt.QLabel(fieldName))
            
            applyButton.enabled = activeNode != None
        
        
        def displayStatisticsOnStatsTable():
            # ---------------------------- Statistics Table ----------------------------
            for keyField, valueField in self.fieldDictionary.iteritems():
                statTable2 = qt.QTableWidget()
                statTable2.setColumnCount(9)
                statTable2.setHorizontalHeaderLabels(['ROI', 'Min', 'Max', 'Average', 'STD', 'PER15', 'PER50', 'PER75', 'PER95'])
                tab.addTab(statTable2, keyField)
                # Add Values:
                numberOfRows = valueField.__len__()
                statTable2.setRowCount(numberOfRows)
                i = numberOfRows -1
                for key, value in valueField.iteritems():
                    statTable2.setCellWidget(i, 0, qt.QLabel(key))
                    statTable2.setCellWidget(i, 1, qt.QLabel(value.min))
                    statTable2.setCellWidget(i, 2, qt.QLabel(value.max))
                    statTable2.setCellWidget(i, 3, qt.QLabel(value.mean))
                    statTable2.setCellWidget(i, 4, qt.QLabel(value.std))
                    statTable2.setCellWidget(i, 5, qt.QLabel(value.percentile15))
                    statTable2.setCellWidget(i, 6, qt.QLabel(value.percentile50))
                    statTable2.setCellWidget(i, 7, qt.QLabel(value.percentile75))
                    statTable2.setCellWidget(i, 8, qt.QLabel(value.percentile95))
                    i -= 1
            self.layout.addWidget(tab)
            self.layout.addLayout(exportLayout)
            exportButton.connect('clicked()', onExportButton)
        
        def onApplyButton():
            activeInput = inputComboBox.currentNode()
            if activeInput:
                activePointData = activeInput.GetModelDisplayNode().GetInputPolyData().GetPointData()
                numberOfRowField = tableField.rowCount
                numberOfRowROI = ROITable.rowCount
                self.fieldDictionary.clear()
                del self.ROIList[:]
                for i in range(0, numberOfRowField):
                    widget = tableField.cellWidget(i, 0)
                    if widget.isChecked():
                        self.fieldDictionary[activePointData.GetArray(i).GetName()] = dict()
                for i in range(0, numberOfRowROI):
                    widget = ROITable.cellWidget(i, 0)
                    label = ROITable.cellWidget(i, 1)
                    if widget.isChecked():
                        self.ROIList.append(label.text)
                print self.ROIList
                if self.ROIList and self.fieldDictionary.__len__() > 0:
                    for key, value in self.fieldDictionary.iteritems():
                        fieldArray = activePointData.GetArray(key)
                        for Region in self.ROIList:
                            value[Region] = fieldState()
                            if Region == 'Entire Shape':
                                self.logic.computeAll(fieldArray, value[Region], 'None')
                            else:
                                ROIArray = activePointData.GetArray(Region)
                                self.logic.computeAll(fieldArray, value[Region], ROIArray)
                
                indexWidgetTab = self.layout.indexOf(tab)
                if indexWidgetTab != -1:
                    for i in range(0, tab.count):
                        widget = tab.widget(i)
                        widget.clearContents()
                        widget.setRowCount(0)
                    tab.clear()
                    
                    exportButton.disconnect('clicked()', onExportButton)
                    self.layout.removeWidget(exportButton)
                    self.layout.removeItem(exportLayout)
                displayStatisticsOnStatsTable()
        
        
        def onExportButton():
            dialog = ctk.ctkFileDialog()
            dialog.selectNameFilter('.csv')
            filename = dialog.getSaveFileName(parent=self, caption='Save file')
            self.logic.exportAsCSV(filename, self.fieldDictionary)
        
        inputComboBox.connect('currentNodeChanged(vtkMRMLNode*)', onCurrentNodeChanged)
        applyButton.connect('clicked()', onApplyButton)
        
        self.layout.addStretch(1)
        
        def onCloseScene(obj, event):
            print " --- OnCloseScene ---"
            # initialize Parameters
            globals()["MeshStats"] = slicer.util.reloadScriptedModule("MeshStats")
        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, onCloseScene)
    
    
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
    
    def defineArray(self, fieldArray, ROIArray):
        valueList = list()
        if ROIArray == 'None':
            for i in range(0, fieldArray.GetNumberOfTuples()):
                valueList.append(fieldArray.GetValue(i))
            valueArray = numpy.array(valueList)
            return valueArray
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
    
    def exportAsCSV(self, filename, fieldDictionary):
        file = open(filename, 'w')
        cw = csv.writer(file, delimiter=',')
        for keyField, fieldValue in fieldDictionary.iteritems():
            cw.writerow([keyField])
            cw.writerow(['ROI', 'Min', 'Max', 'Average', 'STD', 'PER15', 'PER50', 'PER75', 'PER95'])
            for key, value in fieldValue.iteritems():
                cw.writerow([key,
                             value.min,
                             value.max,
                             value.mean,
                             value.std,
                             value.percentile15,
                             value.percentile50,
                             value.percentile75,
                             value.percentile95])
            cw.writerow([' '])
        
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