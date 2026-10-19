# The audio engine. An INTERFACE library: every executable that links it (the app, the tests)
# compiles these sources together with its own copy of the JUCE modules, which is how JUCE
# modules are meant to be consumed. Only non-GUI JUCE modules may be linked here.
add_library(oldj_engine INTERFACE)

target_sources(oldj_engine
    INTERFACE
        ${CMAKE_CURRENT_SOURCE_DIR}/src/Engine.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/src/TestTone.cpp)

target_include_directories(oldj_engine
    INTERFACE
        ${CMAKE_CURRENT_SOURCE_DIR}/include)

target_link_libraries(oldj_engine
    INTERFACE
        juce::juce_audio_basics)
