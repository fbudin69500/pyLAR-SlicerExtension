
set(proj ANTS)

set(${proj}_DEPENDENCIES ITKv4)

ExternalProject_Include_Dependencies(${proj} PROJECT_VAR proj DEPENDS_VAR ${proj}_DEPENDENCIES)

# Sanity checks
if(DEFINED ANTS_DIR AND NOT EXISTS ${ANTS_DIR})
  message(FATAL_ERROR "ANTS_DIR variable is defined but corresponds to nonexistent directory")
endif()

if(NOT ${CMAKE_PROJECT_NAME}_USE_SYSTEM_${proj})
  #-----------------------------------------------------------------------------
  # Add external dependencies: pyLAR library
  set(proj ANTS)
  set(projbuild ${proj}-build)
#  if( MSVC )
#    set( INSTALL_CONFIG ${projbuild}/ANTS.sln /Build Release /Project INSTALL.vcproj )
#  else()
#    set( INSTALL_CONFIG -C ${projbuild} install)
#  endif()
  ExternalProject_Add(${proj}
    ${${proj}_EP_ARGS}
    GIT_REPOSITORY ${git_protocol}://github.com/fbudin69500/ANTs.git
    GIT_TAG 5bbf379aa583d603df92b3f6b2f54e12ba5484cb
    SOURCE_DIR ${proj}
    BINARY_DIR ${projbuild}
    CMAKE_ARGS
      -DCMAKE_CXX_COMPILER:FILEPATH=${CMAKE_CXX_COMPILER}
      -DCMAKE_CXX_FLAGS:STRING=${ep_common_cxx_flags}
      -DCMAKE_C_COMPILER:FILEPATH=${CMAKE_C_COMPILER}
      -DCMAKE_C_FLAGS:STRING=${ep_common_c_flags}
      -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
      -DCMAKE_RUNTIME_OUTPUT_DIRECTORY:PATH=${CMAKE_RUNTIME_OUTPUT_DIRECTORY}
      -DCMAKE_LIBRARY_OUTPUT_DIRECTORY:PATH=${CMAKE_LIBRARY_OUTPUT_DIRECTORY}
      -DCMAKE_ARCHIVE_OUTPUT_DIRECTORY:PATH=${CMAKE_ARCHIVE_OUTPUT_DIRECTORY}
      -DANTS_BUILD_WarpImageMultiTransform:BOOL=TRUE
      -DANTS_BUILD_ComposeMultiTransform:BOOL=TRUE
      -DANTS_BUILD_AverageImages:BOOL=TRUE
      -DBUILD_ALL_ANTS_APPS:BOOL=FALSE
      -DBUILD_SHARED_LIBS:BOOL=OFF
      -DBIN_INSTALL_DIR:STRING=${Slicer_INSTALL_ExternalBinMODULES_BIN_DIR}
      -DBUILD_TESTING:BOOL=OFF
      -DITK_DIR:PATH=${ITK_DIR}
      -DSlicerExecutionModel:PATH=${SlicerExecutionModel_DIR}
      -DANTS_SUPERBUILD:BOOL=FALSE
#    INSTALL_COMMAND ${CMAKE_MAKE_PROGRAM} ${INSTALL_CONFIG}
    INSTALL_COMMAND ""
    DEPENDS
      ${${proj}_DEPENDENCIES}
  )
#  set(ANTS_DIR ${CMAKE_BINARY_DIR}/${proj}-install/bin)
  set(ANTS_DIR ${CMAKE_BINARY_DIR}/${projbuild})
else()
  ExternalProject_Add_Empty(${proj} DEPENDS ${${proj}_DEPENDENCIES})
endif()

mark_as_superbuild(
  VARS ANTS_DIR:PATH 
  LABELS "FIND_PACKAGE"
  )
