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
import json
import threading
import Queue
from time import sleep
import errno

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
"""  # replace with organization, grant and thanks.


#
# LowRankImageDecompositionWidget
#

class LowRankImageDecompositionWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    class QMovingProgressBar(qt.QProgressBar):
        def __init__(self, size=15, interval=100):
            qt.QProgressBar.__init__(self)
            self.setRange(0, size)
            self.timer = qt.QTimer()
            self.timer.setInterval(interval)
            self.timer.connect('timeout()', self._move)
            self.setTextVisible(False)

        def start(self):
            self.setValue(0)
            self.show()
            self.timer.start()

        def _move(self):
            self.value += 1
            if self.value == self.maximum:
                self.value = 0

        def stop(self):
            self.timer.stop()
            self.value = self.maximum

        def clear(self):
            self.timer.stop()
            self.hide()
            self.value = 0

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = LowRankImageDecompositionLogic()
        # Initialize variables
        self.configFile = ""
        self.Algorithm = {"Unbiased Atlas Creation": "uab",
                          "Low Rank/Sparse Decomposition": "lr",
                          "Low Rank Atlas Creation": "nglra"}
        self.errorLog = slicer.app.errorLogModel()

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
        configFilesCollapsibleButton.collapsed = True
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
        dataCollapsibleButton.collapsed = True
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
        self.abortDownloadButton = qt.QPushButton("Abort Download")
        self.abortDownloadButton.toolTip = "Abort Downloading data"
        self.abortDownloadButton.enabled = True
        dataFormLayout.addRow(self.abortDownloadButton)
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
        self.selectedConfigFile = qt.QLabel()
        parametersFormLayout.addRow(self.selectedConfigFile)

        #
        # Volume selector
        #

        self.inputSelector = slicer.qMRMLNodeComboBox()
        self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputSelector.selectNodeUponCreation = True
        self.inputSelector.addEnabled = False
        self.inputSelector.removeEnabled = False
        self.inputSelector.noneEnabled = True
        self.inputSelector.showHidden = False
        self.inputSelector.showChildNodeTypes = False
        self.inputSelector.setMRMLScene(slicer.mrmlScene)
        self.inputSelector.setToolTip("Pick an input to the algorithm. Not required.")
        parametersFormLayout.addRow("Input Volume: ", self.inputSelector)

        #
        # Select algorithm
        #
        self.selectAlgorithm = qt.QButtonGroup()
        self.selectUnbiasedAtlas = qt.QRadioButton("Unbiased Atlas Creation")
        self.selectLowRankDecomposition = qt.QRadioButton("Low Rank/Sparse Decomposition")
        self.selectLowRankAtlasCreation = qt.QRadioButton("Low Rank Atlas Creation")
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

        outputCollapsibleButton = ctk.ctkCollapsibleButton()
        outputCollapsibleButton.text = "Output"
        self.layout.addWidget(outputCollapsibleButton)
        # Layout within a collapsible button
        outputFormLayout = qt.QFormLayout(outputCollapsibleButton)

        # show log
        self.log = qt.QTextEdit()
        self.log.readOnly = True

        outputFormLayout.addRow(self.log)
        self.logMessage('<p>Status: <i>Idle</i>\n')

        # Add vertical spacer
        self.layout.addStretch(1)

        # Progress bar

        self.progress_bar = self.QMovingProgressBar()
        self.progress_bar.hide()
        outputFormLayout.addRow(self.progress_bar)

        # connections
        self.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.selectConfigFileButton.connect('clicked(bool)', self.onSelectFile)
        self.selectUnbiasedAtlas.connect('clicked(bool)', self.onSelect)
        self.selectLowRankDecomposition.connect('clicked(bool)', self.onSelect)
        self.selectLowRankAtlasCreation.connect('clicked(bool)', self.onSelect)

        self.mapperExampleFile = qt.QSignalMapper()
        self.BullseyeFileName = "Bullseye.json"
        self.HealthyVolunteersT1FlashFileName = "HealthyVolunteers-T1-Flash.json"
        self.HealthyVolunteersT1MPRageFileName = "HealthyVolunteers-T1-MPRage.json"
        self.HealthyVolunteersMRAFileName = "HealthyVolunteers-MRA.json"
        self.HealthyVolunteersT2FileName = "HealthyVolunteers-T2.json"
        self.mapperExampleFile.connect('mapped(const QString&)', self.onDownloadData)
        self.mapperExampleFile.setMapping(self.bulleyeButton, self.BullseyeFileName)
        self.mapperExampleFile.setMapping(self.t1flashButton, self.HealthyVolunteersT1FlashFileName)
        self.mapperExampleFile.setMapping(self.t1mprageButton, self.HealthyVolunteersT1MPRageFileName)
        self.mapperExampleFile.setMapping(self.mraButton, self.HealthyVolunteersMRAFileName)
        self.mapperExampleFile.setMapping(self.t2Button, self.HealthyVolunteersT2FileName)
        self.bulleyeButton.connect('clicked()', self.mapperExampleFile, 'map()')
        self.t1flashButton.connect('clicked()', self.mapperExampleFile, 'map()')
        self.t1mprageButton.connect('clicked()', self.mapperExampleFile, 'map()')
        self.mraButton.connect('clicked()', self.mapperExampleFile, 'map()')
        self.t2Button.connect('clicked()', self.mapperExampleFile, 'map()')
        self.abortDownloadButton.connect('clicked()', self.onAbortDownloadData)

        self.mapperExampleConfig = qt.QSignalMapper()
        self.mapperExampleConfig.connect('mapped(const QString&)', self.onSaveConfigFile)
        self.mapperExampleConfig.setMapping(self.exampleLRButton, self.Algorithm["Low Rank/Sparse Decomposition"])
        self.mapperExampleConfig.setMapping(self.exampleUABButton, self.Algorithm["Unbiased Atlas Creation"])
        self.mapperExampleConfig.setMapping(self.exampleNGLRAButton, self.Algorithm["Low Rank Atlas Creation"])
        self.exampleLRButton.connect('clicked()', self.mapperExampleConfig, 'map()')
        self.exampleUABButton.connect('clicked()', self.mapperExampleConfig, 'map()')
        self.exampleNGLRAButton.connect('clicked()', self.mapperExampleConfig, 'map()')

        # Refresh Apply button state
        self.onSelect()

    def onDownloadData(self, name):
        result = qt.QMessageBox.question(slicer.util.mainWindow(),
                                         'Download', "Downloading data might take several minutes",
                                         qt.QMessageBox.Ok, qt.QMessageBox.Cancel)
        if result == qt.QMessageBox.Cancel:
            return
        try:
            self.initProcessGUI()
            self.logic.run_downloadData(name)
        except Exception as e:
            logging.warning(e)
            self.onLogicRunStop()

    def onAbortDownloadData(self):
        if self.logic:
            logging.info("Download will stop after current file.")
            self.logic.abort = True

    def logEvent(self):
        self.logMessage(self.errorLog.logEntryDescription(self.errorLog.logEntryCount() - 1))

    def logMessage(self, message):
        self.log.setText(str(message))
        self.log.ensureCursorVisible()

    def onSelectFile(self):
        self.configFile = qt.QFileDialog.getOpenFileName(parent=self, caption='Select file')
        self.selectedConfigFile.text = self.configFile
        self.onSelect()

    def onSaveConfigFile(self, algo):
        """ Select an output file from dialog and save example configuration file

        Parameters
        ----------
        algo: 'lr', 'nglra', 'uab'
        """
        file = qt.QFileDialog.getSaveFileName(parent=self, caption='Select file')
        if file:
            self.logic.createExampleConfigurationAndListFiles(file, self.BullseyeFileName, algo)
        qt.QMessageBox.warning(slicer.util.mainWindow(),
                               'Download data',
                               'To use this configuration file, you will need to download the synthetic data')

    def initProcessGUI(self):
        self.progress_bar.start()
        sa = slicer.util.findChildren(name='ScrollArea')[0]
        vs = sa.verticalScrollBar()
        vs.setSliderPosition(vs.maximum)
        self.errorLog.connect('entryAdded(ctkErrorLogLevel::LogLevel)', self.logEvent)

    def cleanup(self):
        self.resetUI()
        if self.logic:
            self.logic.abort = True
        self.configFile = None
        self.selectedConfigFile.text = ''

    def onSelect(self):
        # Only enable applyButton is a config file is selected and an algorithm has been selected
        self.applyButton.enabled = self.configFile and self.selectAlgorithm.checkedButton()

    def resetUI(self):
        self.errorLog.disconnect('entryAdded(ctkErrorLogLevel::LogLevel)', self.logEvent)
        self.progress_bar.clear()

    def onApplyButton(self):
        try:
            self.initProcessGUI()
            self.logic.run_pyLAR(self.configFile,
                           self.Algorithm[self.selectAlgorithm.checkedButton().text],
                           self.inputSelector.currentNode())
        except Exception as e:
            logging.warning(e)
            # if error, stop logic
            self.onLogicRunStop()

    def onLogicRunStop(self):
        """ Reset UI once logic is done"""
        self.resetUI()
        self.logic.post_queue_stop_delayed()


#
# LowRankImageDecompositionLogic
#

class LowRankImageDecompositionLogic(ScriptedLoadableModuleLogic):
    """
  Class to download example data, create example configuration files, and run pyLAR algorithm (low-rank decomposition,
  unbiased atlas building, and low-rank atlas creation).
  The method downloading the data from a Midas server (URL and files to download are store in a JSON file) and
  running the pyLAR algorithms are multithreaded using the method implemented in [1]. This allows the Slicer GUI
  to stay responsive while one of these operation is performed. Since Slicer crashes if new data is loaded from
  a thread that is not the main thread, the new thread only performs computation and file management operations.
  Images computed or downloaded in the secondary thread are past to the main thread through a queue that loads the images
  using a QTimer call.

  [1] https://github.com/SimpleITK/SlicerSimpleFilters/blob/master/SimpleFilters/SimpleFilters.py#L333-L514
  """

    def __init__(self):
        self.main_queue = Queue.Queue()
        self.main_queue_running = False
        self.post_queue = Queue.Queue()
        self.post_queue_running = False
        self.post_queue_timer = qt.QTimer()
        self.post_queue_interval = 0.5  # 0.5 second intervals
        self.post_queue_timer.setInterval(self.post_queue_interval)
        self.post_queue_timer.connect('timeout()', self.post_queue_process)
        self.thread = threading.Thread()
        self.abort = False

    def __del__(self):
        # Stop the queues before deleting the object
        logging.debug("deleting logic")
        if self.main_queue_running:
            self.main_queue_stop()
        if self.post_queue_running:
            self.post_queue_stop()
        if self.thread.is_alive():
            self.thread.join()

    def yieldPythonGIL(self, seconds=0):
        """ Pause to yield Python GIL.
        """
        sleep(seconds)

    def thread_doit(self, f, *args, **kwargs):
        """ Starts a thread that runs the callable 'f'.

        Once callable is done running, adds 'main_queue_stop' to cleanly
        terminate multithreaded process.

        Parameters
        ----------
        f: callable to run in this new thread.
        args: arguments to pass to the callable 'f'
        kwargs: keyword arguments to pass to the callable 'f'
        """
        try:
            if callable(f):
                f(*args, **kwargs)
            else:
                logging.error("Not a callable.")
        except Exception as e:
            msg = e.message
            self.abort = True

            self.yieldPythonGIL()
            # raise is a statement, we need a function to raise an exception
            # Solution found here:
            # http://stackoverflow.com/questions/8294618/define-a-lambda-expression-that-raises-an-exception
            self.main_queue.put(lambda: (_ for _ in ()).throw(Exception(e)))
        finally:
            self.main_queue.put(self.main_queue_stop)

    def main_queue_start(self):
        """ Begins monitoring of main_queue for callables
        """
        self.main_queue_running = True
        qt.QTimer.singleShot(0, self.main_queue_process)

    def post_queue_start(self):
        """ Starts post_queue_timer to run post_queue_process as a background task
        """
        self.post_queue_running = True
        self.post_queue_timer.start()

    def post_queue_process(self):
        """ Asynchronously loads images in post_queue.

        Slicer can only be modified from the main thread. No direct interaction with Slicer, such as GUI update
        or image loading can be done from a processing thread different from Slicer's main thread.
        As a work around, this post_queue_process is run automatically, started by a QTimer, and checks if
        new image have been added to the queue. Since this is running in Slicer's main thread, this can load
        image into Slicer.
        """
        loader = slicer.util.loadVolume
        if not loader:
            logging.warning("No loader available.")
            return
        while not self.post_queue.empty():
            try:
                if self.abort:
                    break
                name, filepath = self.post_queue.get_nowait()
                logging.info('Loading %s...' % (name,))
                if loader(filepath):
                    logging.info('done loading %s...' % (name,))
                else:
                    logging.warning('Error loading %s...' % (name,))
            except Queue.Empty:
                logging.debug("No file in post_queue to load.")

    def post_queue_stop_delayed(self):
        """
    Stops the post_queue_timer with a delay long enough to run it one last time.
    This is useful when one wants the final post processing to be performed after
    the thread is finished and tries to stop post_queue_timer
    """
        qt.QTimer.singleShot(self.post_queue_interval * 2.0, self.post_queue_stop)

    def post_queue_stop(self):
        """ End monitoring of post_queue for images
        """
        self.post_queue_running = False
        self.post_queue_timer.stop()
        with self.post_queue.mutex:
            self.post_queue.queue.clear()
        logging.info("Done loading images")

    def main_queue_stop(self):
        """ End monitoring of main_queue for callables
        """
        self.main_queue_running = False
        if self.thread.is_alive():
            self.thread.join()
        slicer.modules.LowRankImageDecompositionWidget.onLogicRunStop()

    def main_queue_process(self):
        """ Processes the main_queue of callables
        """
        try:
            while not self.main_queue.empty():
                f = self.main_queue.get_nowait()
                if callable(f):
                    f()

            if self.main_queue_running:
                # Yield the GIL to allow other thread to do some python work.
                # This is needed since pyQt doesn't yield the python GIL
                self.yieldPythonGIL(.01)
                qt.QTimer.singleShot(0, self.main_queue_process)
        except Exception as e:
            logging.warning("Error in main_queue: \"{0}\"".format(e))

            # if there was an error try to resume
            if not self.main_queue.empty() or self.main_queue_running:
                qt.QTimer.singleShot(0, self.main_queue_process)

    def requiredSoftware(self):
        """ Creates and returns list of required software.
        """
        slicerSoftware = ['BRAINSFit', 'BRAINSDemonWarp', 'BRAINSResample',
                          'antsRegistration', 'AverageImages', 'ComposeMultiTransform', 'WarpImageMultiTransform',
                          'CreateJacobianDeterminantImage', 'InvertDeformationField']
        return slicerSoftware

    def softwarePaths(self):
        """ Creates and returns configuration object that contains software path.
        """
        savedPATH = os.environ["PATH"]
        currentFilePath = os.path.dirname(os.path.realpath(__file__))
        upDirectory = os.path.realpath(os.path.join(currentFilePath, '..'))
        # Prepend PATH with path of executables packaged with extension
        os.environ["PATH"] = os.path.join(upDirectory, 'ExternalBin') + os.pathsep + savedPATH
        # Creates software configuration file
        software = type('obj', (object,), {})
        slicerSoftware = self.requiredSoftware()
        for i in slicerSoftware:
            setattr(software, 'EXE_' + str(i), find_executable(i))
        os.environ["PATH"] = savedPATH
        return software

    def run_pyLAR(self, configFile, algo, node=None):
        """ Entry point to asynchronously run pyLAR algorithm from Slicer module.

        If no thread has already been started (unfinished data download or previous pyLAR computation):
        - Creates software configuration file for project.
        - Update configuration file if vtkMRMLScalarVolumeNode is passed.
        - Setup pyLAR processing thread.
        - Starts pyLAR processing in main_queue
        - Starts post_queue to asynchronously load data in Slicer
    """
        # Check that pyLAR is not already running:
        try:
            if self.thread.is_alive():
                logging.warning("Processing is already running")
                return
        except AttributeError:
            pass
        # Create software configuration object
        config = pyLAR.loadConfiguration(configFile, 'config')
        software = self.softwarePaths()
        pyLAR.containsRequirements(config, ['data_dir', 'file_list_file_name', 'result_dir'], configFile)
        result_dir = config.result_dir
        data_dir = config.data_dir
        file_list_file_name = config.file_list_file_name
        im_fns = pyLAR.readTxtIntoList(os.path.join(data_dir, file_list_file_name))
        # 'clean' needs to be done before configuring the logger that creates a file in the output directory
        if os.path.isdir(result_dir) and hasattr(config, "clean") and config.clean:
            shutil.rmtree(result_dir)
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        pyLAR.configure_logger(logger, config, configFile)
        # If node given, save node on disk to run script
        # result_dir is created while configuring logger if it did not exist before
        if node:
            extra_image_file_name = os.path.join(result_dir, "ExtraImage.nrrd")
            slicer.util.saveNode(node, extra_image_file_name)
            config.selection.append(len(im_fns))
            im_fns.append(extra_image_file_name)
        # Start actual process
        self.abort = False
        self.thread = threading.Thread(target=self.thread_doit,
                                       args=(self.thread_pyLAR, algo, config, software, im_fns, result_dir),
                                       kwargs={'configFN': configFile, 'file_list_file_name': file_list_file_name})

        self.main_queue_start()
        self.post_queue_start()
        self.thread.start()

    def thread_pyLAR(self, algo, config, software, im_fns, result_dir,
                         configFN, file_list_file_name):
        """ Run the actual pyLAR algorithm.

        Parameters
        ----------
        algo: defines which of the 3 pyLAR algorithm is run: 'lr', 'nglra', 'uab'
        config: configuration object containing all the configuration information
        software: software configuration object
        im_fns: List of the images to process
        result_dir: Output directory. If it does not already exist, it will be created
        configFN: Optional configuration file name, to print more explicit log messages
        file_list_file_name: Optional file list file name, to print more explicit log messages.

        Returns
        -------
        This functions does not return any value by populates self.post_queue with the list of
        output files from pyLAR.run(). The list of files depends on the algorithm that is chosen.

        """
        pyLAR.run(algo, config, software, im_fns, result_dir,
                  configFN=configFN, file_list_file_name=file_list_file_name)
        list_images = pyLAR.readTxtIntoList(os.path.join(result_dir, 'list_outputs.txt'))
        for i in list_images:
            name = os.path.splitext(os.path.basename(i))[0]
            self.post_queue.put((name, i))

    def loadJSONFile(self, filename):
        """ Reads a JSON file into a dictionary.

         Parameters
         ----------
         filename: file containing JSON structure.

         Returns
         -------
         Dictionary with file content

    """
        file_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(file_path)
        dir_path = os.path.join(dir_path, 'Data')
        data = open(os.path.join(dir_path, filename), 'r').read()
        return json.loads(data)

    def thread_downloadData(self, downloads, selection=None):
        """ Downloads data based on the information provided in filename (JSON).

        JSON must contain a key called 'url' and a key called 'files'. See example files in 'Data' directory.
        File name of the images that are downloaded are inserted in post_queue. If 'post_queue' is started,
        images will be asynchronously loaded in Slicer.

        Parameters
        ----------
        filename: file containing JSON structure.
        selection: list of integers. Only files that are selected will be downloaded. If no selection is
                   provided, all files will be downloaded.
        """
        logging.info('Starting to download')
        logging.debug("downloads:" + str(downloads))
        import socket
        socket.setdefaulttimeout(50)
        if not selection:
            selection = range(0, len(downloads['files'].keys()))
        else:
            print "downloads: %r" % downloads
            if max(selection) > len(downloads['files'].keys())-1:
                raise Exception("'selection' contains items (%d) greater than the number of files available in %r"
                                % (max(selection), downloads))
        import urllib
        if 'url' not in downloads.keys():
            raise Exception("Key 'url' is missing in dictionary")
        url = downloads['url']
        if 'files' not in downloads.keys():
            raise Exception("Key 'files' is missing in dictionary")
        for name, value in [downloads['files'].items()[i] for i in selection]:
            if self.abort:
                raise Exception("Download aborted")
            item_url = url + value
            filePath = os.path.join(slicer.app.settings().value('Cache/Path'), name)
            if not os.path.exists(filePath) \
                    or slicer.app.settings().value('Cache/ForceRedownload') != 'false' \
                    or os.stat(filePath).st_size == 0:
                logging.info('Requesting download %s\nfrom %s...\n' % (filePath, item_url))
                urllib.urlretrieve(item_url, filePath)
            self.post_queue.put((name, filePath))
        logging.info('Finished with download')
        return downloads

    def run_downloadData(self, filename):
        """ Asynchronously download data and load it in Slicer.

        If there is not already a thread running, either to download images, or to run
        the pyLAR processing, a new thread is started to asynchronously download data.
        Data is downloaded in 'main_queue' and loaded in Slicer in 'post_queue'.

        Parameters
        ----------
        filename: JSON file containing information to download images.
        """
        # Check that pyLAR is not already running:
        try:
            if self.thread.is_alive():
                logging.warning("Processing is already running")
                return
        except AttributeError:
            pass
        data_dict = self.loadJSONFile(filename)
        self.abort = False
        self.thread = threading.Thread(target=self.thread_doit,
                                       args=(self.thread_downloadData, data_dict))
        self.main_queue_start()
        self.post_queue_start()
        self.thread.start()

    def createExampleConfigurationAndListFiles(self, filename, datafile, algo,
                                               selection=None, output_dir=None,
                                               registration='affine', download=False):
        """ Writes example configuration file and an image list file based on JSON content.

        Parameters
        ----------
        filename: output file name.
        datafile: JSON file containing image information.
        algo: algorithm to create the configuration file for ('lr', 'uab', 'nglra')
        download: boolean to download data or not.
        selection: selection passed to 'createConfiguration()'
        output_dir: output_dir passed to 'createConfiguration()'
        registration: registration passed to 'createConfiguration()'
        """
        data_dict = self.loadJSONFile(datafile)
        if download:
            data_dict = self.thread_downloadData(data_dict)
        data_list = data_dict['files'].keys()
        cache_dir = slicer.app.settings().value('Cache/Path')
        data_list_path = []
        for data in data_list:
            data_list_path.append(os.path.join(cache_dir, data))
        temp_dir = slicer.app.temporaryPath
        file_list_file_name = u'fileList.txt'
        pyLAR.writeTxtFromList(os.path.join(temp_dir, file_list_file_name), data_list_path)
        if selection == None:
            selection = range(0, len(data_list))
        config = self.createConfiguration(algo, reference_im_fn=data_list_path[0], file_list_dir=temp_dir,
                                          file_list_file_name=file_list_file_name, selection=selection,
                                          result_dir=output_dir, registration=registration)
        pyLAR.saveConfiguration(filename, config)


    def createConfiguration(self, algo, reference_im_fn,
                                file_list_dir, file_list_file_name, selection,
                                modality='Simu', lamda=2.0, verbose=True,
                                result_dir=None, ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=None, clean=True,
                                registration='affine', histogram_matching=False, sigma=0, num_of_iterations_per_level=4,
                                num_of_levels=1, number_of_cpu=None,
                                ants_params=None, use_healthy_atlas=False, registration_type='ANTS'):
        """ Writes configuration file for pyLAR

        Parameters
        ----------
        algo: select configuration file for specified algorithm: 'lr', 'uab', 'nglra'
        reference_im_fn: Reference image.
        file_list_dir: folder containing file_list_file_name.
        file_list_file_name: output file name of the file containing the list of data to process.
                             It should only contain the basename.
        selection: List of images that would be process.
        modality: prefix used when naming output image. Default: 'Simu'
        lamda: float value
        verbose: boolean
        result_dir: output folder containing processing result. Default: slicer.app.temporaryPath+'/output'
        ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS: Number of threads used by tools based on ITK
        clean: boolean specifying if result_dir is removed before new computation is run.
        registration: Type of registration ('none', 'rigid', 'affine'). Only for 'lr'.
        histogram_matching: boolean. Only for 'lr'.
        sigma: Smoothing kernel size. For 'lr' and 'nglra'.
        num_of_iterations_per_level: integer. For 'uab' and 'nglra'.
        num_of_levels: integer. For 'uab' and 'nglra'.
        number_of_cpu: Number of tools run in parallel. For 'uab' and 'nglra'.
        ants_params: Parameters used for ANTS. For 'uab' and 'nglra'.
                    Default: ants_params = {'Convergence': '[100x50x25,1e-6,10]', \
                               'Dimension': 3, \
                               'ShrinkFactors': '4x2x1', \
                               'SmoothingSigmas': '2x1x0vox', \
                               'Transform': 'SyN[0.1,1,0]', \
                               'Metric': 'MeanSquares[fixedIm,movingIm,1,0]'}
        use_healthy_atlas: boolean. For 'nglra'
        registration_type: Registration used: 'BSpline', 'Demons', 'ANTS'. For 'nglra'.
        """
        # Checks that parameters are reasonable
        if file_list_file_name and os.path.basename(file_list_file_name) != file_list_file_name:
            raise Exception("'file_list_file_name' should only be a file name.\
             It should not contain path information. Got %s, expected %s"
                            %(file_list_file_name, os.path.basename(file_list_file_name)))
        ####
        config_data = type('config_obj', (object,), {'modality': 'Simu'})()
        config_data.file_list_file_name = "'" + file_list_file_name + "'"
        config_data.data_dir = "'" + file_list_dir + "'"
        config_data.reference_im_fn = "'" + reference_im_fn + "'"
        config_data.modality = modality
        config_data.lamda = lamda
        config_data.verbose = verbose
        temp_dir = slicer.app.temporaryPath
        if not result_dir:
            result_dir = os.path.join(temp_dir, 'output')
        config_data.result_dir = "'" + result_dir + "'"
        config_data.selection = selection
        if ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS:
            config_data.ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS = ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS
        config_data.clean = clean
        if algo == 'lr':  # Low-rank
            config_data.registration = registration
            config_data.histogram_matching = histogram_matching
            config_data.sigma = sigma
        else:
            config_data.num_of_iterations_per_level = num_of_iterations_per_level
            config_data.num_of_levels = num_of_levels
            if number_of_cpu:
              config_data.number_of_cpu = number_of_cpu
            if ants_params is None:
                ants_params = {'Convergence': '[100x50x25,1e-6,10]', \
                               'Dimension': 3, \
                               'ShrinkFactors': '4x2x1', \
                               'SmoothingSigmas': '2x1x0vox', \
                               'Transform': 'SyN[0.1,1,0]', \
                               'Metric': 'MeanSquares[fixedIm,movingIm,1,0]'}
            config_data.ants_params = ants_params
            if algo == 'nglra':  # Non-Greedy Low-rank altas creation
                config_data.use_healthy_atlas = use_healthy_atlas
                config_data.sigma = sigma
                config_data.registration_type = registration_type
            elif algo == 'uab':  # Unbiased Atlas Creation
                pass
            else:
                raise Exception('Unknown algorithm to create configuration file')
        return config_data


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
        """Run all tests
        """
        self.setUp()
        self.test_softwarePaths()
        self.test_softwarePaths_PATH_unchanged()
        self.test_loadJSONFile()
        self.test_createConfiguration()
        self.test_createExampleConfigurationAndListFiles()
        self.test_downloadData()
        self.test_lowRankImageDecomposition()
        self.test_lowRankImageDecompositionExtraNode()

    def test_softwarePaths(self):
        """ Verifies that all the expected tools are found and are in the correct location.

        BRAINSResample, BRAINSDemonWarp, and BRAINSFit should be found in Slicer.
        The other tools should be found in this extension's directory.
        """
        self.delayDisplay("Starting test_softwarePaths")
        logic = LowRankImageDecompositionLogic()
        software = logic.softwarePaths()
        requiredSoftware = logic.requiredSoftware()
        listPATH=[]
        for i in requiredSoftware:
            listPATH.append(getattr(software, 'EXE_' + str(i)))
        logging.debug("List software paths: %s"%(listPATH))
        self.assertTrue(all(listPATH))
        listToolsInSlicerTrunk = ['BRAINSResample', 'BRAINSDemonWarp', 'BRAINSFit']
        for i in listToolsInSlicerTrunk:
            path = getattr(software, 'EXE_' + str(i))
            logging.debug("Path found: %s ; extensions path: %s"%(path,slicer.app.slicerHome))
            self.assertTrue(slicer.app.slicerHome in path)
        listToolsInExtension = set(requiredSoftware) - set(listToolsInSlicerTrunk)
        for i in listToolsInExtension:
            path = getattr(software, 'EXE_' + str(i))
            logging.debug("Path found: %s ; extensions path: %s"%(path,slicer.app.extensionsInstallPath))
            self.assertTrue(slicer.app.extensionsInstallPath in path)
        self.delayDisplay('test_softwarePaths passed!')


    def test_softwarePaths_PATH_unchanged(self):
        """ Making sure that PATH is unchanged after looking for software on the system.

        The function 'softwarePaths()' modifies the environment variable PATH to find executables
        on the system. This test makes sure that PATH is reset to its original value after
        exiting 'softwarePaths()'. Not resetting PATH could lead to issues, and would also incrementally
        make PATH longer each time this function is called.
        """
        self.delayDisplay("Starting test_softwarePaths_PATH_unchanged")
        logic = LowRankImageDecompositionLogic()
        savedPATH = os.environ["PATH"]
        logic.softwarePaths()
        PATH = os.environ["PATH"]
        self.assertTrue(not cmp(savedPATH,PATH))
        self.delayDisplay('test_softwarePaths_PATH_unchanged passed!')

    def test_loadJSONFile(self):
        """ Test that a given JSON file containing downloading information can be loaded.

        One of the JSON file used to download example data is loaded. This test verifies that
        this file is loaded and that its content matches expected values.
        """
        self.delayDisplay("Starting test_loadJSONFile")
        logic = LowRankImageDecompositionLogic()
        downloads = logic.loadJSONFile("Bullseye.json")
        self.assertTrue('url' in downloads.keys())
        self.assertTrue(downloads['url'] == "http://slicer.kitware.com/midas3/download?items=")
        self.assertTrue('files' in downloads.keys())
        self.assertTrue(downloads['files']['fMeanSimu.nrrd'] == "231227")
        self.delayDisplay('test_loadJSONFile passed!')

    def test_createConfiguration(self):
        """ Test the creation of a configuration file.

        A configuration file is created. This test verifies that the file gets created in the correct
        location and that its content is what is expected.
        It also verifies that if 'createConfiguration()' is called with wrong arguments
        (file_list_file_name should only contain a basename, selection should contain files in given data_list),
        an exception is thrown.
        """
        self.delayDisplay("Starting test_createConfiguration")
        logic = LowRankImageDecompositionLogic()
        temp_dir = slicer.app.temporaryPath
        filename = os.path.join(temp_dir, "test_createConfiguration_file.txt")
        # Remove the file that could have been created in a previous test
        try:
            os.remove(filename)
        except OSError as e:
            if errno.errorcode[e.errno] != 'ENOENT':  # No such file or directory
                raise e
        # Make sure that an exception is thrown if the given 'createConfiguration' is
        # not only a basename (has path information)
        failed_list_file = os.path.join(slicer.app.temporaryPath, 'failed_list_file.txt')
        with self.assertRaisesRegexp(Exception,"'file_list_file_name' should only be a file name.\
             It should not contain path information..*"):
            logic.createConfiguration("lr", "fake_reference_image.nrrd", "fake_file_list_dir",
                                      failed_list_file, [0])
        # This time a configuration file should be created.
        selection = [0,3]
        config = logic.createConfiguration("lr", "fake_reference_image.nrrd", "fake_file_list_dir",
                                           "fake_file_list_name.txt", selection)
        # Loads the configuration file that was saved and compare only the selection indices.
        # If the indices are correct, we hope that everything is correct
        self.assertTrue(config.selection == selection, 'Expected %r. Got %r'%(selection,config.selection))
        self.delayDisplay('test_createConfiguration passed!')

    def test_createExampleConfigurationAndListFiles(self):
        """ Creates a configuration file based on the content of a loaded JSON file.

        When creating an example configuration file in this module, some of its
        content is given by a JSON file that is used to download example data.
        This test assess that creating a configuration file from a JSON file creates
        a configuration file with the expected values.
        """
        self.delayDisplay("Starting test_createExampleConfigurationAndListFiles")
        temp_dir = slicer.app.temporaryPath
        filename = os.path.join(temp_dir, "test_createExampleConfigurationAndListFiles_file.txt")
        json_file_name = "Bullseye.json"
        # Remove the file that could have been created in a previous test
        try:
            os.remove(filename)
        except OSError as e:
            if errno.errorcode[e.errno] != 'ENOENT':  # No such file or directory
                raise e
        logic = LowRankImageDecompositionLogic()
        selection = [0,1,3]
        logic.createExampleConfigurationAndListFiles(filename, json_file_name , 'nglra', selection=selection)
        # Make sure the example configuration file was created
        self.assertTrue(os.path.isfile(filename), '%s is not a file.'%filename)
        # Check a few of its variables
        config = pyLAR.loadConfiguration(filename, 'config')
        self.assertTrue(config.selection == selection, 'Got %r. Expected %r'%(config.selection,selection))
        self.assertTrue(config.use_healthy_atlas is False, 'Got %r. Expected %r'%(config.use_healthy_atlas, False))
        self.assertTrue(config.registration_type == 'ANTS', 'Got %r. Expected %r'%(config.registration_type, 'ANTS'))
        # Tries to load file_list_file_name file and compare its
        listFiles = pyLAR.readTxtIntoList(os.path.join(config.data_dir, config.file_list_file_name))
        cache_dir = slicer.app.settings().value('Cache/Path')
        data_dict = logic.loadJSONFile(json_file_name)
        file0 = os.path.join(cache_dir, data_dict['files'].keys()[0])
        self.assertTrue(listFiles[0] == file0, 'Got %s. Expected %s.'%(listFiles[0], file0))
        self.delayDisplay('test_createExampleConfigurationAndListFiles passed!')

    def test_downloadData(self):
        """ Verifies that data can be downloaded from a server.

        Example data can be downloaded from a server. This test assess that the download
        process works for one image which information is loaded from a JSON file that
        contains its download information (url, image name, image key on the server).

        """
        self.delayDisplay("Starting test_downloadData")
        json_file_name = "TestDownloadOneImage.json"
        logic = LowRankImageDecompositionLogic()
        data_dict = logic.loadJSONFile(json_file_name)
        with self.assertRaisesRegexp(Exception,"'selection' contains .*"):
            logic.thread_downloadData(data_dict, [1])
        logic.thread_downloadData(data_dict, [0])
        self.delayDisplay('test_downloadData passed!')


    def test_lowRankImageDecomposition(self):
        """ Test low rank/sparse decomposition of an image

         This test verifies that calling the low rank/sparse decomposition algorithm from pyLAR
         outputs the expected file.
        """
        self.delayDisplay("Starting test_lowRankImageDecomposition")
        #
        # first, get some data
        #
        json_file_name = "TestDownloadOneImage.json"
        algo = 'lr'
        logic = LowRankImageDecompositionLogic()
        lr_test_file_name = os.path.join(slicer.app.temporaryPath,'lr_test_file.txt')
        result_dir = os.path.join(slicer.app.temporaryPath, 'output')
        # Remove result directory to start from a clean computation
        shutil.rmtree(result_dir, ignore_errors=True)
        logic.createExampleConfigurationAndListFiles(lr_test_file_name, json_file_name, algo,
                                               selection=[0], output_dir=result_dir,
                                               registration='none', download=True)
        logic.run_pyLAR(os.path.join(slicer.app.temporaryPath, lr_test_file_name), algo)
        if logic.thread.is_alive():
            logic.thread.join()
        # Check that output files are there and loaded in Slicer
        list_images = pyLAR.readTxtIntoList(os.path.join(result_dir, 'list_outputs.txt'))
        for image in list_images:
            self.assertTrue(os.path.isfile(image))
        self.delayDisplay('test_lowRankImageDecomposition passed!')

    def test_lowRankImageDecompositionExtraNode(self):
        """ Test low rank/sparse decomposition of an image given by a vtkMRMLScalarVolumeNode

        If a vtkMRMLScalarVolumeNode is passed to the logic additionally to the configuration file,
        the scalar volume of the node is saved on the disk and a new configuration file containing the added file is
        created and used to run the processing.
        """
        self.delayDisplay("Starting test_lowRankImageDecompositionExtraNode")
        #
        # first, get some data
        #
        self.setUp()  # Clear MRML
        json_file_name = "Bullseye.json"
        logic = LowRankImageDecompositionLogic()

        algo = 'lr'
        logic = LowRankImageDecompositionLogic()
        lr_test_file_basename = 'lr_test_file.txt'
        lr_test_file_filename = os.path.join(slicer.app.temporaryPath, lr_test_file_basename)
        result_dir = os.path.join(slicer.app.temporaryPath, 'output')
        # Remove result directory to start from a clean computation
        shutil.rmtree(result_dir, ignore_errors=True)
        selection = [0,4,10]
        logic.createExampleConfigurationAndListFiles(lr_test_file_filename, json_file_name, algo,
                                       selection=selection, output_dir=result_dir,
                                       registration='none', download=True)
        self.assertTrue(os.path.isfile(lr_test_file_filename), '%s not found' % lr_test_file_filename)
        file_name_to_check = os.path.join(slicer.app.temporaryPath, u'fileList.txt')
        self.assertTrue(os.path.isfile(file_name_to_check), '%s not found' % file_name_to_check)
        # Load data in Slicer
        loader = slicer.util.loadVolume
        self.assertTrue(loader, 'Volume loaded not found')
        cache_dir = slicer.app.settings().value('Cache/Path')
        data_dict = logic.loadJSONFile(json_file_name)
        data_list = data_dict['files'].keys()
        self.assertTrue(os.path.basename(data_list[0]) == data_list[0],
                        "Got %s, expected %s" % (data_list[0], os.path.basename(data_list[0])))
        for i in range(0, len(data_list)):
            data_list[i] = os.path.join(cache_dir, data_list[i])
        loaded_image = os.path.join(cache_dir, data_list[0])
        self.assertTrue(loader(loaded_image), 'Unable to load %s' % loaded_image)
        # Get node from Slicer
        nodeName = os.path.splitext(os.path.basename(data_list[0]))[0]
        mrml = slicer.app.mrmlScene()
        collection = mrml.GetNodesByName(nodeName)
        scalarNode = collection.GetItemAsObject(0)
        self.assertTrue(scalarNode, '%s not found as a scalar node' % nodeName)

        logic.run_pyLAR(lr_test_file_filename, algo, node=scalarNode)
        if logic.thread.is_alive():
            logic.thread.join()
        # Check that output files are there and loaded in Slicer
        list_images = pyLAR.readTxtIntoList(os.path.join(result_dir, 'list_outputs.txt'))
        for image in list_images:
            self.assertTrue(os.path.isfile(image), '%s not found' % image)
        # Check new configuration file and new file_list_file_name file created with additional node
        config_file_name = os.path.join(result_dir, lr_test_file_basename)
        config = pyLAR.loadConfiguration(config_file_name, 'config')
        expected_selection = selection + [len(data_list)]
        self.assertTrue(config.selection == expected_selection,
                        "Unexpected selection. Got %s in %s, expected %s"
                        %(str(config.selection), config_file_name,str(expected_selection)))
        data_dir = config.data_dir
        file_list_file_name = config.file_list_file_name
        im_fns = pyLAR.readTxtIntoList(os.path.join(data_dir, file_list_file_name))
        self.assertTrue(len(expected_selection) == len(config.selection),
                        "Unexpected selection length: got %d,expected %d"
                        %(len(config.selection),len(selection)+1))
        self.assertTrue(config.selection[len(config.selection)-1] == len(data_list),
                        "Unexpected last selection value. Got %d, expected %d"
                        %(config.selection[len(config.selection)-1], len(data_list)))
        self.assertTrue(len(im_fns)-2 > 0)
        for i in range(0,len(im_fns)-2):
            self.assertTrue(im_fns[i] == data_list[i], 'Expected %s. Got %s' % (im_fns[i],data_list[i]))
        expected_extra_image_name = os.path.join(result_dir, "ExtraImage.nrrd")
        self.assertTrue(im_fns[len(im_fns)-1] == expected_extra_image_name, "Got %s, expected %s. Pos %d - whole list %s"
                        %(im_fns[len(im_fns)-1], expected_extra_image_name,len(im_fns), str(im_fns)))
        self.delayDisplay('test_lowRankImageDecompositionExtraNode passed!')
