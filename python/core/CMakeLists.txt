# Copyright (c) 2024 CNES
#
# All rights reserved. Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
include_directories(include)

find_package(GSL REQUIRED)
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

set_target_properties(Python::Module PROPERTIES
        MAP_IMPORTED_CONFIG_DEBUG ";RELEASE")

message("Python3 Include Dirs: " ${Python_INCLUDE_DIRS})
# show the python path
message("Python3_EXECUTABLE: " ${Python_EXECUTABLE})

file(GLOB_RECURSE IMPLEMENT "lib/*.cpp")
add_library(pyinterp STATIC ${IMPLEMENT})
set_target_properties(pyinterp PROPERTIES POSITION_INDEPENDENT_CODE TRUE)
target_include_directories(pyinterp PUBLIC ${Python3_INCLUDE_DIRS})
target_include_directories(pyinterp PUBLIC ${Python_INCLUDE_DIRS})
target_link_libraries(pyinterp PRIVATE ${Python3_LIBRARIES})
target_link_libraries(
  pyinterp
  PRIVATE
  pybind11::headers
  PUBLIC
  cpp_coverage
)

file(GLOB_RECURSE SOURCES "module/*.cpp")
pybind11_add_module(core MODULE ${SOURCES})
target_link_libraries(
  core
  PRIVATE
  pyinterp
  GSL::gsl
  GSL::gslcblas
  PUBLIC
  cpp_coverage
)

if(GTest_FOUND)
  add_subdirectory(tests)
endif()
