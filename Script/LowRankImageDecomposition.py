import os
import sys
import shutil
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import SimpleITK as sitk
import pyLAR
from distutils.spawn import find_executable
import threading
import json
#
# Low-rank Image Decomposition
#

class LowRankImageDecomposition(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Low-rank Image Decomposition"
    self.parent.categories = ["Filtering"]
    self.parent.dependencies = []
    self.parent.contributors = ["Francois Budin (Kitware Inc.)"]
    self.parent.helpText = """
    This script computes a low-rank decomposition of an input image. It returns both
     a low-rank image and a sparse image.
    """
    self.parent.acknowledgementText = """
    This work was supported, in-part, by the NIBIB
    (R41EB015775), the NINDS (R41NS081792) and the NSF (EECS-1148870)
""" # replace with organization, grant and thanks.

#
# LowRankImageDecompositionWidget
#

class LowRankImageDecompositionWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.logic = LowRankImageDecompositionLogic()
    # Initialize variables
    self.configFile = ""
    self.Algorithm = {"Unbiased Atlas Creation": "uab",
                      "Low Rank/Sparse Decomposition": "lr",
                      "Low Rank Atlas Creation": "nglra"}
    # Instantiate and connect widgets ...

    examplesCollapsibleButton = ctk.ctkCollapsibleButton()
    examplesCollapsibleButton.text = "Examples"
    examplesCollapsibleButton.collapsed = True
    self.layout.addWidget(examplesCollapsibleButton)

    # Layout within a collapsible button
    examplesFormLayout = qt.QFormLayout(examplesCollapsibleButton)

    #
    # Save example configuration file Buttons
    #
    configFilesCollapsibleButton = ctk.ctkCollapsibleButton()
    configFilesCollapsibleButton.text = "Configuration Files"
    configFilesCollapsibleButton.collapsed = False
    examplesFormLayout.addRow(configFilesCollapsibleButton)
    configFormLayout = qt.QFormLayout(configFilesCollapsibleButton)
    self.exampleUABButton = qt.QPushButton("Unbiased Atlas Creation")
    self.exampleUABButton.toolTip = "Save example configuration file to run Unbiased Atlas Creation."
    self.exampleUABButton.enabled = True
    configFormLayout.addRow(self.exampleUABButton)
    self.exampleLRButton = qt.QPushButton("Low Rank/Sparse Decomposition")
    self.exampleLRButton.toolTip = "Save example configuration file to run Low Rank/Sparse Decomposition."
    self.exampleLRButton.enabled = True
    configFormLayout.addRow(self.exampleLRButton)
    self.exampleNGLRAButton = qt.QPushButton("Low Rank Atlas Creation")
    self.exampleNGLRAButton.toolTip = "Save example configuration file to run Low Rank Atlas Creation."
    self.exampleNGLRAButton.enabled = True
    configFormLayout.addRow(self.exampleNGLRAButton)

    # Download data
    dataCollapsibleButton = ctk.ctkCollapsibleButton()
    dataCollapsibleButton.text = "Download data"
    dataCollapsibleButton.collapsed = False
    examplesFormLayout.addRow(dataCollapsibleButton)
    dataFormLayout = qt.QFormLayout(dataCollapsibleButton)
    self.bulleyeButton = qt.QPushButton("Download synthetic data (Bull's eye)")
    self.bulleyeButton.toolTip = "Download synthetic data from http://slicer.kitware.com/midas3"
    self.bulleyeButton.enabled = True
    dataFormLayout.addRow(self.bulleyeButton)
    self.t1flashButton = qt.QPushButton("Download Healthy Volunteer (T1-Flash)")
    self.t1flashButton.toolTip = "Download healthy volunteer data from http://insight-journal.org/midas/community/view/21"
    self.t1flashButton.enabled = True
    dataFormLayout.addRow(self.t1flashButton)
    self.t1mprageButton = qt.QPushButton("Download Healthy Volunteer (T1-MPRage)")
    self.t1mprageButton.toolTip = "Download healthy volunteer data from http://insight-journal.org/midas/community/view/21"
    self.t1mprageButton.enabled = True
    dataFormLayout.addRow(self.t1mprageButton)
    self.t2Button = qt.QPushButton("Download Healthy Volunteer (T2)")
    self.t2Button.toolTip = "Download healthy volunteer data from http://insight-journal.org/midas/community/view/21"
    self.t2Button.enabled = True
    dataFormLayout.addRow(self.t2Button)
    self.mraButton = qt.QPushButton("Download Healthy Volunteer (MRA)")
    self.mraButton.toolTip = "Download healthy volunteer data from http://insight-journal.org/midas/community/view/21"
    self.mraButton.enabled = True
    dataFormLayout.addRow(self.mraButton)
    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within a collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # parameter file selector
    #
    self.selectConfigFileButton = qt.QPushButton("Select Configuration File")
    self.selectConfigFileButton.toolTip = "Select configuration file."
    parametersFormLayout.addRow(self.selectConfigFileButton)


    self.label = qt.QLabel()
    parametersFormLayout.addRow(self.label)
    #
    # Select algorithm
    #
    self.selectAlgorithm = qt.QButtonGroup()
    self.selectUnbiasedAtlas = qt.QRadioButton("Unbiased Atlas Creation (UAB)")
    self.selectLowRankDecomposition = qt.QRadioButton("Low Rank/Sparse Decomposition (LR)")
    self.selectLowRankAtlasCreation = qt.QRadioButton("Low Rank Atlas Creation (nglra)")
    self.selectAlgorithm.addButton(self.selectUnbiasedAtlas)
    self.selectAlgorithm.addButton(self.selectLowRankDecomposition)
    self.selectAlgorithm.addButton(self.selectLowRankAtlasCreation)
    parametersFormLayout.addRow(self.selectUnbiasedAtlas)
    parametersFormLayout.addRow(self.selectLowRankDecomposition)
    parametersFormLayout.addRow(self.selectLowRankAtlasCreation)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    # show log
    self.log = qt.QTextEdit()
    self.log.readOnly = True

    parametersFormLayout.addRow(self.log)
    self.logMessage('<p>Status: <i>Idle</i>\n')

    # Add vertical spacer
    self.layout.addStretch(1)

    #Progress bar
    self.progress_bar = slicer.qSlicerCLIProgressBar()
    self.progress_bar.setProgressVisibility(False)
    self.progress_bar.setStatusVisibility(False)
    self.progress_bar.setNameVisibility(False)
    parametersFormLayout.addRow(self.progress_bar)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.selectConfigFileButton.connect('clicked(bool)', self.onSelectFile)
    self.selectUnbiasedAtlas.connect('clicked(bool)', self.onSelect)
    self.selectLowRankDecomposition.connect('clicked(bool)', self.onSelect)
    self.selectLowRankAtlasCreation.connect('clicked(bool)', self.onSelect)
    self.exampleNGLRAButton.connect('clicked(bool)', self.onSaveConfigFile)

    self.mapper = qt.QSignalMapper()
    self.mapper.connect('mapped(const QString&)', self.onDownloadData)
    self.mapper.setMapping(self.bulleyeButton,"Bullseye.json")
    self.mapper.setMapping(self.t1flashButton,"HealthyVolunteers-T1-Flash.json")
    self.mapper.setMapping(self.t1mprageButton,"HealthyVolunteers-T1-MPRage.json")
    self.mapper.setMapping(self.mraButton,"HealthyVolunteers-MRA.json")
    self.mapper.setMapping(self.t2Button,"HealthyVolunteers-T2.json")
    self.bulleyeButton.connect('clicked()', self.mapper, 'map()')
    self.t1flashButton.connect('clicked()', self.mapper, 'map()')
    self.t1mprageButton.connect('clicked()', self.mapper, 'map()')
    self.mraButton.connect('clicked()', self.mapper, 'map()')
    self.t2Button.connect('clicked()', self.mapper, 'map()')

    # Refresh Apply button state
    self.onSelect()

  def onDownloadData(self,name):
    result = qt.QMessageBox.question(slicer.util.mainWindow(),
                                     'Download', "Downloading data might take several minutes",
                                      qt.QMessageBox.Ok, qt.QMessageBox.Cancel)
    if result == qt.QMessageBox.Cancel:
      return

    errorLog = slicer.app.errorLogModel()
    errorLog.connect('entryAdded(ctkErrorLogLevel::LogLevel)', self.logEvent)
    clinode = self.logic.downloadData(name)
    self.startProgressBar(clinode)
    #errorLog.disconnect('entryAdded(ctkErrorLogLevel::LogLevel)', self.logEvent)

  def logEvent(self):
    errorLog = slicer.app.errorLogModel()
    self.label.text=str(errorLog.logEntryCount()) + " - " +errorLog.logEntryDescription(errorLog.logEntryCount() - 1)
    self.logMessage(errorLog.logEntryDescription(errorLog.logEntryCount() - 1))

  def logMessage(self, message):
    self.log.setText(message)
#    self.log.insertPlainText('\n')
    self.log.ensureCursorVisible()
    self.log.repaint()

  def onSelectFile(self):
    self.configFile = qt.QFileDialog.getOpenFileName(parent=self,caption='Select file')
    self.onSelect()

  def onSaveConfigFile(self):
    configFile = qt.QFileDialog.getOpenFileName(parent=self,caption='Select file')

  def cleanup(self):
    errorLog = slicer.app.errorLogModel()
    errorLog.disconnect('entryAdded(ctkErrorLogLevel::LogLevel)', self.logEvent)
    self.configFile = None
    self.logic = None

  def onSelect(self):
    self.applyButton.enabled = self.configFile and self.selectAlgorithm.checkedButton()

  def resetUI(self):
    self.applyButton.setText("Apply")
    self.applyButton.setEnabled(True)
    self.applyButton.repaint()

  def startProgressBar(self,clinode):
    clinode.AddObserver('ModifiedEvent', self.isFinished)
    self.progress_bar.setCommandLineModuleNode(clinode)

  def onApplyButton(self):
    self.applyButton.setText("Computing...")
    self.applyButton.enabled = False
    self.applyButton.repaint()
    errorLog = slicer.app.errorLogModel()
    errorLog.connect('entryAdded(ctkErrorLogLevel::LogLevel)', self.logEvent)
    clinode = self.logic.run(self.configFile, self.Algorithm[self.selectAlgorithm.checkedButton().text])
    self.startProgressBar(clinode)

  def isFinished(caller, event):
    print("Got a %s from a %s" % (event, caller.GetClassName()))
    if caller.IsA('vtkMRMLCommandLineModuleNode'):
      if caller.GetStatusString() == 'Completed':
        print("Status is %s" % caller.GetStatusString())
        self.resetUI()
        errorLog = slicer.app.errorLogModel()
        errorLog.disconnect('entryAdded(ctkErrorLogLevel::LogLevel)', self.logEvent)
#
# LowRankImageDecompositionLogic
#

class LowRankImageDecompositionLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def softwarePaths(self):
    savedPATH = os.environ["PATH"]
    currentFilePath = os.path.dirname(os.path.realpath(__file__))
    upDirectory = os.path.realpath(os.path.join(currentFilePath, '..'))
    # Prepend PATH with path of executables packaged with extension
    os.environ["PATH"] = os.path.join(upDirectory, 'ExternalBin') + os.pathsep + savedPATH
    # Creates software configuration file
    software = type('obj', (object,), {})
    slicerSoftware = ['BRAINSFit', 'BRAINSDemonWarp', 'BSplineDeformableRegistration', 'BRAINSResample',
                      'ANTS', 'AverageImages', 'ComposeMultiTransform', 'WarpImageMultiTransform',
                      'CreateJacobianDeterminantImage', 'InvertDeformationField']
    for i in slicerSoftware:
      setattr(software, 'EXE_'+str(i), find_executable(i))
    os.environ["PATH"] = savedPATH
    return software

  def run(self, configFile, algo):
    """
    Run the actual algorithm
    """
    # Check that pyLAR is not already running:
    try:
      if self.thread.is_alive():
        logging.warning("Processing is already running")
        return
    except:
      pass
    # Create software configuration object
    config = pyLAR.loadConfiguration(configFile, 'config')
    software = self.softwarePaths()
    pyLAR.containsRequirements(config, ['data_dir', 'file_list_file_name', 'result_dir'], configFile)
    result_dir = config.result_dir
    data_dir = config.data_dir
    file_list_file_name = config.file_list_file_name
    im_fns = pyLAR.readTxtIntoList(os.path.join(data_dir, file_list_file_name))
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    pyLAR.configure_logger(logger, config, configFile)
    clinode = slicer.cli.createNode(slicer.modules.brainsfit)
    self.thread = threading.Thread(target=self.RunThread,
                                   args=(algo, config, software, im_fns, result_dir, clinode),
                                   kwargs={'configFile':configFile, 'file_list_file_name':file_list_file_name})
    self.thread.start()
    clinode.SetStatus(2)  # 2: 'Running'
    return clinode

  def RunThread(self, algo, config, software, im_fns, result_dir, clinode,
                configFile, file_list_file_name):
    pyLAR.run(algo, config, software, im_fns, result_dir,
              configFN=configFile, file_list_file_name=file_list_file_name)
    clinode.SetStatus(32)  # 32: 'Completed'

  def loadDataFile(self, filename):
    """
    Returns
    -------
    downloads: List of the names of the bull's eye images available on http://slicer.kitware.com/midas3
    with their corresponding item number.
    """
    file_path = os.path.realpath(__file__)
    dir_path = os.path.dirname(file_path)
    dir_path = os.path.join(dir_path, 'Data')
    data = open(os.path.join(dir_path,filename),'r').read()
    return json.loads(data)

  def downloadDataThread(self,downloads,clinode):
    import urllib
    loader = slicer.util.loadVolume
    if 'url' not in downloads.keys():
      raise Exception("Key 'url' is missing in dictionary")
    url = downloads['url']
    if 'files' not in downloads.keys():
      raise Exception("Key 'files' is missing in dictionary")
    for name, value in downloads['files'].items():
      item_url = url + value
      filePath = os.path.join(slicer.app.temporaryPath, name)
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s\nfrom %s...\n' %(name, item_url))
        urllib.urlretrieve(item_url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    logging.info('Finished with download and loading')
    clinode.SetStatus(32)  # 32: 'Completed'


  def downloadData(self, filename):
    """
    Downloads bull's eye example data from http://slicer.kitware.com/midas3
    The dataset contains 8 healthy synthetic images, and 8 subjects with anomalies,
    as well as an average image.
    """
    downloads = self.loadDataFile(filename)
    logging.info('Starting to download')
    clinode = slicer.cli.createNode(slicer.modules.brainsfit)
    self.thread = threading.Thread(target=self.downloadDataThread,
                                   args=(downloads, clinode))
    self.thread.start()
    clinode.SetStatus(2)  # 2: 'Running'
    return clinode

  def CreateExampleConfigurationFile(self):
    data_dir = slicer.app.temporaryPath
    reference_im_fn = bulleyeData()[0][1]
    fileListFN = os.path.join(slicer.app.temporaryPath,"fileList.txt")
    modality = 'Simu'
    lamda = 2.0
    result_dir = os.path.join(data_dir,'output')
    os.makedirs(result_dir)


class LowRankImageDecompositionTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_LowRankImageDecomposition1()

  def test_LowRankImageDecomposition1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=231227', 'fMeanSimu.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = LowRankImageDecompositionLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
