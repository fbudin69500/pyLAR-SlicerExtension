import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import SimpleITK as sitk
import pyLAR.alm.ialm as ialm

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
    # input volume selector
    #
    self.inputSelector = slicer.qMRMLNodeComboBox()
    self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector.selectNodeUponCreation = True
    self.inputSelector.addEnabled = False
    self.inputSelector.removeEnabled = False
    self.inputSelector.noneEnabled = False
    self.inputSelector.showHidden = False
    self.inputSelector.showChildNodeTypes = False
    self.inputSelector.setMRMLScene( slicer.mrmlScene )
    self.inputSelector.setToolTip( "Pick the input to the algorithm." )
    parametersFormLayout.addRow("Input Volume: ", self.inputSelector)

    #
    # output volume selector
    #
    self.outputLowRankSelector = slicer.qMRMLNodeComboBox()
    self.outputLowRankSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputLowRankSelector.selectNodeUponCreation = True
    self.outputLowRankSelector.addEnabled = True
    self.outputLowRankSelector.removeEnabled = True
    self.outputLowRankSelector.noneEnabled = True
    self.outputLowRankSelector.showHidden = False
    self.outputLowRankSelector.showChildNodeTypes = False
    self.outputLowRankSelector.setMRMLScene( slicer.mrmlScene )
    self.outputLowRankSelector.setToolTip( "Pick the output to the algorithm (low-rank)." )
    parametersFormLayout.addRow("Output Low-Rank Volume: ", self.outputLowRankSelector)

    self.outputSparseSelector = slicer.qMRMLNodeComboBox()
    self.outputSparseSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputSparseSelector.selectNodeUponCreation = True
    self.outputSparseSelector.addEnabled = True
    self.outputSparseSelector.removeEnabled = True
    self.outputSparseSelector.noneEnabled = True
    self.outputSparseSelector.showHidden = False
    self.outputSparseSelector.showChildNodeTypes = False
    self.outputSparseSelector.setMRMLScene( slicer.mrmlScene )
    self.outputSparseSelector.setToolTip( "Pick the output to the algorithm (sparse)." )
    parametersFormLayout.addRow("Output Sparse Volume: ", self.outputSparseSelector)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputLowRankSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputSparseSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.inputSelector.currentNode()\
                               and self.outputLowRankSelector.currentNode()\
                               and self.outputSparseSelector.currentNode()

  def onApplyButton(self):
    logic = LowRankImageDecompositionLogic()
    logic.run(self.inputSelector.currentNode(),
              self.outputLowRankSelector.currentNode(),
              self.outputSparseSelector.currentNode())

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

  def hasImageData(self,volumeNode):
    """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      logging.debug('hasImageData failed: no volume node')
      return False
    if volumeNode.GetImageData() == None:
      logging.debug('hasImageData failed: no image data in volume node')
      return False
    return True

  def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
    """Validates if the output is not the same as input
    """
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False
    if not outputVolumeNode:
      logging.debug('isValidInputOutputData failed: no output volume node defined')
      return False
    if inputVolumeNode.GetID()==outputVolumeNode.GetID():
      logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
      return False
    return True

  def run(self, inputVolume, outputLowRankVolume, outputSparseVolume ):
    """
    Run the actual algorithm
    """

    if not self.isValidInputOutputData(inputVolume, outputLowRankVolume):
      slicer.util.errorDisplay('Input volume is the same as the output low-rank volume.\
       Choose a different output low-rank volume.')
      return False
    if not self.isValidInputOutputData(inputVolume, outputSparseVolume):
      slicer.util.errorDisplay('Input volume is the same as the output sparse volume.\
       Choose a different output sparse volume.')
      return False
    if not self.isValidInputOutputData(outputLowRankVolume, outputSparseVolume):
      slicer.util.errorDisplay('Output low-rank volume is the same as the output sparse volume.\
       Choose a different output volume.')
      return False

    logging.info('Processing started')

    # Compute the low-rank and sparse volumes using pyLAR
    # decompose X into L+S
    # data for processing
    X = slicer.util.array(inputVolume.GetName())
    L, S, _, _, _, _ = ialm.recover(X)

    L_image = sitk.GetImageFromArray(np.asarray(L, dtype=np.uint8))
    S_image = sitk.GetImageFromArray(np.asarray(S, dtype=np.uint8))
    sitkUtils.PushToSlicer(L_image, outputLowRankVolume.GetName())
    sitkUtils.PushToSlicer(S_image, outputSparseVolume.GetName())
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
