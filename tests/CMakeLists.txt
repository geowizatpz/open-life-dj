include(FetchContent)

FetchContent_Declare(Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG v3.16.1
    GIT_SHALLOW TRUE)
FetchContent_MakeAvailable(Catch2)

# Links only the engine (non-GUI JUCE modules). If the engine ever starts needing a GUI
# module, this target stops compiling - that is intentional.
juce_add_console_app(oldj_tests PRODUCT_NAME "oldj_tests")

target_sources(oldj_tests
    PRIVATE
        EngineTests.cpp)

target_compile_definitions(oldj_tests
    PRIVATE
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=0)

target_link_libraries(oldj_tests
    PRIVATE
        oldj_engine
        Catch2::Catch2WithMain
        juce::juce_recommended_config_flags
        juce::juce_recommended_warning_flags)

# Tests compare exact sample values on purpose (silence must be exactly 0.0f).
target_compile_options(oldj_tests PRIVATE $<$<CXX_COMPILER_ID:Clang,AppleClang,GNU>:-Wno-float-equal>)

list(APPEND CMAKE_MODULE_PATH ${catch2_SOURCE_DIR}/extras)
include(Catch)
catch_discover_tests(oldj_tests)
