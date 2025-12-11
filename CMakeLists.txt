cmake_minimum_required(VERSION 3.16)
project(DeeJay LANGUAGES CXX)

option(DEEJAY_ENABLE_RUBBERBAND "Enable Rubber Band Library integration" ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(deejay_audio STATIC
    src/TimeStretchPitchProcessor.cpp
    src/LatencyCompensatedProcessor.cpp
)

target_include_directories(deejay_audio PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)

if (DEEJAY_ENABLE_RUBBERBAND)
    find_package(RubberBand QUIET)
    if (RubberBand_FOUND)
        target_link_libraries(deejay_audio PUBLIC RubberBand::rubberband)
        target_compile_definitions(deejay_audio PUBLIC DEEJAY_HAVE_RUBBERBAND=1)
        message(STATUS "Building with Rubber Band Library support")
    else()
        message(WARNING "Rubber Band Library not found; building with stub implementation")
    endif()
endif()

