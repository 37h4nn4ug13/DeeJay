cmake_minimum_required(VERSION 3.20)

project(DeeJayAudio LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(DEEJAY_USE_SYSTEM_PORTAUDIO "Link against a system PortAudio install" OFF)

if(DEEJAY_USE_SYSTEM_PORTAUDIO)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(PORTAUDIO REQUIRED portaudio-2.0)
    add_library(portaudio INTERFACE)
    target_include_directories(portaudio INTERFACE ${PORTAUDIO_INCLUDE_DIRS})
    target_link_libraries(portaudio INTERFACE ${PORTAUDIO_LIBRARIES})
else()
    include(FetchContent)

    set(PORTAUDIO_TAG v19.7.0)
    FetchContent_Declare(
        portaudio
        URL https://github.com/PortAudio/portaudio/archive/refs/tags/${PORTAUDIO_TAG}.tar.gz
    )

    FetchContent_MakeAvailable(portaudio)
endif()

add_executable(deejay_audio
    src/main.cpp
)

target_link_libraries(deejay_audio PRIVATE portaudio)

target_compile_features(deejay_audio PRIVATE cxx_std_17)

include(CTest)

if(BUILD_TESTING)
    add_test(NAME deejay_audio_smoke COMMAND deejay_audio --duration-seconds 0)
endif()
