cmake_minimum_required(VERSION 3.22)

project(OpenLifeDJ VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(APPLE AND NOT CMAKE_OSX_DEPLOYMENT_TARGET)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "11.0" CACHE STRING "Minimum macOS version" FORCE)
endif()

option(OLDJ_BUILD_TESTS "Build the engine unit tests" ON)

add_subdirectory(external/JUCE)

# Engine first: it must never depend on GUI modules (the test target proves this).
add_subdirectory(engine)
add_subdirectory(app)

if(OLDJ_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
