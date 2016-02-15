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

include(ExternalProject)

set(proj pyLAR)
ExternalProject_Add(${proj}
GIT_REPOSITORY git@github.com:fbudin69500/pyLAR.git
GIT_TAG cadedde782cf9cc9f9aa53bf616da870c0ce203e
SOURCE_DIR ${proj}
CONFIGURE_COMMAND ""
BUILD_COMMAND ""
INSTALL_COMMAND ""
)
install(DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/pyLAR/pyLAR DESTINATION ${Slicer_QTSCRIPTEDMODULES_LIB_DIR})
#-----------------------------------------------------------------------------
# Add external dependencies: pyLAR library
set(proj ANTS)
ExternalProject_Add(${proj}
GIT_REPOSITORY https://github.com/stnava/ANTs.git
GIT_TAG 3758b7c5617ec1e21d4e60a2930d9729fe03a5cd
SOURCE_DIR ${proj}
BINARY_DIR ${proj}-build
CMAKE_GENERATOR ${gen}
CMAKE_ARGS
    -DCMAKE_CXX_COMPILER:FILEPATH=${CMAKE_CXX_COMPILER}
    -DCMAKE_CXX_FLAGS:STRING=${ep_common_cxx_flags}
    -DCMAKE_C_COMPILER:FILEPATH=${CMAKE_C_COMPILER}
    -DCMAKE_C_FLAGS:STRING=${ep_common_c_flags}
    -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
    -DCMAKE_RUNTIME_OUTPUT_DIRECTORY:PATH=${CMAKE_RUNTIME_OUTPUT_DIRECTORY}
    -DCMAKE_LIBRARY_OUTPUT_DIRECTORY:PATH=${CMAKE_LIBRARY_OUTPUT_DIRECTORY}
    -DCMAKE_ARCHIVE_OUTPUT_DIRECTORY:PATH=${CMAKE_ARCHIVE_OUTPUT_DIRECTORY}
    -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}/${proj}-install
    -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
    -DBUILD_SHARED_LIBS:BOOL=OFF
    -DBUILD_TESTING:BOOL=OFF
)


#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(LowRankImageDecomposition)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
