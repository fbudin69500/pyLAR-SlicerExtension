cmake_minimum_required(VERSION 2.8.9)

project(pyLAR-SlicerExtension)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/pyLAR-SlicerExtension")
set(EXTENSION_CATEGORY "Filtering")
set(EXTENSION_CONTRIBUTORS "Francois Budin (Kitware Inc.)")
set(EXTENSION_DESCRIPTION "Low-rank decomposition of images")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/pyLAR.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/pyLAR/Screenshots/1.png")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})
set(Slicer_INSTALL_ExternalBinMODULES_BIN_DIR ${Slicer_INSTALL_CLIMODULES_BIN_DIR}/../ExternalBin )
#-----------------------------------------------------------------------------
# Git
#-----------------------------------------------------------------------------
option(${CMAKE_PROJECT_NAME}_USE_GIT_PROTOCOL "If behind a firewall turn this off to use http instead." ON)
set(git_protocol "git")
if(NOT ${CMAKE_PROJECT_NAME}_USE_GIT_PROTOCOL)
  set(git_protocol "http")
endif()
find_package(Git REQUIRED)

#-----------------------------------------------------------------------------
# Enable and setup External project global properties
#-----------------------------------------------------------------------------

set(ep_common_c_flags "${CMAKE_C_FLAGS_INIT} ${ADDITIONAL_C_FLAGS}")
set(ep_common_cxx_flags "${CMAKE_CXX_FLAGS_INIT} ${ADDITIONAL_CXX_FLAGS}")

#-----------------------------------------------------------------------------
# Add external dependencies:

set(${PROJECT_NAME}_SUPERBUILD TRUE)

include(ExternalProject)
set(proj ${PROJECT_NAME})
set(${proj}_DEPENDENCIES pyLAR ANTS ITKFixedPointInverseDeformationField)

ExternalProject_Include_Dependencies(${proj}
  DEPENDS_VAR ${proj}_DEPENDENCIES
  )

ExternalProject_Add_Empty(${proj}
  DEPENDS
    ${${proj}_DEPENDENCIES}
  )

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(Script)
## NEXT_MODULE
#-----------------------------------------------------------------------------
# Packaging
set(ANTS_EXE
 antsRegistration
 AverageImages
 ComposeMultiTransform
 WarpImageMultiTransform
 CreateJacobianDeterminantImage
)
foreach(VAR ${ANTS_EXE})
  set(CPACK_INSTALL_CMAKE_PROJECTS "${CPACK_INSTALL_CMAKE_PROJECTS};${ANTS_DIR};ANTS;RUNTIME_${VAR};/")
endforeach()
set(CPACK_INSTALL_CMAKE_PROJECTS "${CPACK_INSTALL_CMAKE_PROJECTS};${ITKFixedPointInverseDeformationField_DIR};ITKFixedPointInverseDeformationField;ALL;/")
install(DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/pyLAR/pyLAR DESTINATION ${Slicer_INSTALL_QTSCRIPTEDMODULES_BIN_DIR} )
set(CPACK_INSTALL_CMAKE_PROJECTS "${CPACK_INSTALL_CMAKE_PROJECTS};.;pyLAR-SlicerExtension;ALL;/")
include(${Slicer_EXTENSION_CPACK})

