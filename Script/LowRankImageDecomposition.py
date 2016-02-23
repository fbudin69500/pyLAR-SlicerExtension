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
    self.Algorithm = {"Unbias Atlas Creation": "uab",
                      "Low Rank/Sparse Decomposition": "lr",
                      "Low Rank Atlas Creation": "nglra"}
    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # Apply Button
    #
    self.exampleButton = qt.QPushButton("Example Configuration File")
    self.exampleButton.toolTip = "Save example configuration file."
    self.exampleButton.enabled = True
    parametersFormLayout.addRow(self.exampleButton)

    #
    # parameter file selector
    #
    self.selectConfigFileButton = qt.QPushButton("Select Configuration File")
    self.selectConfigFileButton.toolTip = "Select configuration file."
    parametersFormLayout.addRow(self.selectConfigFileButton)

    #
    # Select algorithm
    #
    self.selectAlgorithm = qt.QButtonGroup()
    self.selectUnbiasAtlas = qt.QRadioButton("Unbias Atlas Creation")
    self.selectLowRankDecomposition = qt.QRadioButton("Low Rank/Sparse Decomposition")
    self.selectLowRankAtlasCreation = qt.QRadioButton("Low Rank Atlas Creation")
    self.selectAlgorithm.addButton(self.selectUnbiasAtlas)
    self.selectAlgorithm.addButton(self.selectLowRankDecomposition)
    self.selectAlgorithm.addButton(self.selectLowRankAtlasCreation)
    parametersFormLayout.addRow(self.selectUnbiasAtlas)
    parametersFormLayout.addRow(self.selectLowRankDecomposition)
    parametersFormLayout.addRow(self.selectLowRankAtlasCreation)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)


    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.selectConfigFileButton.connect('clicked(bool)', self.onSelectFile)
    self.selectUnbiasAtlas.connect('clicked(bool)', self.onSelect)
    self.selectLowRankDecomposition.connect('clicked(bool)', self.onSelect)
    self.selectLowRankAtlasCreation.connect('clicked(bool)', self.onSelect)
    self.exampleButton.connect('clicked(bool)', self.onSaveConfigFile)
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

    # Refresh Apply button state
    self.onSelect()

  def logEvent(self):
    errorLog = slicer.app.errorLogModel()
    self.logMessage(errorLog.logEntryDescription(errorLog.logEntryCount() - 1))

  def logMessage(self, message):
    self.log.append(message)
    self.log.insertPlainText('\n')
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

  def onApplyButton(self):
    self.applyButton.setText("Computing...")
    self.applyButton.enabled = False
    self.applyButton.repaint()
    errorLog = slicer.app.errorLogModel()
    errorLog.connect('entryAdded(ctkErrorLogLevel::LogLevel)', self.logEvent)
    clinode = self.logic.run(self.configFile, self.Algorithm[self.selectAlgorithm.checkedButton().text])
    clinode.AddObserver('ModifiedEvent', self.isFinished)
    self.progress_bar.setCommandLineModuleNode(clinode)

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
                                   args=(algo, config, software, im_fns, result_dir),
                                   kwargs={'configFile':configFile, 'file_list_file_name':file_list_file_name})
    self.thread.start()
    clinode.SetStatus(2)  # 2: 'Running'
    return clinode

  def RunThread(self, algo, config, software, im_fns, result_dir,
                configFile, file_list_file_name):
    pyLAR.run(algo, config, software, im_fns, result_dir,
              configFN=configFile, file_list_file_name=file_list_file_name)
    clinode.SetStatus(32)  # 32: 'Completed'


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
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
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
