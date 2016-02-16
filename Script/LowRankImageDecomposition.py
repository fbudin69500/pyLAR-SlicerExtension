import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import SimpleITK as sitk
import pyLAR
from distutils.spawn import find_executable

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
    # parameter file selector
    #
    self.selectConfigFileButton = qt.QPushButton("Select Configuration File")
    self.selectConfigFileButton.toolTip = "Select configuration file."
    parametersFormLayout.addRow(self.selectConfigFileButton)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

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


    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.selectConfigFileButton.connect('clicked(bool)', self.onSelectFile)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def onSelectFile(self):
      self.configFile = qt.QFileDialog.getOpenFileName(parent=self,caption='Select file')

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.configFile and self.selectAgolrithm.checkedButton()

  def onApplyButton(self):
    logic = LowRankImageDecompositionLogic()
    logic.run(self.configFile, self.selectAlgorithm.checkedButton().text)

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
    currentFilePath = os.path.realpath(__file__)
    upDirectory = os.path.join(currentFilePath, '..')
    # Prepend PATH with path of executables packaged with extension
    os.environ["PATH"] = os.path.join(upDirectory, 'ExternalBin') + os.pathsep + os.environ["PATH"]
    # Creates software configuration file
    software = type('obj', (object,), {})
    slicerSoftware = ['BRAINSFit', 'BRAINSDemonWarp', 'BSplineDeformableRegistration', 'BRAINSResample'
                      'ANTS', 'AverageImages', 'ComposeMultiTransform', 'WarpImageMultiTransform',
                      'CreateJacobianDeterminantImage', 'InvertDeformationField']
    for i in slicerSoftware:
      setattr(software, 'EXE'+str(i), find_executable(i))
    return software

  def run(self, configFile, algo ):
    """
    Run the actual algorithm
    """
    # Loads configuration file
    config = pyLAR.loadConfiguration(configFile, 'config')
    software = self.softwarePaths()

    result_dir = config.result_dir
    # For reproducibility: save all parameters into the result dir
    savedFileName = lambda name, default: os.path.basename(name) if name else default
    pyLAR.saveConfiguration(os.path.join(result_dir, savedFileName(configFN, 'Config.txt')), config)
    pyLAR.saveConfiguration(os.path.join(result_dir, savedFileName(configSoftware, 'Software.txt')),
                            software)
    fileListFN = config.fileListFN
    pyLAR.writeTxtIntoList(os.path.join(result_dir, savedFileName(fileListFN, 'listFiles.txt')), im_fns)
    currentPyFile = os.path.realpath(__file__)
    shutil.copy(currentPyFile, result_dir)
    sys.stdout = open(os.path.join(result_dir, 'RUN.log'), "w")
    logging.info('Processing started')
    if algo == "Unbias Atlas Creation":
      dsfsdf
    elif algo == "Low Rank/Sparse Decomposition":
      dsfsdf
    elif algo == "Low Rank Atlas Creation":
      esdf
    else:
      print "Error while selecting algorithm"
      return False
    logging.info('Processing completed')
    return True


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
